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
import time
import requests
from requests.api import head

MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

def handle(value, context):
    assert isinstance(value, dict)
    data = value
    action = data["action"].lower()
    frontend_ip_port = data["self_ip_port"]
    trigger_status_map = data["trigger_status_map"]
    trigger_error_map = data["trigger_error_map"]

    response = {}
    response_data = {}
    errmsg = ""

    if action == "start":
        handle_start(frontend_ip_port, trigger_status_map, trigger_error_map, context)
        success = True
        response_data["message"] = "Triggers Frontend registered with Management service."
    elif action == "status":
        handle_status(frontend_ip_port, trigger_status_map, trigger_error_map, context)
        success = True
        response_data["message"] = "Triggers Frontend updated successfully."
    elif action == "stop":
        handle_stop(frontend_ip_port, trigger_status_map, trigger_error_map, context)
        success = True
        response_data["message"] = "Triggers Frontend stopped successfully."
    else:
        success = False
        errmsg = "Unknown action: " + str(action)

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"
        response_data["message"] = errmsg
    response["data"] = response_data
    return response

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

def get_trigger_info_dlc(dlc, trigger_id):
    ret = dlc.getMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)


def add_trigger_info(context, trigger_id, data):
    print("add_trigger_info: " + trigger_id + ", data: " + data)
    context.putMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, data, True)

def add_trigger_info_dlc(dlc, trigger_id, data):
    print("add_trigger_info: " + trigger_id + ", data: " + data)
    dlc.putMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, data)

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


# called when a frontend starts
def handle_start(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [START] frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))


    assert(len(trigger_status_map) == 0) # frontend should not be running anything yet
    assert(len(trigger_error_map) == 0) # frontend should not be running anything yet

    pending_triggers = []
    frontend_available = is_frontend_registered(context, frontend_ip_port)
    if frontend_available:
        print("Frontend already registered, but it is reporting that it is starting!!")
        # we have the frontend already registered with us. Why is it starting again,
        # without telling us that it stopped? Maybe because the stop message did not reach us?
        # check if we have any triggers that we think should be active, 
        # and were earlier assigned to this frontend which has just started up
        # such triggers will have to be re-assigned

        '''
        frontend_info = get_frontend_info(context, frontend_ip_port) # list of trigger ids that were earlier assigned to the frontend
        for trigger_id in frontend_info:
            trigger_info = get_trigger_info(context, trigger_id)
            if trigger_info is not None:
                if trigger_info["frontend_ip_port"] == frontend_ip_port:
                    # we have a registered trigger which we think is ready, but the corresponding frontend just restarted
                    if trigger_info["status"] == "ready" or trigger_info["status"] == "starting":
                        pending_triggers.append(trigger_info)
                    remove_trigger_info(context, trigger_id)
                else:
                    # trigger is registered with a different frontend?
                    print("Trigger_id " + trigger_id + " is already registered with a different frontend: " + trigger_info["frontend_ip_port"])
            else:
                # the trigger is not registered with us. do nothing
                print("Reported trigger_id: " + trigger_id + " not registered with management")

        remove_frontend_info(context, frontend_ip_port)
        '''

    new_frontend_entry = '{}'
    add_frontend_info(context, frontend_ip_port, new_frontend_entry)

    if len(pending_triggers) > 0:
        inform_workflows_for_triggers(pending_triggers)


