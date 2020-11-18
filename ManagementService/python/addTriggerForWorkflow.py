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

import json
import random
import requests
import time

MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

### Utility functions ###
def get_available_frontends(context):
    tf_hosts = context.getMapKeys(MAP_AVAILABLE_FRONTENDS, True)
    return tf_hosts

def is_frontend_registered(context, frontend_ip_port):
    return context.containsMapKey(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, True)

def get_frontend_info(context, frontend_ip_port):
    ret = context.getMapEntry(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, True)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def remove_frontend_info(context, frontend_ip_port):
    print("remove_frontend_info: " + frontend_ip_port)
    context.deleteMapEntry(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, True)

def add_frontend_info(context, frontend_ip_port, entry):
    print("add_frontend_info: " + frontend_ip_port + ", data: " + entry)
    context.putMapEntry(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, entry, True)

def is_trigger_registered(context, trigger_id):
    return context.containsMapKey(MAP_TRIGGERS_TO_INFO, trigger_id, True)

def get_trigger_info(context, trigger_id):
    ret = context.getMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def add_trigger_info(context, trigger_id, data):
    print("add_trigger_info: " + trigger_id + ", data: " + data)
    context.putMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, data, True)

def remove_trigger_info(context, trigger_id):
    print("remove_trigger_info: " + trigger_id)
    context.deleteMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)

def get_user_trigger_list(context, email):
    user_triggers_list = context.get(email + "_list_triggers", True)
    if user_triggers_list is not None and user_triggers_list != "":
        user_triggers_list = json.loads(user_triggers_list)
    else:
        user_triggers_list = {}
    return user_triggers_list

def update_user_trigger_list(context, email, user_trigger_list):
    print("User: " + email + ", Trigger list updates to: " + str(user_trigger_list))
    context.put(email + "_list_triggers", user_trigger_list, True)


