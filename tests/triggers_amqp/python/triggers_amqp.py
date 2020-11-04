#!/usr/bin/python
#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import time
import json
import base64


workflow_other_json = '''{
	"Comment": "other Workflow",
	"StartAt": "test",
	"States": {
		"test": {
			"Type": "Task",
			"Resource": "triggers_amqp",
			"End": true
		}
	}
}'''

# sample input
#    name of this wf,    nonce,         amqp address,                                                               routing key,    amqp exchange name
# [ "wf_triggers_amqp", "23049823", "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost", "rabbit.routing.key", "rabbitexchange"]

def handle(event, context):
    if type(event) == type([]):
        nonce = event[1]
        print(f"_!_EXPLICIT_START_{nonce}")
        workflowname = event[0]
        trigger_name = nonce
        amqp_addr = event[2]
        routing_key = event[3]
        exchange = event[4]

        try:
            # creating an amqp trigger
            trigger_info = \
            {
                "trigger_type": "amqp", 
                "amqp_addr": amqp_addr, 
                "routing_key": routing_key, 
                "exchange": exchange,    # optional
                "auto_ack": True         # optional
            }
            addTrigger(trigger_name, trigger_info, context)

            time.sleep(1)

            # associating main wf with the trigger
            addTriggerForWorkflow(trigger_name, workflowname, "triggers_amqp_state2", context)
            
            time.sleep(10)

            # associating main wf with the trigger
            deleteTriggerForWorkflow(trigger_name, workflowname, context)

            time.sleep(1)

            # associating main wf with the trigger
            addTriggerForWorkflow(trigger_name, workflowname, "", context)
            
            time.sleep(10)

            # associating main wf with the trigger
            deleteTriggerForWorkflow(trigger_name, workflowname, context)


            deleteTrigger(trigger_name, context)

            time.sleep(3)

        except Exception as e:
            print("Exception: " + str(e))
            deleteTrigger(trigger_name, context)
            time.sleep(3)
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
                print("_!_TRIGGER_START_" + event['trigger_name'] + ";triggers_amqp;" + event['workflow_name'] + ";" + event['source'] + ";" + event['data'])
                time.sleep(1)
        else:
            print("ERROR: received event: " + str(event))
            assert(0)
        return {}


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
    time.sleep(1)

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
    time.sleep(1)

def deleteTriggerForWorkflow(trigger_name, workflowname, context):
    message = f"deleteTriggerForWorkflow Trigger: {trigger_name}"
    status, status_msg = context.deleteTriggerForWorkflow(trigger_name, workflowname)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)
    time.sleep(1)


def deleteTrigger(trigger_name, context):
    message = f"deleteTrigger Trigger: {trigger_name}"
    status, status_msg = context.deleteTrigger(trigger_name)
    if status == None or status == False:
        message = f"{message}, Error: response: {status}, message: {status_msg}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {status}, message: {status_msg}"
        print(message)
    time.sleep(1)



def addWorkflow(workflowname, context):
    message = f"addWorkflow: workflow: {workflowname}"
    request = \
        {
            "action": "addWorkflow",
            "data": {
                "workflow": {"name": workflowname}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    workflow_id = response['data']['workflow']['id']
    message = f"{message}, Success, workflow_id = {workflow_id}"
    print(message)
    return workflow_id


def deleteWorkflow(workflowname, workflow_id, context):
    message = f"deleteWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
        {
            "action": "deleteWorkflow",
            "data": {
                "workflow": {"id": workflow_id}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success"
    print(message)


def uploadWorkflowJSON(workflowname, workflow_id, workflow_json, context):
    message = f"uploadWorkflowJSON: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
        {
            "action": "uploadWorkflowJSON",
            "data": {
                "workflow": {"id": workflow_id, "json": base64.b64encode(workflow_json.encode()).decode()}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def deployWorkflow(workflowname, workflow_id, context):
    message = f"deployWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
        {
            "action": "deployWorkflow",
            "data": {
                "workflow": {"id": workflow_id}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def undeployWorkflow(workflowname, workflow_id, context):
    message = f"undeployWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
        {
            "action": "undeployWorkflow",
            "data": {
                "workflow": {"id": workflow_id}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Status message: {status_message}, Error: Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def retrieveAllWorkflowLogs(workflowname, workflow_id, context):
    message = f"retrieveAllWorkflowLogs: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
        {
            "action": "retrieveAllWorkflowLogs",
            "data": {
                "workflow": {"id": workflow_id}
            }
        }
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)

    workflow_log = response["data"]["workflow"]["log"]
    workflow_log = base64.b64decode(workflow_log).decode()
    workflow_log_lines = workflow_log.split("\n")
    return workflow_log_lines