def handle_status(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [STATUS], frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))
    pending_triggers = []
    frontend_available = is_frontend_registered(context, frontend_ip_port)
    if frontend_available:
        # we know about this frontend
        frontend_info = get_frontend_info(context, frontend_ip_port)
        assert(frontend_info is not None)
        print("Known frontend with data: " + str(frontend_info))

        # first check if any trigger has stopped unexpectedly, and check if we had this trigger registered with us
        # if so, then remove this trigger from our known list and put them in pending list

        for error_trigger_id in trigger_error_map:
            error_trigger_info = get_trigger_info(context, error_trigger_id)
            if error_trigger_id in frontend_info and error_trigger_info is not None:
                if error_trigger_info["status"] == "ready" or error_trigger_info["status"] == "starting":
                    pending_triggers.append((error_trigger_info, trigger_error_map[error_trigger_id]))

        '''
        for error_trigger_id in trigger_error_map:
            error_trigger_info = get_trigger_info(context, error_trigger_id)
            if error_trigger_id in frontend_info and error_trigger_info is not None:
                if error_trigger_info["status"] == "ready" or error_trigger_info["status"] == "starting":
                    pending_triggers.append(error_trigger_info)
            remove_trigger_info(context, error_trigger_id)
            if error_trigger_id in frontend_info:
                print("Removing error_trigger_id: " + error_trigger_id + " from frontend_info")
                del frontend_info[error_trigger_id]

        # for any trigger that stopped normally and is listed with us, remove it from our list
        for (trigger_id, trigger_status) in trigger_status_map.items():
            trigger_status = trigger_status.lower()
            trigger_info = get_trigger_info(context, trigger_id)
            if trigger_status == "stoppednormal" or trigger_status == "stopping":
                remove_trigger_info(context, trigger_id)
                if trigger_id in frontend_info:
                    print("Removing trigger_id: " + trigger_id + " from frontend_info")
                    del frontend_info[trigger_id]
            elif trigger_info is not None:
                assert(trigger_info["frontend_ip_port"] == frontend_ip_port)
                if trigger_info["status"].lower() == "starting" and trigger_status == "ready":
                    trigger_info["status"] = trigger_status
                    add_trigger_info(context, trigger_id, json.dumps(trigger_info))

        # any trigger that is known to be active for us, but not in the reported list, should also be
        # added to pending list
        for known_trigger_id in frontend_info:
            know_trigger_info = get_trigger_info(context, known_trigger_id)
            assert(know_trigger_info is not None)
            assert(know_trigger_info["frontend_ip_port"] == frontend_ip_port)
            if know_trigger_info["status"] == "ready" or know_trigger_info["status"] == "starting":
                if known_trigger_id not in trigger_status_map:
                    pending_triggers.append(know_trigger_info)

        add_frontend_info(context, frontend_ip_port, frontend_info)
        # now process the pending list, to add triggers to available frontends
        '''
        if len(pending_triggers) > 0:
            inform_workflows_for_triggers(pending_triggers, context)

        if len(pending_triggers) > 0:
            removeTriggerAndWorkflowAssociations(pending_triggers, context)

    else:
        # we don't know about this frontend. Ideally it should not have any triggers
        print("Unknown frontend sending a status update!!")
        new_frontend_entry = '{}'

        # add all the triggers in the reported list to our list of triggers associated with frontend
        # also make sure that those triggers exist in the larger trigger map
        '''
        for (trigger_id, trigger_status) in trigger_status_map.items():
            trigger_status = trigger_status.lower()
            trigger_info = get_trigger_info(context, trigger_id)
            if trigger_info is not None:
                assert(trigger_info["frontend_ip_port"] == frontend_ip_port)
                if trigger_info["status"] != trigger_status:
                    trigger_info["status"] = trigger_status
                    add_trigger_info(context, trigger_id, json.dumps(trigger_info))
                new_frontend_entry[trigger_id] = ""
            else:
                # we dont have the triggered registerd with us but a frontend has it running!
                pass
        '''
        add_frontend_info(context, frontend_ip_port, json.dumps(new_frontend_entry))

def handle_stop(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [STOP], frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))
    assert(len(trigger_status_map) == 0)
    pending_triggers = []
    frontend_info = get_frontend_info(context, frontend_ip_port)
    assert(frontend_info is not None)

    for error_trigger_id in trigger_error_map:
        error_trigger_info = get_trigger_info(context, error_trigger_id)
        if error_trigger_id in frontend_info and error_trigger_info is not None:
            if error_trigger_info["status"] == "ready" or error_trigger_info["status"] == "starting":
                pending_triggers.append((error_trigger_info, trigger_error_map[error_trigger_id]))

    if len(pending_triggers) > 0:
        inform_workflows_for_triggers(pending_triggers, context)

    if len(pending_triggers) > 0:
        removeTriggerAndWorkflowAssociations(pending_triggers, context)

    remove_frontend_info(context, frontend_ip_port)


