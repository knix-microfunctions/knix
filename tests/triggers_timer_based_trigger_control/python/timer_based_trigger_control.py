#!/usr/bin/python
import time
import json

# Sample input to this workflow
# ["triggers_timer_based_trigger_control", "trigger_amqp_to_be_controlled_1", "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost", "rabbit.*.*", "egress_exchange", "trigger_timer_controller_1", 20000]

def handle(event, context):
    if type(event) == type([]):
        print(f"_!_EXPLICIT_START")
        if len(event) >= 7:
            workflowname = str(event[0])
            trigger_name_amqp = str(event[1])
            amqp_addr = str(event[2])
            routing_key = str(event[3])
            exchange = str(event[4])
            trigger_name_timer = str(event[5])
            ttl = int(event[6])
            

            # store the input for the next function's trigger start
            context.put("timer_based_trigger_control_input", json.dumps(event))

            try:
                # creating an amqp trigger
                trigger_info_amqp = \
                {
                    "trigger_type": "amqp", 
                    "amqp_addr": amqp_addr, 
                    "routing_key": routing_key, 
                    "exchange": exchange,    # optional, default "egress_exchange"
                    "with_ack": False,       # optional, default False. False means auto ack
                    "durable": False,        # optional, default False. 
                }

                # creating an amqp trigger
                trigger_info_timer = \
                {
                    "trigger_type": "timer", 
                    "timer_interval_ms": ttl, 
                }

                # create a named amqp trigger
                addTrigger(trigger_name_amqp, trigger_info_amqp, context)

                time.sleep(1)

                # associate a specific workflow state with the named trigger
                addTriggerForWorkflow(trigger_name_amqp, workflowname, "", context)
                
                time.sleep(1)

                # create a named amqp trigger
                addTrigger(trigger_name_timer, trigger_info_timer, context)

                time.sleep(1)

                # associate a specific workflow state with the named trigger
                addTriggerForWorkflow(trigger_name_timer, workflowname, "timer_based_trigger_control_state2", context)
        
            except Exception as e:
                # cleanup
                print("Exception: " + str(e))
                deleteTrigger(trigger_name_amqp, context)
                deleteTrigger(trigger_name_timer, context)
                context.delete("timer_based_trigger_control_input")
                time.sleep(1)
        return event
    else:
        if type(event) == type({}) \
            and 'trigger_status' in event \
            and 'trigger_type' in event \
            and 'trigger_name' in event \
            and 'workflow_name' in event \
            and 'source' in event \
            and 'data' in event:
                assert(event["trigger_type"] == "amqp")
                assert(event["trigger_status"] == "ready" or event["trigger_status"] == "error")
                if event["trigger_status"] == "ready":
                    print("_!_TRIGGER_START_" + event['trigger_name'] + ";timer_based_trigger_control;" + event['workflow_name'] + ";" + event['source'] + ";" + event['data'])
                else:
                    # if there is an error while the trigger was already running. The 'data' field will contain an error message
                    print("_!_TRIGGER_ERROR_" + event['trigger_name'] + ";timer_based_trigger_control;" + event['workflow_name'] + ";" + event['source'] + ";" + event['data'])
        else:
            print("ERROR: received event: " + str(event))
            assert(0)
        return []


def addTrigger(trigger_name, trigger_info, context):
    message = f"addTrigger Trigger: {trigger_name}"
    status, status_msg = context.addTrigger(trigger_name, trigger_info)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)

def addTriggerForWorkflow(trigger_name, workflowname, workflow_state, context):
    message = f"addTriggerForWorkflow Trigger: {trigger_name}"
    status, status_msg = context.addTriggerForWorkflow(trigger_name, workflowname, workflow_state)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)

def deleteTriggerForWorkflow(trigger_name, workflowname, context):
    message = f"deleteTriggerForWorkflow Trigger: {trigger_name}"
    status, status_msg = context.deleteTriggerForWorkflow(trigger_name, workflowname)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        #raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)


def deleteTrigger(trigger_name, context):
    message = f"deleteTrigger Trigger: {trigger_name}"
    status, status_msg = context.deleteTrigger(trigger_name)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        #raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)