### Main entry ###
def handle(value, context):
    assert isinstance(value, dict)
    data = value
    print("[addTriggerForWorkflow] input data: " + str(data))
    status_msg = ""
    trigger_name = ""
    workflow_name = ""
    try:
        if "email" not in data or "trigger_name" not in data or "workflow_name" not in data:
            raise Exception(
                "Couldn't add trigger for workflow; either user email or trigger_name or workflow_name is missing")
        email = data["email"]
        trigger_name = data["trigger_name"]
        workflow_name = data["workflow_name"]
        workflow_state = ""
        if "workflow_state" in data:
            workflow_state = data["workflow_state"]
        storage_userid = data["storage_userid"]
        trigger_id = storage_userid + "_" + trigger_name

        if isTriggerPresent(email, trigger_id, trigger_name, context) == False:
            print("[addTriggerForWorkflow] User: " + email + ", Trigger: " + trigger_name + " not found.")
            raise Exception("[addTriggerForWorkflow] Trigger: " + trigger_name + " not found.")

        # now check if the workflow is present
        isWorkflowPresent, isWorkflowDeployed, workflow_details = isWorkflowPresentAndDeployed(
            email, workflow_name, context)
        if isWorkflowPresent == False:
            print("[addTriggerForWorkflow] User: " + email + "Workflow: " + workflow_name + " not found.")
            raise Exception("[addTriggerForWorkflow] Workflow: " + workflow_name + " not found.")

        if isWorkflowPresent == True:
            # add the trigger name in workflow's metadata
            addTriggerToWorkflowMetadata(email, trigger_name, workflow_name, workflow_state, workflow_details["id"], context)

        if isWorkflowDeployed == True:
            # add the workflow to the trigger
            addWorkflowToTrigger(email, workflow_name, workflow_state, workflow_details, trigger_id, trigger_name, context)

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't add the trigger: " + trigger_name + " for workflow: " + workflow_name + ", error: " + str(e)
        response["data"] = response_data
        print("[addTriggerForWorkflow] Error: " + str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = status_msg
    response["data"] = response_data
    print("[addTriggerForWorkflow] response: " + str(response))
    return response


def isWorkflowPresentAndDeployed(email, workflowname, sapi):
    workflows = sapi.get(email + "_list_workflows", True)
    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
    else:
        workflows = {}

    isWorkflowPresent = False
    isWorkflowDeployed = False
    details = {}
    if workflowname in workflows:
        wf_id = workflows[workflowname]
        wf = sapi.get(email + "_workflow_" + wf_id, True)
        if wf is not None and wf != "":
            isWorkflowPresent = True
            wf = json.loads(wf)
            details["email"] = email
            details["name"] = workflowname
            details["id"] = wf_id
            wf_status = sapi.get("workflow_status_" + wf_id, True)
            details["status"] = wf_status
            if "endpoints" in wf:
                details["endpoints"] = wf["endpoints"]
            if "modified" in wf:
                details["modified"] = wf["modified"]
            if "associatedTriggerableTables" in wf:
                details["associatedTriggerableTables"] = wf["associatedTriggerableTables"]
            if "associatedTriggers" in wf:
                details["associatedTriggers"] = wf["associatedTriggers"]
            if wf["status"] == "deployed" or wf["status"] == "deploying":
                isWorkflowDeployed = True

    return isWorkflowPresent, isWorkflowDeployed, details


def addTriggerToWorkflowMetadata(email, trigger_name, workflow_name, workflow_state, workflow_id, context):
    print("[addTriggerToWorkflowMetadata] called with: trigger_name: " + str(trigger_name) + ", workflow_name: " + str(workflow_name) + ", workflow_state: " + str(workflow_state) + ", workflow_id: " + str(workflow_id))
    wf = context.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        print("[addTriggerToWorkflowMetadata] User: " + email + ", Workflow: " +
              workflow_name + ": couldn't retrieve workflow metadata.")
        raise Exception("[addTriggerToWorkflowMetadata] User: " + email +
                        ", Workflow: " + workflow_name + ": couldn't retrieve workflow metadata.")

    wf = json.loads(wf)
    print("[addTriggerToWorkflowMetadata] User: " + email + ", Workflow: " +
          workflow_name + ": Current workflow metadata: " + str(wf))

    if 'associatedTriggers' not in wf:
        wf['associatedTriggers'] = {}
    associatedTriggers = wf['associatedTriggers']
    if trigger_name not in associatedTriggers:
        associatedTriggers[trigger_name] = workflow_state
        wf['associatedTriggers'] = associatedTriggers
        print("[addTriggerToWorkflowMetadata] updated workflow metadata: " + str(wf))
        context.put(email + "_workflow_" + workflow_id, json.dumps(wf), True)
        print("[addTriggerToWorkflowMetadata] User: " + email +
              ", Trigger: " + trigger_name + " added to Workflow: " + workflow_name)
    else:
        print("[addTableToWorkflowMetadata] User: " + email + ", Trigger: " +
              trigger_name + " already present in Workflow: " + workflow_name)


def deleteTriggerFromWorkflowMetadata(email, trigger_name, workflow_name, workflow_id, context):
    print("[deleteTriggerFromWorkflowMetadata] called with: trigger_name: " + str(trigger_name) + ", workflow_name: " + str(workflow_name) + ", workflow_id: " + str(workflow_id))
    wf = context.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Workflow: " +
              workflow_name + ": couldn't retrieve workflow metadata.")
        #raise Exception("[deleteTriggerFromWorkflowMetadata] User: " + email +
        #                ", Workflow: " + workflow_name + ": couldn't retrieve workflow metadata.")

    wf = json.loads(wf)
    print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Workflow: " +
          workflow_name + ": Current workflow metadata: " + str(wf))

    if 'associatedTriggers' not in wf:
        wf['associatedTriggers'] = {}
    associatedTriggers = wf['associatedTriggers']
    if trigger_name in associatedTriggers:
        del associatedTriggers[trigger_name]
        wf['associatedTriggers'] = associatedTriggers
        context.put(email + "_workflow_" + workflow_id, json.dumps(wf), True)
        print("[deleteTriggerFromWorkflowMetadata] User: " + email +
              ", Trigger: " + trigger_name + " removed from Workflow: " + workflow_name)
    else:
        print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Trigger: " +
              trigger_name + " not present in Workflow: " + workflow_name)


def isTriggerPresent(email, trigger_id, trigger_name, context):
    # check if the global trigger is present
    global_trigger_info = get_trigger_info(context, trigger_id)

    # check if the trigger does not exist in global list
    if global_trigger_info is None:
        return False

    return True


