/*
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
package main

import (
    "bufio"
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "io/ioutil"
    "log"
    "net/http"
    "os"
    "os/signal"
    "strings"
    "sync"
    "syscall"
    "time"

    "github.com/apache/thrift/lib/go/thrift"
    "github.com/go-redis/redis/v8"
    "github.com/google/uuid"
    "github.com/knix-microfunctions/knix/Sandbox/frontend/datalayermessage"
    "github.com/knix-microfunctions/knix/Sandbox/frontend/datalayerservice"
)

// custom log writer to overwrite the default log format
type LogWriter struct {
}

func (writer LogWriter) Write(bytes []byte) (int, error) {
  tnow := time.Now()
  tnow_millis := tnow.UnixNano() / 1000000
  return fmt.Printf("[%d] [%s] [INFO] [org.microfunctions.sandbox.frontend] %s",
      tnow_millis,
      tnow.Format("2006-01-02 15:04:05.000"),
      string(bytes))
}

// Execution keeps a condition and a message pointer
// Upon completion (i.e. when a result has been retrieved),
// the message contains the result and the condition is signalled
type Execution struct {
  cond *sync.Cond
  msg *MfnMessage
  rt_rcvdlq int64
}

// ExecutionResults keeps a map of execution id's (UUID rendered strings) and Execution
var ExecutionMutex = sync.Mutex{}
var ExecutionCond = sync.NewCond(&ExecutionMutex)
var ExecutionResults = make(map[string]*Execution)
var fluentbit *bufio.Writer

// The following variables are used by all Thrift clients to adhere to the correct protocol
var (
  protocolFactory = thrift.NewTCompactProtocolFactory()
  transportFactory = thrift.NewTFramedTransportFactory(thrift.NewTTransportFactory())
)

// Producer (see InitProducer() and SendMessage()) sends new events to entryTopic
// The producer thrift client requires its own transport and context not to interfere with other clients
var (
  entryTopic string
  producer *redis.Client
  producerCtx = context.Background()
  producerMutex = sync.Mutex{}
)

// Consumer (see ConsumeResults() uses a global result topic set by main()
var (
  resultTopic string
)

var (
  internalEndpoint string
  externalEndpoint string
)

// Datalayer is used to store checkpoints when sending a message and to retrieve results of executions by the HTTP handler
// main() initializes the commonly used keyspace and tablenames for this sandbox frontend
// a mutex is required to sync datalayer access (a pool might be worthwhile with high concurrency)
var (
  datalayer *datalayerservice.DataLayerServiceClient
  datalayerCtx = context.Background()
  datalayerTransport thrift.TTransport
  datalayerKeyspace string
  datalayerMapTable string
  datalayerTable string
  datalayerMutex = sync.Mutex{}
)

var (
  httpServer *http.Server
)

// ConsumeResults (a concurrent go routine)
// Initializes its own thrift client to consume from the results topic
// It loops to consume messages
// The loop can be halted by a boolean to the quit channel
// After graceful shutdown (respecting 10s pull timeout), it sends a boolean to the done channel
func ConsumeResults(quit <-chan bool, done chan<- bool) {
  var (
    consumer *redis.Client
    consumerCtx = context.Background()
  )
  fmt.Println("consumer: Starting client")

  consumer = redis.NewClient(&redis.Options {
          Addr: os.Getenv("MFN_QUEUE"),
          Password: "",
          DB: 0,
  })

  // _XXX_: entry and exit topics are handled by the sandbox agent before
  // launching the frontend, so no need
  //err = consumer.AddTopic(consumerCtx, resultTopic)
  //if err != nil {
  //  fmt.Println("consumer: Error creating result topic", resultTopic, err)
  //  log.Fatal(err)
  //}
  fmt.Println("consumer: result topic", resultTopic)

  defer func() {
    //err := consumer.RemoveTopic(consumerCtx, resultTopic)
    //if err != nil {
    //  fmt.Println("consumer: Error removing result topic", resultTopic, err)
    //  log.Fatal(err)
    //}
    //log.Println("consumer: Removed result topic", resultTopic)
    consumer.Close()
    close(done)
  }()
  var rt_rcvdlq int64
  for {
    select {
    case <-quit:
        return
    default:
      res, err := consumer.XRead(consumerCtx, &redis.XReadArgs{
                Streams: []string{resultTopic, "0"},
                Count:   1,
                Block:   0,
            }).Result()
      rt_rcvdlq = time.Now().UnixNano()
      if len(res) == 0 {
          continue
      } else if len(res[0].Messages) == 0 {
          continue
      }

      lqcm := res[0].Messages[0].Values
      lqcm_id := res[0].Messages[0].ID

      //n, err := client.XDel(ctx, "stream", "1-0", "2-0", "3-0").Result()
      n, err := consumer.XDel(consumerCtx, resultTopic, lqcm_id).Result()

      if n != 1 {
        log.Println("consumer: Couldn't receive message", err)
        continue
      }

      if err != nil {
        log.Println("consumer: Couldn't receive message", err)
        continue
      }

      value := lqcm["value"].(string)
      valueb := []byte(value)

      msg := MfnMessage{}
      err = msg.UnmarshalJSON(valueb)

      if err != nil {
        log.Println("consumer: Couldn't unmarshal message", err)
        continue
      }

      ExecutionCond.L.Lock()
      e, ok := ExecutionResults[msg.Mfnmetadata.ExecutionId]
      ExecutionCond.L.Unlock()
      if !ok {
        log.Println("consumer: Received unknown result", string(msg.Mfnmetadata.ExecutionId))
        continue
      }
      log.Println("consumer: Received result for ID", msg.Mfnmetadata.ExecutionId)
      e.cond.L.Lock()
      e.rt_rcvdlq = rt_rcvdlq
      e.msg = &msg
      e.cond.Broadcast()
      e.cond.L.Unlock()
    }
  }
}

// handler is an HTTP handle function
// It checks requests for URL parameters async and executionId
// If an executionId is present, it is a retrieval that only tries to fetch the result from the datalayer
// If the retrieval is synchronous and no result is available, it will also create an Execution and wait on its completion
// New requests are checked to have a Content-type 'application/json'
// the body will be used to generate a new MfnMessage and sent
// Synchronous requests will create an execution and wait on its completion before returning thr response
// Asynchronous requests will be answered with a 3xx response and a Location header pointing to the retrieval URL with param executionId
func handler(w http.ResponseWriter, r *http.Request) {
  //w.Header().Set("Access-Control-Allow-Origin", fmt.Sprintf("http://%s:*", r.Host[:strings.LastIndex(r.Host,":")]))
  w.Header().Set("Access-Control-Allow-Origin", "*")
  w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
  w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
  if r.Method == "OPTIONS" {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    return
  }
  var err error
  var (
    rt_entry  int64
    rt_sendlq int64
    rt_sentlq int64
    rt_rcvdlq int64
    rt_exitfe int64
  )
  rt_entry = time.Now().UnixNano()

  // CHECK FOR ASYNC
  async := false
  hasync, ok := r.URL.Query()["async"]
  if ok && len(hasync[0]) > 0 && strings.ToLower(hasync[0]) != "false" && hasync[0] != "0" {
    async = true
  }

  // HANDLE EXECUTIONID RESULT RETRIEVAL
  hexecutionid, ok := r.URL.Query()["executionId"]
  if ok && len(hexecutionid[0]) > 0 {
    id := hexecutionid[0]
    res, err := FetchResult(id)
    if err != nil {
      log.Println("handler: Couldn't fetch result of execution ID", id, err)
      http.Error(w, "Can't fetch result", http.StatusInternalServerError)
    } else if res == nil {
      if async {
        /*
        the client asked for the result in async mode.
        if the result is not available yet, then just return the execution id again
        and let the client handle the retry.
        */
        log.Printf("handler: Result not yet available of execution ID %s.", id)
        //log.Printf("handler: Result not yet available of execution ID %s, redirecting", id)
        // TODO: 300 location redirect
        //http.Redirect(w, r, r.URL.Path + "?executionId=" + id, http.StatusTemporaryRedirect)
        //w.Header().Set("Content-Type", "application/json")
        // w.Header().Set("Retry-After", "5")
        // http.Redirect(w, r, r.URL.Path + "?executionId=" + id, http.StatusFound)

        type ResultMessage struct {
              ExecutionId string `json:"executionId"`
              Result []byte `json:"result"`
          }
          var res ResultMessage
          res.ExecutionId = id
          res.Result = nil
          var msgb []byte
          msgb, err := json.Marshal(res)
          if err != nil {
            http.Error(w, "Couldn't marshal result to JSON", http.StatusInternalServerError)
            log.Println("handler: Couldn't marshal result to JSON: ", err)
          } else {
            w.Header().Set("Content-Type", "application/json")
            w.Write(msgb)
          }
        //w.Write([]byte(id))
      } else {
        log.Printf("handler: Result not yet available of execution ID %s, waiting", id)
        ExecutionCond.L.Lock()
        e, ok := ExecutionResults[id]
        ExecutionCond.L.Unlock()
        if !ok {
          m := sync.Mutex{}
          c := sync.NewCond(&m)
          e = &Execution{c,nil,0}
          ExecutionCond.L.Lock()
          ExecutionResults[id] = e
          ExecutionCond.L.Unlock()
        }
        e.cond.L.Lock()
        // Wait on Result
        e.cond.Wait()
        e.cond.L.Unlock()

        // Modify ExecutionResults
        ExecutionCond.L.Lock()
        delete(ExecutionResults, id)
        ExecutionCond.L.Unlock()

        w.Header().Set("Content-Type", "application/json")
        w.Write([]byte(e.msg.Mfnuserdata))
      }
    } else {
      /*msgb,err = res.MarshalJSON()
      if err != nil {
        http.Error(w, "Couldn't marshal result to JSON", http.StatusInternalServerError)
        log.Println("handler: Couldn't marshal result to JSON: ", err)
      } else {
        w.Header().Set("Content-Type", "application/json")
        w.Write(msgb)
      }*/
      w.Header().Set("Content-Type", "application/json")
      w.Write([]byte(res.Mfnuserdata))
    }
    return
  }

  // CHECK CONTENT
  if !strings.Contains(r.Header.Get("Content-type"), "application/json") {
    http.Error(w, "Only accepting JSON for now", http.StatusUnsupportedMediaType)
    return
  }

  // CHECK HEADERS FOR SESSION UPDATES, POST-PARALLEL MESSAGES OR OTHER GLOBAL MESSAGES
  var (
      topic string
      msg MfnMessage
      id string
      is_special_message bool
  )
  actionhdr := r.Header.Get("x-mfn-action")
  actiondata := r.Header.Get("x-mfn-action-data")
  if (actionhdr != "" && actiondata != "") {
      // handle different cases here
      log.Printf("Got a special message: [%s] [%s]", actionhdr, actiondata)
      is_special_message = true
      if (actionhdr == "session-update") {
          log.Printf("New session update message...")

          type ActionMessage struct {
              Topic string `json:"topic"`
              Key string `json:"key"`
              Value string `json:"value"`
              ClientOriginFrontend string `json:"client_origin_frontend"`
          }
          var data ActionMessage
          bactiondata := []byte(actiondata)
          err := json.Unmarshal(bactiondata, &data)
          if err != nil {
              log.Printf("handler: Couldn't unmarshal session update message: %s", err)
              log.Fatal(err)
          }

          log.Printf("Parsed session update message topic: [%s], id: [%s], value: [%s]", data.Topic, data.Key, data.Value)

          topic = data.Topic
          id = data.Key

          msg = MfnMessage{}
          msg.Mfnmetadata = &Metadata{}
          msg.Mfnmetadata.AsyncExecution = async
          msg.Mfnmetadata.ExecutionId = id
          msg.Mfnmetadata.FunctionExecutionId = id
          msg.Mfnmetadata.ClientOriginFrontend = data.ClientOriginFrontend
          msg.Mfnmetadata.TimestampFrontendEntry = float64(time.Now().UnixNano()) / float64(1000000000.0)

          msg.Mfnuserdata = data.Value

          log.Printf("Session update message topic: [%s], id: [%s]", topic, id)

      } else if (actionhdr == "post-parallel") {
          log.Printf("New Post-Parallel update message...")

          type ActionMessage struct {
              Key string `json:"Key"`
              Topic string `json:"Topic"`
              StateAction string `json:"__state_action"`
              AsyncExec bool `json:"__async_execution"`
              CounterValue int `json:"CounterValue"`
              WorkflowInstanceMetadataStorageKey string `json:"WorkflowInstanceMetadataStorageKey"`
          }

          var data ActionMessage
          bactiondata := []byte(actiondata)
          err := json.Unmarshal(bactiondata, &data)
          if err != nil {
              log.Printf("handler: Couldn't unmarshal post parallel message: %s", err)
              log.Fatal(err)
          }

          log.Printf("Parsed post parallel message Topic: [%s], Key: [%s], StateAction: [%s], AsyncExec: [%t], CounterValue: [%d], WorkflowInstanceMetadataStorageKey: [%s]", data.Topic, data.Key, data.StateAction, data.AsyncExec, data.CounterValue, data.WorkflowInstanceMetadataStorageKey)

          topic = data.Topic
          id = data.Key

          msg = MfnMessage{}
          msg.Mfnmetadata = &Metadata{}
          msg.Mfnmetadata.AsyncExecution = data.AsyncExec
          msg.Mfnmetadata.ExecutionId = id
          msg.Mfnmetadata.FunctionExecutionId = id
          msg.Mfnmetadata.TimestampFrontendEntry = float64(time.Now().UnixNano()) / float64(1000000000.0)
          msg.Mfnmetadata.StateAction = data.StateAction

          msg.Mfnuserdata = actiondata

          log.Printf("Post-Parallel message topic: [%s], id: [%s]", topic, id)

      } else if (actionhdr == "post-map") {
          // TODO
      } else if (actionhdr == "global-pub") {
          // TODO
      } else if (actionhdr == "trigger-event") {
        // Treat this as normal workflow invocation, except for the topic name
        // CREATE NEW MfnMessage with a new execution id
        id, err = GenerateExecutionID()
        if err != nil {
          http.Error(w, err.Error(), http.StatusInternalServerError)
          return
        }

        msg = MfnMessage{}
        msg.Mfnmetadata = &Metadata{}
        msg.Mfnmetadata.AsyncExecution = async
        msg.Mfnmetadata.ExecutionId = id
        msg.Mfnmetadata.FunctionExecutionId = id
        msg.Mfnmetadata.ClientOriginFrontend = internalEndpoint
        msg.Mfnmetadata.TimestampFrontendEntry = float64(time.Now().UnixNano()) / float64(1000000000.0)
        body, err := ioutil.ReadAll(r.Body)
        if err != nil {
          log.Println("handler: Error reading body", err)
          http.Error(w, "can't read body", http.StatusBadRequest)
          return
        }
        msg.Mfnuserdata = string(body)
        topic = actiondata
        log.Printf("Trigger-Event message topic: [%s], id: [%s]", topic, id)
    } else if (actionhdr == "remote-result") {
        log.Printf("New remote result message...")

        type ActionMessage struct {
            Key string `json:"key"`
            Value string `json:"value"`
        }
        var data ActionMessage
        bactiondata := []byte(actiondata)
        err := json.Unmarshal(bactiondata, &data)
        if err != nil {
            log.Printf("handler: Couldn't unmarshal remote result message: %s", err)
            log.Fatal(err)
        }

        log.Printf("Parsed remote result message: id: [%s], result: [%s]", data.Key, data.Value)

        valueb := []byte(data.Value)

        msg := MfnMessage{}
        err = msg.UnmarshalJSON(valueb)

        // get the execution context and signal that the result is available
        ExecutionCond.L.Lock()
        e, ok := ExecutionResults[msg.Mfnmetadata.ExecutionId]
        ExecutionCond.L.Unlock()
        if !ok {
            log.Println("handler: Received unknown remote result", string(msg.Mfnmetadata.ExecutionId))
            return
        }
        log.Println("handler: Received remote result for ID", msg.Mfnmetadata.ExecutionId)
        e.cond.L.Lock()
        e.rt_rcvdlq = rt_rcvdlq
        e.msg = &msg
        e.cond.Broadcast()
        e.cond.L.Unlock()

        // this special message doesn't trigger the workflow; therefore, need to stop here
        return
    }
  } else {
      is_special_message = false
      // the headers are not special, so this must be a regular message to trigger a workflow
      // CREATE NEW MfnMessage
      id, err = GenerateExecutionID()
      if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
      }

      msg = MfnMessage{}
      msg.Mfnmetadata = &Metadata{}
      msg.Mfnmetadata.AsyncExecution = async
      msg.Mfnmetadata.ExecutionId = id
      msg.Mfnmetadata.FunctionExecutionId = id
      msg.Mfnmetadata.ClientOriginFrontend = internalEndpoint
      msg.Mfnmetadata.TimestampFrontendEntry = float64(time.Now().UnixNano()) / float64(1000000000.0)
      body, err := ioutil.ReadAll(r.Body)
      if err != nil {
        log.Println("handler: Error reading body", err)
        http.Error(w, "can't read body", http.StatusBadRequest)
        return
      }
      msg.Mfnuserdata = string(body)
      topic = entryTopic
  }

  // SUBMIT MESSAGE INTO SYSTEM
  if async {
    err, _ = SendMessage(msg, topic)
    if err != nil {
      http.Error(w, "Error submitting event to system", http.StatusInternalServerError)
    } else {
        // w.Header().Set("Content-Type", "application/json")
        // w.WriteHeader(http.StatusAccepted)
        // Create entry and lock to wait on
        if !is_special_message {
            m := sync.Mutex{}
            c := sync.NewCond(&m)
            e := Execution{c,nil,0}
            ExecutionCond.L.Lock()
            ExecutionResults[id] = &e
            ExecutionCond.L.Unlock()
        }
        w.Write([]byte(id))
    }
  } else {
    // Create entry and lock to wait on
    m := sync.Mutex{}
    c := sync.NewCond(&m)
    e := Execution{c,nil,0}
    ExecutionCond.L.Lock()
    ExecutionResults[id] = &e
    ExecutionCond.L.Unlock()
    c.L.Lock()
    // Send now that we're able to wait on it
    inFlightRequestsCounterChan <- 1
    err, rt_sendlq = SendMessage(msg, topic)
    rt_sentlq = time.Now().UnixNano()
    if err != nil {
      log.Println("Couldn't send message to LocalQueueService: ", err)
      http.Error(w, "Error submitting event to system", http.StatusInternalServerError)
    } else {
      // Wait on Result
      c.Wait()
      // Marshall result
      //msgb,err = e.msg.MarshalJSON()
      //if err != nil {
      //  log.Println("Couldn't marshal result to JSON: ", err)
      //  log.Fatal(err)
      //}
      rt_rcvdlq = e.rt_rcvdlq
      w.Header().Set("Content-Type", "application/json")
      w.Write([]byte(e.msg.Mfnuserdata))
      rt_exitfe = time.Now().UnixNano()
      inFlightRequestsCounterChan <- -1
      log.Printf(
        `[ResumedUserSession] [ExecutionId] [%s] [Size] [0] [TimestampMap] [{"tfe_entry":%d,"tfe_sendlq":%d,"tfe_sentlq":%d,"tfe_rcvdlq":%d,"tfe_exit":%d}] [LatencyRoundtrip] [%d] [Response] {...}`,
        e.msg.Mfnmetadata.ExecutionId,
        rt_entry / 1000000,
        rt_sendlq / 1000000,
        rt_sentlq / 1000000,
        rt_rcvdlq / 1000000,
        rt_exitfe / 1000000,
        (rt_rcvdlq - rt_sendlq) / 1000000)
    }
    c.L.Unlock()
    // Modify ExecutionResults
    ExecutionCond.L.Lock()
    delete(ExecutionResults, id)
    ExecutionCond.L.Unlock()
  }
}

