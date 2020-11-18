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
    print("[DeleteTrigger] input data: " + str(data))
    status_msg = ""
    try:
        if "email" not in data or "trigger_name" not in data:
            raise Exception(
                "Couldn't delete trigger; either user email or trigger_name is missing")
        email = data["email"]
        trigger_name = data["trigger_name"]
        storage_userid = data["storage_userid"]
        trigger_id = storage_userid + "_" + trigger_name

        # check the global list for the trigger
        global_trigger_info = get_trigger_info(context, trigger_id)
        
        # check the user's storage area for the trigger name
        user_triggers_list = get_user_trigger_list(context, email)

        tf_ip_port = ""
        if global_trigger_info is not None:
            # we know about the trigger. delete it
            try:
                # get the list of available frontends. Select one
                tf_hosts = get_available_frontends(context)
                if len(tf_hosts) == 0:
                    raise Exception("[DeleteTrigger] No available TriggersFrontend found")
                tf_ip_port = global_trigger_info["frontend_ip_port"]
                if tf_ip_port not in tf_hosts:
                    raise Exception("[DeleteTrigger] Frontend: " + tf_ip_port + " not available")

                # send the request and wait for response
                url = "http://" + tf_ip_port + "/delete_trigger"
                res_obj = {}
                try:
                    res = requests.post(url, json={"trigger_id": trigger_id})
                    if res.status_code != 200:
                        raise Exception("[DeleteTrigger] status code: " + str(res.status_code) + " returned")
                    res_obj = res.json()
                except Exception as e:
                    status_msg = "[DeleteTrigger] Error: trigger_id" + trigger_id + "," + str(e)
                
                if "status" in res_obj and res_obj["status"].lower() == "success":
                    # remove the trigger_id from frontend map
                    frontend_info = get_frontend_info(context, tf_ip_port)
                    if frontend_info is not None and trigger_id in frontend_info:
                        del frontend_info[trigger_id]
                        add_frontend_info(context, tf_ip_port, json.dumps(frontend_info))

                    associated_workflows = global_trigger_info["associated_workflows"]
                    for associated_workflow_name in associated_workflows:
                        removeTriggerFromWorkflowAndUpdateWorkflowMetadata(email, trigger_name, trigger_id, associated_workflow_name, context)

                    remove_trigger_info(context, trigger_id)

                    # add the trigger_name to user's list of triggers
                    if user_triggers_list is not None and trigger_name in user_triggers_list:
                        del user_triggers_list[trigger_name]
                        update_user_trigger_list(context, email, json.dumps(user_triggers_list))
                    
                    # write the user's list
                    status_msg = "Trigger deleted successfully. Message: " + res_obj["message"]
                else:
                    if "message" in res_obj:
                        status_msg = status_msg + ", message: " + res_obj["message"]
                    status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
                    raise Exception(status_msg)

            except Exception as e:
                if tf_ip_port is not "":
                    frontend_info = get_frontend_info(context, tf_ip_port)
                    if frontend_info is not None and trigger_id in frontend_info:
                        del frontend_info[trigger_id]
                        add_frontend_info(context, tf_ip_port, json.dumps(frontend_info))

                associated_workflows = global_trigger_info["associated_workflows"]
                for associated_workflow_name in associated_workflows:
                    removeTriggerFromWorkflowAndUpdateWorkflowMetadata(email, trigger_name, trigger_id, associated_workflow_name, context)

                remove_trigger_info(context, trigger_id)

                # add the trigger_name to user's list of triggers
                if user_triggers_list is not None and trigger_name in user_triggers_list:
                    del user_triggers_list[trigger_name]
                    update_user_trigger_list(context, email, json.dumps(user_triggers_list))
                raise e

        else:
            if user_triggers_list is not None and trigger_name in user_triggers_list:
                del user_triggers_list[trigger_name]
                update_user_trigger_list(context, email, json.dumps(user_triggers_list))
            status_msg = "Could not find Trigger " + trigger_name


    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't delete the trigger; " + str(e)
        response["data"] = response_data
        print("[DeleteTrigger] Error: " + str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = status_msg
    response["data"] = response_data
    print("[DeleteTrigger] response: " + str(response))
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


def deleteTriggerFromWorkflowMetadata(email, trigger_name, workflow_name, workflow_id, context):
    wf = context.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Workflow: " +
              workflow_name + ": couldn't retrieve workflow metadata.")
        raise Exception("[deleteTriggerFromWorkflowMetadata] User: " + email +
                        ", Workflow: " + workflow_name + ": couldn't retrieve workflow metadata.")

    wf = json.loads(wf)
    print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Workflow: " +
          workflow_name + ": Current workflow metadata: " + str(wf))

    if 'associatedTriggers' not in wf:
        wf['associatedTriggers'] = {}
    associatedTriggers = wf['associatedTriggers']
    if trigger_name in associatedTriggers:
        del associatedTriggers[trigger_name]
        wf['associatedTriggers'] = associatedTriggers
        wf = context.put(email + "_workflow_" + workflow_id, json.dumps(wf), True)
        print("[deleteTriggerFromWorkflowMetadata] User: " + email +
              ", Trigger: " + trigger_name + " removed from Workflow: " + workflow_name)
    else:
        print("[deleteTriggerFromWorkflowMetadata] User: " + email + ", Trigger: " +
              trigger_name + " not present in Workflow: " + workflow_name)


def removeTriggerFromWorkflowAndUpdateWorkflowMetadata(email, trigger_name, trigger_id, workflow_name, context):
    status_msg = ""
    try:
        removeTriggerFromWorkflow(trigger_name, trigger_id, workflow_name, context)
    except Exception as e:
        status_msg = status_msg + ", " + str(e)
    finally:
        isWorkflowPresent, isWorkflowDeployed, workflow_details = isWorkflowPresentAndDeployed(
            email, workflow_name, context)
        
        try:
            if isWorkflowPresent == True:
                # add the trigger name in workflow's metadata
                deleteTriggerFromWorkflowMetadata(
                    email, trigger_name, workflow_name, workflow_details["id"], context)
        except Exception as e:
            status_msg = status_msg + ", " + str(e)

    return status_msg


def removeTriggerFromWorkflow(trigger_name, trigger_id, workflow_name, context):
    status_msg = ""
    global_trigger_info = get_trigger_info(context, trigger_id)
    try:
        workflow_to_remove = global_trigger_info["associated_workflows"][workflow_name]

        # get the list of available frontends.
        tf_hosts = get_available_frontends(context)
        if len(tf_hosts) == 0:
            raise Exception("No available TriggersFrontend found")

        # if the frontend with the trigger is available
        tf_ip_port = global_trigger_info["frontend_ip_port"]
        if tf_ip_port not in tf_hosts:
            raise Exception("Frontend: " + tf_ip_port + " not available")
        
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
        except Exception as e:
            status_msg = "Error: trigger_id" + trigger_id + "," + str(e)
        
        if "status" in res_obj and res_obj["status"].lower() == "success":
            # if success then update the global trigger table to add a new workflow.
            print("Success response from " + url)
            if workflow_name in global_trigger_info["associated_workflows"]:
                del global_trigger_info["associated_workflows"][workflow_name]
            add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))
            status_msg = "Trigger " + trigger_name + " removed successfully from workflow:" + workflow_name + ". Message: " + res_obj["message"]
        else:
            if "message" in res_obj:
                status_msg = status_msg + ", message: " + res_obj["message"]
            status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
            raise Exception(status_msg)

    except Exception as e:
        if workflow_name in global_trigger_info["associated_workflows"]:
            del global_trigger_info["associated_workflows"][workflow_name]
            add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))
        raise e