def addWorkflowToTrigger(email, workflow_name, workflow_state, workflow_details, trigger_id, trigger_name, context):
    print("[addWorkflowToTrigger] called with: trigger_id: " + str(trigger_id) + ", trigger_name: " + str(trigger_name) + ", workflow_name: " + str(workflow_name) + ", workflow_state: " + str(workflow_state) + ", workflow_details: " + str(workflow_details))
    status_msg = ""
    try:
        workflow_endpoints = workflow_details["endpoints"]
        if len(workflow_endpoints) == 0:
            raise Exception("[addTriggerForWorkflow] No workflow endpoint available")
        # TODO: [For bare metal clusters] send all workflow endpoints to frontend to let is load balance between wf endpoints. For k8s there will only be one name
        selected_workflow_endpoint = workflow_endpoints[random.randint(0,len(workflow_endpoints)-1)]
        print("[addTriggerForWorkflow] selected workflow endpoint: " + selected_workflow_endpoint)

        workflow_to_add = \
        {
            "workflow_url": selected_workflow_endpoint,
            "workflow_name": workflow_name,
            "workflow_state": workflow_state
        }

        # get the list of available frontends.
        tf_hosts = get_available_frontends(context)
        if len(tf_hosts) == 0:
            raise Exception("[addTriggerForWorkflow] No available TriggersFrontend found")

        # if the frontend with the trigger is available
        global_trigger_info = get_trigger_info(context, trigger_id)
        tf_ip_port = global_trigger_info["frontend_ip_port"]
        if tf_ip_port not in tf_hosts:
            raise Exception("Frontend: " + tf_ip_port + " not available")
        
        tryRemovingFirst(tf_ip_port, trigger_id, workflow_to_add)

        url = "http://" + tf_ip_port + "/add_workflows"
        # send the request and wait for response

        req_obj = {"trigger_id": trigger_id, "workflows": [workflow_to_add]}
        print("[addTriggerForWorkflow] Contacting: " + url + ", with data: " + str(req_obj))
        res_obj = {}
        try:
            res = requests.post(url, json=req_obj)
            if res.status_code != 200:
                raise Exception("status code: " + str(res.status_code) + " returned")
            res_obj = res.json()
        except Exception as e:
            status_msg = "Error: trigger_id" + trigger_id + "," + str(e)
        
        if "status" in res_obj and res_obj["status"].lower() == "success":
            # if success then update the global trigger table to add a new workflow.
            print("[addTriggerForWorkflow] Success response from " + url)
            global_trigger_info["associated_workflows"][workflow_name] = workflow_to_add
            add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))

            status_msg = "[addTriggerForWorkflow] Trigger " + trigger_name + " added successfully to workflow:" + workflow_name + ". Message: " + res_obj["message"]
        else:
            if "message" in res_obj:
                status_msg = status_msg + ", message: " + res_obj["message"]
            status_msg = "[addTriggerForWorkflow] Error: " + status_msg + ", response: " + str(res_obj)
            raise Exception(status_msg)
    except Exception as e:
        print("[addWorkflowToTrigger] exception: " + str(e))
        deleteTriggerFromWorkflowMetadata(email, trigger_name, workflow_name, workflow_details["id"], context)
        raise e


def tryRemovingFirst(tf_ip_port, trigger_id, workflow_to_remove):
    print("[tryRemovingFirst] called with: tf_ip_port: " + str(tf_ip_port) + ", trigger_id: " + str(trigger_id) + ", workflow_to_remove: " + str(workflow_to_remove))
    url = "http://" + tf_ip_port + "/remove_workflows"
    # send the request and wait for response

    req_obj = {"trigger_id": trigger_id, "workflows": [workflow_to_remove]}
    print("Contacting: " + url + ", with data: " + str(req_obj))
    res_obj = {}
    try:
        res = requests.post(url, json=req_obj)
        if res.status_code != 200:
            raise Exception("status code: " + str(res.status_code) + " returned")
        res_obj = res.json()
        print("[tryRemovingFirst] Response from " + url + ", response: " + str(res_obj))
    except Exception as e:
        status_msg = "Error: trigger_id" + trigger_id + "," + str(e)
        print("[tryRemovingFirst] exception: " + status_msg)