// GenerateExecutionID generates an mfn exexution id
func GenerateExecutionID() (string, error) {
  var (
    err error
    mid []byte
    id string
  )
  var msgid uuid.UUID
  msgid,err = uuid.NewUUID()
  if err != nil {
    log.Println("handler: Couldn't generate UUID", err)
    return "", errors.New("Can't generate UUID for event")
  }
  mid,err = msgid.MarshalText()
  if err != nil {
    fmt.Println("handler: Couldn't marshal UUID", err)
    log.Fatal(err)
  }
  sid := string(mid)
  bid := make([]byte, 32)
  // copy UUID without dashes (e.g. 1f115d4c-4d08-11ea-b6ed-68b5996bc19c)
  copy(bid[ 0:8],sid[ 0: 8])
  copy(bid[8:12],sid[ 9:13])
  copy(bid[12:16],sid[14:18])
  copy(bid[16:20],sid[19:23])
  copy(bid[20:32],sid[24:36])
  id = string(bid)
  return id, nil
}

// InitDatalayer initializes and connects the datalayer thrift client
func InitDatalayer() {
  log.Print("datalayer: Starting client")
  var err error
  var protocolFactory thrift.TProtocolFactory
  protocolFactory = thrift.NewTCompactProtocolFactory()
  var transportFactory thrift.TTransportFactory
  transportFactory = thrift.NewTTransportFactory()
  transportFactory = thrift.NewTFramedTransportFactory(transportFactory)
  var transport thrift.TTransport
  transport, err = thrift.NewTSocket(os.Getenv("MFN_DATALAYER"))
  if err != nil {
      log.Println("producer: Error opening socket:", err)
      log.Fatal(err)
  }
  datalayerTransport, err = transportFactory.GetTransport(transport)
  if err != nil {
    log.Fatal(err)
  }
  if err := transport.Open(); err != nil {
    log.Fatal(err)
  }
  iprot := protocolFactory.GetProtocol(datalayerTransport)
  oprot := protocolFactory.GetProtocol(datalayerTransport)
  datalayer = datalayerservice.NewDataLayerServiceClient(thrift.NewTStandardClient(iprot, oprot))
}

