## TriggersFrontend

Frontend responsible for subscribing to external message queues on behalf of workflows. 

### Running the frontend
```bash
make
./run.sh
```

### Creating a Trigger 

Send a `POST` request to: `http://[trigger_frontend_host]:[port]/create_trigger` with the following json body:
```
{
  "type": "amqp" or "timer",
  // id is a knix management provided unique string to identify the trigger
  "id": "<string>",
  // trigger_info is an object containing type specific information on how to subscribe to the queue
  "trigger_info": {
    ...
  }
  // workflows is a list of workflows associated with this trigger
  "workflows": [
    {
      // url of the workflow
      "workflow_url": "<string>",
      // workflow developer provided unique string to be included in each workflow invocation
      "tag": "<string>"
    }
    ...
  ]
}
```

All response from the TriggersFrontend have the form:
```
{
  "status": "Success" or "Failure",
  "message": "<string>"
}
```

### Creating an AMQP trigger

Example curl command to create an AMQP trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "type": "amqp",
  "id": "1",
  "trigger_info": {
    "amqp_addr": "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost",
    "routing_key": "rabbit.routing.key",
    "exchange": "rabbitexchange",
    "durable": true,
    "exclusive": true,
    "auto_ack": true
  },
  "workflows": [
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag1"
    },
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag2"
    }
  ]
}' http://localhost:8080/create_trigger
```

### Creating a Timer Trigger

Example curl command to create a timer trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "type": "timer",
  "id": "2",
  "trigger_info": {
    "timer_interval_ms": 1000
  },
  "workflows": [
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag1"
    },
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag2"
    }
  ]
}' http://localhost:8080/create_trigger
```

### Deleting a trigger

Example curl command to delete a trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "id": "1"
}' http://localhost:8080/delete_trigger
```

### Adding more workflows to a Trigger 

Send a `POST` request to: `http://[trigger_frontend_host]:[port]/add_workflows` with the following json body:
```
{
  // id is a knix management provided unique string to identify the trigger
  "id": "<string>",
  // workflows is a list of workflows associated with this trigger
  "workflows": [
    {
      // url of the workflow
      "workflow_url": "<string>",
      // workflow developer provided unique string to be included in each workflow invocation
      "tag": "<string>"
    }
    ...
  ]
}
```

### Removing workflows to a Trigger 

Send a `POST` request to: `http://[trigger_frontend_host]:[port]/remove_workflows` with the following json body:
```
{
  // id is a knix management provided unique string to identify the trigger
  "id": "<string>",
  // workflows is a list of workflows associated with this trigger
  "workflows": [
    {
      // url of the workflow
      "workflow_url": "<string>",
      // workflow developer provided unique string to be included in each workflow invocation
      "tag": "<string>"
    }
    ...
  ]
}
```

### Trigger Messages received at the workflow

The structure of the trigger messages received at the workflow is:

```
{
    "trigger_type": "amqp" or "timer",
    //id is a globally unique identifier for this trigger. To be used for updating and deleting the trigger
    "id": <string>
    //tag is a user specified optional string while creating the trigger
    "tag": "<string>",
    // source is the topic name if available
    "source": "<string>",
    "data": "<string>"
}
```


### Messages sent to the Management workflow

```
{
    "action":"triggersFrontendStatus",
    "data":{
      "action":"start" or "status" or "stop" ,
      "self_ip_port":"10.0.2.15:4997",
      // Status information about the active triggers
      // Status should ideally be always "Ready", but it can also be "Starting", "Stopping", "StoppedNormal"
      "trigger_status_map":{"<trigger_id>" : "trigger_id_status", "<trigger_id>" : "trigger_id_status", ...},
      // Status information about trigger that stopped abonormally on their own
      "trigger_error_map":{"<trigger_id>" : "trigger_id_error_message", "<trigger_id>" : "trigger_id_error_message"}
    }
}
```

more explanations to be added