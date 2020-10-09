## TriggersFrontend

Frontend responsible for subscribing to external message queues on behalf of workflows. 

### Running the frontend
Install rust <https://www.rust-lang.org/tools/install> on your linux environment
```bash
./run.sh
```

### Creating an AMQP trigger

Example curl command to create an AMQP trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "type": "amqp",
  "id": "1",
  "workflows": [
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag1"
    },
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag2"
    }
  ],
  "trigger_info": {
    "amqp_addr": "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost",
    "routing_key": "rabbit.routing.key",
    "exchange": "rabbitexchange",
    "durable": true,
    "exclusive": true,
    "auto_ack": true
  }
}' http://localhost:8080/create_trigger
```

### Creating a Timer Trigger

Example curl command to create a timer trigger

```bash
curl -H "Content-Type: application/json" -d \
'{
  "type": "timer",
  "id": "2",
  "workflows": [
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag1"
    },
    {
      "workflow_url": "http://httpbin.org/post",
      "tag": "tag2"
    }
  ],
  "trigger_info": {
    "timer_interval_ms": 1000
  }
}' http://localhost:8080/create_trigger
```

### Deleting a trigger

Example curl command to delete a trigger

```bash
curl -H "Content-Type: application/json" -d '{"id": "1"}' http://localhost:8080/delete_trigger
```

### Messages received at the workflow

The structure of the messages received at the workflow is:

```json
{
    "type": "amqp" or "timer",
    "tag": "<user specified optional tag>",
    "source": "<the topic name if available>",
    "data": "<string data>"
}
```

### Messages sent to the Management workflow

```json
{
    "action":"triggersFrontendStatus",
    "data":{"action":"start" or "status" or "stop" ,
    "self_ip":"10.0.2.15",
    "trigger_status_map":{},
    "trigger_error_map":{}
}
```

more explanations to be added