// FetchResult uses the datalayer to fetch the result of an execution id
func FetchResult(id string) (*MfnMessage, error) {
  // see ../../ManagementService/management_init.py:365
  key := fmt.Sprintf("result_%s", id)
  // LOCALITY = 1 (access global datalayer)
  datalayerMutex.Lock()
  kvp, err := datalayer.SelectRow(datalayerCtx, datalayerKeyspace, datalayerTable, key, 1)
  datalayerMutex.Unlock()
  if err != nil || len(kvp.Value) == 0 {
    return nil, err
  }
  msg := &MfnMessage{}
  err = msg.UnmarshalJSON(kvp.Value)
  return msg, err
}

// InitProducer initialized the producer thrift client and connects it to the local queue service
func InitProducer() {
  fmt.Print("producer: Starting client")
  producer = redis.NewClient(&redis.Options {
          Addr: os.Getenv("MFN_QUEUE"),
          Password: "",
          DB: 0,
  })

  // _XXX_: entry and exit topics are handled by the sandbox agent before
  // launching the frontend, so no need
  //err = producer.AddTopic(producerCtx, entryTopic)
  //if err != nil {
  //  log.Println("producer: Error creating entry topic", entryTopic, err)
  //  log.Fatal(err)
  //}
  fmt.Println("producer: entry topic", entryTopic)
}

