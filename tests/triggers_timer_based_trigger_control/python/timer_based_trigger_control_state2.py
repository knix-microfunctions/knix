import time
import json

def handle(event, context):
    if type(event) == type([]):
        print(f"_!_EXPLICIT_START")
        if len(event) >= 7:
            # ensure that the input data has been stored in the datalayer
            try:
                input_data = context.get("timer_based_trigger_control_input")
                input_data = json.loads(input_data)
                assert(event == input_data)
                print("Stored input data: " + str(input_data))
            except Exception as e:
                print("Exception: " + str(e))
                raise e
        return event
    else:
        if type(event) == type({}) \
            and 'trigger_status' in event \
            and 'trigger_type' in event \
            and 'trigger_name' in event \
            and 'workflow_name' in event \
            and 'source' in event \
            and 'data' in event:
                assert(event["trigger_type"] == "timer")
                assert(event["trigger_status"] == "ready" or event["trigger_status"] == "error")
                input_data = context.get("timer_based_trigger_control_input")
                input_data = json.loads(input_data)
                if event["trigger_status"] == "ready":
                    print("_!_TRIGGER_START_" + event['trigger_name'] + ";timer_based_trigger_control_state2;" + event['workflow_name'] + ";" + event['source'] + ";")
                    deleteTrigger(input_data[1], context)
                    deleteTrigger(event['trigger_name'], context)
                    context.delete("timer_based_trigger_control_input")
                else:
                    # if there is an error while the trigger was already running. The 'data' field will contain an error message
                    print("_!_TRIGGER_ERROR_" + event['trigger_name'] + ";timer_based_trigger_control_state2;" + event['workflow_name'] + ";" + event['source'] + ";")
                    raise Exception("Timer trigger error")
        else:
            print("ERROR: received event: " + str(event))
            assert(0)
        return []


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
    time.sleep(1)
