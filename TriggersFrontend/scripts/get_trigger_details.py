#!/usr/bin/python

import json

def handle(event, context):
    ## To print details of all triggers of the current user
    trigger_details = getTriggerDetails([], context)
    context.log(json.dumps(trigger_details, indent = 4))

    ## To print details of specific triggers of the current user
    #trigger_details = getTriggerDetails(["trigger_name_1", "trigger_name_2"], context)
    #context.log(json.dumps(trigger_details, indent = 4))

    return event

def getTriggerDetails(trigger_names, context):
    message = f"getTriggerDetails: trigger_names: {trigger_names}"
    request = \
        {
            "action": "getTriggerDetails",
            "data": {
                "trigger_names": trigger_names
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    trigger_details = response['data']['trigger_details']
    message = f"{message}, Success"
    print(message)
    return trigger_details