func StoreData(msg MfnMessage, msgb []byte) {
  mapName := "execution_info_map_" + msg.Mfnmetadata.ExecutionId
  var kvp *datalayermessage.KeyValuePair
  // WRITE BACKUP input to first function
  kvp = &datalayermessage.KeyValuePair{
    "input_" + msg.Mfnmetadata.ExecutionId + "_"+entryTopic,
    msgb,
  }
  // LOCALITY = 1 (access global datalayer)
  //PutEntryToMap(ctx context.Context, keyspace string, table string, mapName string, keyValuePair *datalayermessage.KeyValuePair, locality int32) (r bool, err error)
  datalayerMutex.Lock()
  res, err := datalayer.PutEntryToMap(datalayerCtx, datalayerKeyspace, datalayerMapTable, mapName, kvp, 1)
  datalayerMutex.Unlock()
  if res == false {
    log.Print("producer: Could not store the workflow trigger input. Something mysterious happened and the result is false, check DataLayerService for more details")
    return
  }
  if err != nil {
    log.Print(err)
    return
  }

  // WRITE NEXT ARRAY
  kvp = &datalayermessage.KeyValuePair{
    "next_" + msg.Mfnmetadata.ExecutionId + "_frontend",
    msgb,
  }
  // LOCALITY = 1 (access global datalayer)
  //PutEntryToMap(ctx context.Context, keyspace string, table string, mapName string, keyValuePair *datalayermessage.KeyValuePair, locality int32) (r bool, err error)
  datalayerMutex.Lock()
  res, err = datalayer.PutEntryToMap(datalayerCtx, datalayerKeyspace, datalayerMapTable, mapName, kvp, 1)
  datalayerMutex.Unlock()
  if res == false {
    log.Print("producer: Could not store next array for workflow start. Something mysterious happened and the result is false, check DataLayerService for more details")
    return
  }
  if err != nil {
    log.Print(err)
    return
  }
}
// Send message accepts an MfnMessage (JSON spec)
// It wraps the JSON MfnMessage in a construct known as LocalQueueClientMessage consisting of 4 bytes length (uint32) denoting the end of key, a key byte string and the actual MfnMessage as byte array
// The byte array is then used as Payload of the LocalQueueMessage and sent to the LocalQueueService
// The function also stores to the datalayer:
// - an execution_info_map of that execution with the message as input to the entry function
// - a next function naming frontend with the message as its value
func SendMessage(msg MfnMessage, topic string) (error, int64) {
  // Marshal JSON
  msgb,err := msg.MarshalJSON()
  if err != nil {
    log.Println("handler: Couldn't marshal message to JSON", err)
    return err, 0
  }

  log.Printf("New execution (id=%s)\n", msg.Mfnmetadata.ExecutionId)

  // Send the local queue message
  producerMutex.Lock()
  rt_sendlq := time.Now().UnixNano()
  _, err = producer.XAdd(producerCtx, &redis.XAddArgs{
                Stream: topic,
                ID:     "*",
                Values: map[string]interface{}{"key": msg.Mfnmetadata.ExecutionId, "value": string(msgb)},
            }).Result()
  producerMutex.Unlock()
  if err != nil {
    return err, rt_sendlq
  }

  go StoreData(msg, msgb)
  return nil, rt_sendlq
}


