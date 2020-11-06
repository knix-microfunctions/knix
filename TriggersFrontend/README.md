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
  "trigger_type": "amqp" or "timer",
  // trigger_id is a knix management provided globally unique string to identify the trigger
  "trigger_id": "<string>",
  // trigger_name_user is a knix user provided name for this trigger. Will be included in each event
  "trigger_name": "<string>"
  // trigger_info is an object containing type specific information on how to subscribe to the queue
  "trigger_info": {
    ...
  }
}
```

All response from the TriggersFrontend have the form:
```
{
  "status": "Success" or "Failure",
  "message": "<string>"
}
```

### Adding workflows to a Trigger 

Send a `POST` request to: `http://[trigger_frontend_host]:[port]/add_workflows` with the following json body:
```
{
  // trigger_id is a knix management provided unique string to identify the trigger
  "trigger_id": "<string>",
  // workflows is a list of workflows associated with this trigger
  "workflows": [
    {
      // url of the workflow
      "workflow_url": "<string>",
      // name of the workflow
      "workflow_name": "<string>",
      // name of the state within the workflow to invoke. Could be left blank to invoke the workflow's starting state
      "workflow_state": ""
    }
    ...
  ]
}
```


### Removing workflows from a Trigger 

Send a `POST` request to: `http://[trigger_frontend_host]:[port]/remove_workflows` with the following json body:
```
{
  // id is a knix management provided unique string to identify the trigger
  "trigger_id": "<string>",
  "workflows": [
    {
      // url of the workflow
      "workflow_url": "<string>",
      // name of the workflow
      "workflow_name": "<string>"
    }
    ...
  ]
}
```

### Creating an AMQP trigger

Example curl command to create an AMQP trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "trigger_type": "amqp",
  "trigger_id": "1",
  "trigger_name": "user_provided_name_for_trigger",
  "trigger_info": {
    "amqp_addr": "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost",
    "routing_key": "rabbit.*.*",
    "exchange": "egress_exchange",
    "with_ack": false,
    "durable": false,
    "exclusive": false
  }
}' http://localhost:4997/create_trigger
```

### Creating a Timer Trigger

Example curl command to create a timer trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "trigger_type": "timer",
  "trigger_id": "2",
  "trigger_name": "user_provided_name_for_trigger",
  "trigger_info": {
    "timer_interval_ms": 1000
  }
}' http://localhost:8080/create_trigger
```

### Deleting a trigger

Example curl command to delete a trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "trigger_id": "1"
}' http://localhost:8080/delete_trigger
```



### Trigger Messages received at the workflow

The structure of the trigger messages received at the workflow is:

```
{
    "trigger_status": "ready" or "error",
    "trigger_type": "amqp" or "timer",
    //trigger_name unique identifier for this trigger provided by the user
    "trigger_name": "<string>"
    // workflow_name is the name of the workflow being invoked
    "workflow_name": "<string>"
    // source is the topic name if available
    "source": "<string>",
    // if status is 'ready' then 'data' contains the actual data received. if status is 'error' then 'data' will contain an error message.
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

#### TODOs:
* Invoke a specific state (need to set headers)
* If there is an a runtime error then invoke workflow with error message