def inform_workflows_for_triggers(pending_triggers, context):
    for (trigger_info, error_msg) in pending_triggers:
        print("[inform_workflows_for_triggers] for trigger: " + str(trigger_info))
        frontend_command_info = trigger_info["frontend_command_info"]
        associated_workflows = trigger_info["associated_workflows"]
        for workflow_name in associated_workflows:
            workflow_info = associated_workflows[workflow_name]
            request_obj = { \
                "trigger_status": "error", 
                "trigger_type": frontend_command_info["trigger_type"], 
                "trigger_name": frontend_command_info["trigger_name"],
                "workflow_name": workflow_name,
                "source": "",
                "data": error_msg
            }
            url = workflow_info["workflow_url"]
            workflow_state = workflow_info["workflow_state"]
            execute_workflow(url, request_obj, workflow_state)


def removeTriggerAndWorkflowAssociations(pending_triggers, context):
    for (trigger_info, error_msg) in pending_triggers:        
        removeTriggerFromFrontend(trigger_info, context)

        removeTriggerFromWorkflow(trigger_info, context)

        remove_trigger_info(context, trigger_info["trigger_id"])


def removeTriggerFromFrontend(trigger_info, context):
    print("[removeTriggerFromFrontend] for trigger: " + str(trigger_info))
    trigger_id = trigger_info["trigger_id"]
    frontend_ip_port = trigger_info["frontend_ip_port"]

    # remove the trigger_id from frontend map
    frontend_info = get_frontend_info(context, frontend_ip_port)
    assert(frontend_info is not None)
    if trigger_id in frontend_info:
        del frontend_info[trigger_id]
    add_frontend_info(context, frontend_ip_port, json.dumps(frontend_info))


def removeTriggerFromWorkflow(trigger_info,context):
    print("[removeTriggerFromWorkflow] for trigger: " + str(trigger_info))
    associated_workflows = trigger_info["associated_workflows"]
    email = trigger_info["email"]
    trigger_name = trigger_info["trigger_name"]
    storage_userid = trigger_info["storage_userid"]
    trigger_id = trigger_info["trigger_id"]

    status_msg = ""

    # do the delete trigger processing
    #dlc = context.get_privileged_data_layer_client(suid=storage_userid, is_wf_private=True)

    for associated_workflow_name in associated_workflows:
        del trigger_info["associated_workflows"][associated_workflow_name]
        add_trigger_info(context, trigger_id, json.dumps(trigger_info))

        isWorkflowPresent, isWorkflowDeployed, workflow_details = isWorkflowPresentAndDeployed(email, associated_workflow_name, context)
        print("associated_workflow_name: " + associated_workflow_name + ", isWorkflowPresent: " + str(isWorkflowPresent) + ", details: " + str(workflow_details))
        try:
            if isWorkflowPresent == True:
                # add the trigger name in workflow's metadata
                deleteTriggerFromWorkflowMetadata(email, trigger_name, associated_workflow_name, workflow_details["id"], context)
        except Exception as e:
            status_msg = str(e)
            print("[removeTriggerFromWorkflow] exeception: " + status_msg)
    
    # check the user's storage area for the trigger name
    user_triggers_list = get_user_trigger_list(context, email)
    print("user_triggers_list = " + str(user_triggers_list))

    if trigger_name in user_triggers_list:
        del user_triggers_list[trigger_name]
    update_user_trigger_list(context, email, json.dumps(user_triggers_list))

    return status_msg


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

def execute_workflow(wfurl, wfinput, wfstate):
    result = None
    headers = {"x-mfn-action": "trigger-event", "x-mfn-action-data": wfstate}
    res = None
    try:
        if wfstate == "":
            print("[execute_workflow] url: " + str(wfurl) + ", data: " + str(wfinput))
            res = requests.post(wfurl, params={}, json=wfinput)
        else:
            print("[execute_workflow] url: " + str(wfurl) + ", headers: " + str(headers) + ", data: " + str(wfinput))
            res = requests.post(wfurl, params={}, json=wfinput, headers=headers)

        print("[execute_workflow] status: " + str(res.status_code))

    except Exception as exc:
        print("Execute workflow error: " + str(exc))