func Fakeit(msg *MfnMessage) (error) {
  time.Sleep(time.Second * 1)

  // Marshal JSON
  msgb,err := msg.MarshalJSON()
  if err != nil {
    log.Println("handler: Couldn't marshal message to JSON", err)
    return err
  }

  // CHEAT: write input as result for testing
  var kvp *datalayermessage.KeyValuePair
  kvp = &datalayermessage.KeyValuePair{
    "result_" + msg.Mfnmetadata.ExecutionId,
    msgb,
  }
  datalayerMutex.Lock()
  res, err := datalayer.InsertRow(datalayerCtx, datalayerKeyspace, datalayerTable, kvp, 1)
  datalayerMutex.Unlock()
  if res == false {
    return fmt.Errorf("producer: Could not store input as result for testing, see DataLayerService")
  }
  if err != nil {
    return err
  }

  // CHEAT: send message to result queue
  // Assemble local queue message
  // Send the local queue message
  _, err = producer.XAdd(producerCtx, &redis.XAddArgs{
                Stream: resultTopic,
                ID:     "*",
                Values: map[string]interface{}{"key": msg.Mfnmetadata.ExecutionId, "value": string(msgb)},
            }).Result()
  if err != nil {
    return err
  }

  return nil
}

func init() {
    initResourceStats()
}

// The frontend initializes datalayer and producer thrift clients, starts consumer as a go routine, registers a signal handler for graceful shutdowns and blocks at starting the http server
func main() {
  // overwrite the log's default format
  log.SetFlags(0)
  log.SetOutput(new(LogWriter))

  fmt.Println("Frontend starting ...")
  entryTopic  = os.Getenv("MFN_ENTRYTOPIC")
  resultTopic = os.Getenv("MFN_RESULTTOPIC")
  internalEndpoint = os.Getenv("MFN_INTERNAL_ENDPOINT")
  externalEndpoint = os.Getenv("MFN_EXTERNAL_ENDPOINT")
  fmt.Println("consuming results from", resultTopic)
  datalayerKeyspace = "sbox_"+os.Getenv("SANDBOXID")
  datalayerTable = "sbox_default_" + os.Getenv("SANDBOXID")
  datalayerMapTable = "sbox_map_" + os.Getenv("SANDBOXID")
  fmt.Printf("datalayer keyspace=%s, table=%s, maptable=%s\n", datalayerKeyspace, datalayerTable, datalayerMapTable)
  InitDatalayer()
  InitProducer()

  // Init HTTP server
  var listenAddr string
  port := os.Getenv("PORT")
  if port == "" {
    listenAddr = ":8080"
  } else {
    listenAddr = fmt.Sprintf(":%s", port)
  }
  mux := http.NewServeMux()
  mux.HandleFunc("/", handler)
  mux.HandleFunc("/metrics", handle_metrics)
  httpServer = &http.Server{
    Addr:    listenAddr,
    Handler: mux,
  }

  // Start Consumer
  consumerQuit := make(chan bool, 1)
  consumerDone := make(chan bool, 1)
  go ConsumeResults(consumerQuit, consumerDone)

  // Register shutdown sequence
  quit := make(chan os.Signal, 1)
  signal.Notify(quit, os.Interrupt)
  signal.Notify(quit, syscall.SIGTERM)
  done := make(chan bool, 1)
  go func() {
    // Shutdown hook
    <-quit // wait on signal
    log.Println("Server is shutting down...")

    // create a timed out context to gravefully shutdown httpServer in 30 sec
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    // gracefully shutdown http server
    httpServer.SetKeepAlivesEnabled(false)
    if err := httpServer.Shutdown(ctx); err != nil {
      log.Fatalf("Could not gracefully shutdown the server: %v\n", err)
    }

    // shutdown producer
    log.Println("producer: stopping ...")
    // _XXX_: don't remove the entry topic, because the sandbox agent still
    // needs to gracefully shutdown the entry function
    //err := producer.RemoveTopic(producerCtx, entryTopic)
    //if err != nil {
    //  fmt.Println("producer: Error removing entry topic", entryTopic, err)
    //  log.Fatal(err)
    //}
    //fmt.Println("producer: Removed entry topic", entryTopic)
    producer.Close()
    log.Println("producer: stopped")
    // shutdown consumer
    consumerQuit <- true
    log.Println("consumer: stopping ...")
    <-consumerDone
    log.Println("consumer: stopped")
    // shutdown datalayer
    log.Println("datalayer: stopping ...")
    datalayerTransport.Close()
    log.Println("datalayer: stopped")

    close(done)
  }()

  // TODO: not actually listening, this could still fail opening the socket
  fmt.Println("Frontend is ready to handle requests at", listenAddr)
  fErr, err := os.OpenFile("logs/frontend.log", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
  if err != nil {
    log.Fatalf("Could not open log file logs/frontend.log: %v\n", err)
  }
  syscall.Dup2(int(fErr.Fd()), 1) /* -- stdout */
  syscall.Dup2(int(fErr.Fd()), 2) /* -- stderr */
  if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
    log.Fatalf("Could not listen on %s: %v\n", listenAddr, err)
  }
  <-done
  log.Println("Frontend stopped")
}
