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
import random 

MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"
SET_PENDING_TRIGGERS = "pending_triggers_set"

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
    print("get_frontend_info: data: " + str(ret))
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

def add_to_global_pending_trigger_set(context, entry):
    print("add_to_global_pending_trigger_set: data: " + str(entry))
    context.addSetEntry(SET_PENDING_TRIGGERS, entry, True)

def remove_from_global_pending_trigger_set(context, entry):
    print("remove_from_global_pending_trigger_set: data: " + str(entry))
    context.removeSetEntry(SET_PENDING_TRIGGERS, entry, True)

def get_global_pending_trigger_set(context):
    items = []
    items_ret = context.retrieveSet(SET_PENDING_TRIGGERS, True)
    if items_ret is not None:
        items = list(items_ret)
        print("get_global_pending_trigger_set: data: " + str(items))
    else:
        print("get_global_pending_trigger_set: data: None")
    return items

def clear_global_pending_trigger_set(context):
    context.clearSet(SET_PENDING_TRIGGERS, True)
    print("clear_global_pending_trigger_set")


# called when a frontend starts
def handle_start(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [START] frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))


    assert(len(trigger_status_map) == 0) # frontend should not be running anything yet
    assert(len(trigger_error_map) == 0) # frontend should not be running anything yet

    frontend_available = is_frontend_registered(context, frontend_ip_port)
    triggers_to_recreate = []
    triggers_to_inform_and_remove = []

    if frontend_available:
        print("Frontend already registered, but it is reporting that it is starting!!")
        # we have the frontend already registered with us. Why is it starting again,
        # without telling us that it stopped? Maybe because the stop message did not reach us?
        # check if we have any triggers that we think should be active, 
        # and were earlier assigned to this frontend which has just started up
        # such triggers will have to be re-assigned

        print("[handle_start] First removing information about the old frontend with same ip: " + frontend_ip_port)
        frontend_info = get_frontend_info(context, frontend_ip_port)

        for trigger_id in frontend_info:
            trigger_info = get_trigger_info(context, trigger_id)
            if trigger_info is not None and trigger_info["frontend_ip_port"] == frontend_ip_port:
                if trigger_info["status"].lower() == "ready":
                    triggers_to_recreate.append((trigger_info, ""))
                else:
                    triggers_to_inform_and_remove.append((trigger_info, "Associated Triggers Frontend not active"))
            else:
                # this trigger is now associated with a different frontend, simply remove information
                pass
        
        if len(triggers_to_inform_and_remove) > 0:
            inform_workflows_for_triggers(triggers_to_inform_and_remove, context)
            removeTriggerAndWorkflowAssociations(triggers_to_inform_and_remove, context)

        remove_frontend_info(context, frontend_ip_port)

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

    new_frontend_entry = {}
    add_frontend_info(context, frontend_ip_port, json.dumps(new_frontend_entry))

    pending_triggers_from_other_inactive_frontends = health_check_registered_frontends(context)
    triggers_to_recreate = triggers_to_recreate + pending_triggers_from_other_inactive_frontends

    pending_global_triggers = get_info_for_global_pending_triggers(context)
    triggers_to_recreate = triggers_to_recreate + pending_global_triggers

    recreate_pending_triggers(triggers_to_recreate, context)

def handle_status(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [STATUS], frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))
    triggers_to_inform_and_remove = []
    triggers_to_recreate = []
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
                if error_trigger_info["status"].lower() == "ready":
                    triggers_to_inform_and_remove.append((error_trigger_info, trigger_error_map[error_trigger_id]))

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
        if len(triggers_to_inform_and_remove) > 0:
            inform_workflows_for_triggers(triggers_to_inform_and_remove, context)
            removeTriggerAndWorkflowAssociations(triggers_to_inform_and_remove, context)

    else:
        # we don't know about this frontend. Ideally it should not have any triggers
        print("Unknown frontend sending a status update!!")

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
        new_frontend_entry = {}
        add_frontend_info(context, frontend_ip_port, json.dumps(new_frontend_entry))

    pending_triggers_from_other_inactive_frontends = health_check_registered_frontends(context)
    triggers_to_recreate = triggers_to_recreate + pending_triggers_from_other_inactive_frontends

    pending_global_triggers = get_info_for_global_pending_triggers(context)
    triggers_to_recreate = triggers_to_recreate + pending_global_triggers

    recreate_pending_triggers(triggers_to_recreate, context)

def handle_stop(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("[TriggersFrontend] [STOP], frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))
    assert(len(trigger_status_map) == 0)
    frontend_info = get_frontend_info(context, frontend_ip_port)
    assert(frontend_info is not None)

    triggers_to_recreate = []
    triggers_to_inform_and_remove = []

    for error_trigger_id in trigger_error_map:
        error_trigger_info = get_trigger_info(context, error_trigger_id)
        if error_trigger_id in frontend_info and error_trigger_info is not None:
            #if error_trigger_info["status"].lower() == "ready" and "ready trigger shutdown!" in  trigger_error_map[error_trigger_id].lower():
            if error_trigger_info["status"].lower() == "ready":
                triggers_to_recreate.append((error_trigger_info, trigger_error_map[error_trigger_id]))
            else:
                triggers_to_inform_and_remove.append((error_trigger_info, trigger_error_map[error_trigger_id]))

    if len(triggers_to_inform_and_remove) > 0:
        inform_workflows_for_triggers(triggers_to_inform_and_remove, context)
        removeTriggerAndWorkflowAssociations(triggers_to_inform_and_remove, context)

    remove_frontend_info(context, frontend_ip_port)

    pending_triggers_from_other_inactive_frontends = health_check_registered_frontends(context)
    triggers_to_recreate = triggers_to_recreate + pending_triggers_from_other_inactive_frontends

    pending_global_triggers = get_info_for_global_pending_triggers(context)
    triggers_to_recreate = triggers_to_recreate + pending_global_triggers

    recreate_pending_triggers(triggers_to_recreate, context)

def get_info_for_global_pending_triggers(context):
    global_pending_triggers = get_global_pending_trigger_set(context)
    clear_global_pending_trigger_set(context)
    
    triggers_to_recreate = []

    for trigger_id in global_pending_triggers:
        pending_trigger_info = get_trigger_info(context, trigger_id)
        if pending_trigger_info is not None:
            triggers_to_recreate.append((pending_trigger_info, ""))
    return triggers_to_recreate

def get_active_frontend(context):
    tf_hosts = get_available_frontends(context)
    if len(tf_hosts) == 0:
        print("No available TriggersFrontend found")
        return ""

    tf_hosts = list(tf_hosts)
    tf_ip_port = select_random_active_frontend(tf_hosts)
    if tf_ip_port is None or tf_ip_port is "":
        print("No active TriggersFrontend found")
        return ""
    return tf_ip_port


def recreate_pending_triggers(triggers_to_recreate, context):
    print("[recreate_pending_triggers] called with number of triggers: " + str(len(triggers_to_recreate)))
    triggers_to_inform_and_remove = []

    for (trigger_info, error_msg) in triggers_to_recreate:
        print("[recreate_pending_triggers] Attempting to recreate trigger_id: " + trigger_info["trigger_id"])
        active_frontend = get_active_frontend(context)
        if active_frontend is not "":
            # there is an active frontend available, try to re-create the trigger
            try:
                status, updated_info = attempt_to_recreate_single_trigger(trigger_info, active_frontend, context)
                if status:
                    # trigger created, attempt to add workflow associations
                    associated_workflows = updated_info["associated_workflows"].copy()
                    for workflow_name in associated_workflows:
                        attempt_to_associate_trigger_with_workflows(updated_info["trigger_id"], workflow_name, context)
                else:
                    # need to add this to the list of inform list and then remove it
                    print("[recreate_pending_triggers] Unable to recreate trigger, trigger_id: " + trigger_info["trigger_id"])
                    triggers_to_inform_and_remove.append((trigger_info, "Unable to recreate trigger"))
            except Exception as e:
                print("[recreate_pending_triggers] Exception in attempt_to_recreate_single_trigger: " + str(e))
                triggers_to_inform_and_remove.append((trigger_info, "Unable to recreate trigger"))
        else:
            # no active triggers frontend, add to the pending set again
            print("[recreate_pending_triggers] Queuing up to be recreated, trigger_id: " + trigger_info["trigger_id"])
            add_to_global_pending_trigger_set(context, trigger_info["trigger_id"])


    if len(triggers_to_inform_and_remove) > 0:
        inform_workflows_for_triggers(triggers_to_inform_and_remove, context)
        removeTriggerAndWorkflowAssociations(triggers_to_inform_and_remove, context)


def attempt_to_recreate_single_trigger(trigger_info, tf_ip_port, context):
    print("[attempt_to_recreate_single_trigger] selected frontend: " + tf_ip_port + ", trigger_info: " + str(trigger_info))
    status_msg = ""
    # create the global trigger info all the information, and status set of starting, and not workflow associated
    trigger_id = trigger_info["trigger_id"]
    email = trigger_info["email"]
    trigger_name = trigger_info["trigger_name"]

    global_trigger_info = trigger_info.copy()
    global_trigger_info["status"] = "starting"
    global_trigger_info["frontend_ip_port"] = tf_ip_port

    # add the global_trigger_info to global map
    add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))

    url = "http://" + tf_ip_port + "/create_trigger"
    # send the request and wait for response
    print("[attempt_to_recreate_single_trigger] Contacting: " + url + ", with data: " + str(global_trigger_info["frontend_command_info"]))

    res_obj = {}
    try:
        res = requests.post(url, json=global_trigger_info["frontend_command_info"])
        if res.status_code != 200:
            raise Exception("status code: " + str(res.status_code) + " returned")
        res_obj = res.json()
    except Exception as e:
        status_msg = "POST Error: trigger_id: " + trigger_id + "," + str(e)
        #print("[AddTrigger] " + status_msg)
    
    if "status" in res_obj and res_obj["status"].lower() == "success":
        # add the trigger_id to frontend map
        print("[attempt_to_recreate_single_trigger] Success response from frontend")
        frontend_info = get_frontend_info(context, tf_ip_port)
        #print("get_frontend_info: " + str(frontend_info))
        assert(frontend_info is not None)
        frontend_info[trigger_id] = ''
        add_frontend_info(context, tf_ip_port, json.dumps(frontend_info))

        global_trigger_info["status"] = "ready"
        add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))

        # add the trigger_name to user's list of triggers
        user_triggers_list = get_user_trigger_list(context, email)
        user_triggers_list[trigger_name] = ''
        update_user_trigger_list(context, email, json.dumps(user_triggers_list))

        # write the user's list
        status_msg = "Trigger created successfully. Message: " + res_obj["message"] + ", details: " + str(global_trigger_info)
        print("[attempt_to_recreate_single_trigger] " + status_msg)
        return True, global_trigger_info
    else:
        if "message" in res_obj:
            status_msg = status_msg + ", message: " + res_obj["message"]
        status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
        print("[attempt_to_recreate_single_trigger] " + status_msg)
        return False, global_trigger_info


def attempt_to_associate_trigger_with_workflows(trigger_id, workflow_name, context):
    trigger_info = get_trigger_info(context, trigger_id)
    trigger_id = trigger_info["trigger_id"]
    email = trigger_info["email"]
    trigger_name = trigger_info["trigger_name"]
    tf_ip_port = trigger_info["frontend_ip_port"]
    
    workflow_info = trigger_info["associated_workflows"][workflow_name]
    workflow_state = workflow_info["workflow_state"]

    isWorkflowPresent, isWorkflowDeployed, workflow_details = isWorkflowPresentAndDeployed(email, workflow_name, context)
    if isWorkflowPresent == False:
        print("[attempt_to_associate_trigger_with_workflows] User: " + email + "Workflow: " + workflow_name + " not found.")
        del trigger_info["associated_workflows"][workflow_name]
        add_trigger_info(context, trigger_id, json.dumps(trigger_info))

    if isWorkflowPresent == True:
        # add the trigger name in workflow's metadata
        addTriggerToWorkflowMetadata(email, trigger_name, workflow_name, workflow_state, workflow_details["id"], context)

    if isWorkflowDeployed == True:
        # add the workflow to the trigger
        status = addWorkflowToTrigger(email, workflow_name, workflow_state, workflow_details, trigger_id, trigger_name, context)
        if not status:
            print("[attempt_to_associate_trigger_with_workflows] addWorkflowToTrigger failed: Removing workflow from associated_workflows of the trigger")
            del trigger_info["associated_workflows"][workflow_name]
            add_trigger_info(context, trigger_id, json.dumps(trigger_info))
        return status

    return True
    # TODO: write updated trigger info


def health_check_registered_frontends(context):
    print("[health_check_registered_frontends] called")
    triggers_to_recreate = []
    tf_hosts = get_available_frontends(context)
    if len(tf_hosts) == 0:
        print("[health_check_registered_frontends] No available TriggersFrontend found")
        return triggers_to_recreate
    tf_hosts = list(tf_hosts)

    for tf_ip_port in tf_hosts:
        if not is_frontend_active(tf_ip_port):
            # frontend is not active but is still registered with management

            print("[health_check_registered_frontends] Removing inactive frontend: " + tf_ip_port)
            triggers_to_inform_and_remove = []
            frontend_info = get_frontend_info(context, tf_ip_port)
            if frontend_info is None:
                continue

            for trigger_id in frontend_info:
                trigger_info = get_trigger_info(context, trigger_id)
                if trigger_info is not None and trigger_info["frontend_ip_port"] == tf_ip_port:
                    if trigger_info["status"] == "ready":
                        # this ready trigger is still associated with an inactive frontend
                        print("[health_check_registered_frontends] Queuing up to be recreated, trigger_id: " + str(trigger_id))
                        triggers_to_recreate.append((trigger_info, "READY trigger frontend not active"))
                    else:
                        triggers_to_inform_and_remove.append((trigger_info, "Triggers frontend not active"))
                else:
                    # this trigger is now associated with a different frontend, simply remove frontend information
                    pass
            
            if len(triggers_to_inform_and_remove) > 0:
                inform_workflows_for_triggers(triggers_to_inform_and_remove, context)
                removeTriggerAndWorkflowAssociations(triggers_to_inform_and_remove, context)

            remove_frontend_info(context, tf_ip_port)

    return triggers_to_recreate

def is_frontend_active(tf_ip_port):
    if tf_ip_port is None or tf_ip_port is "":
        return False
    url = "http://" + tf_ip_port + "/"
    print("[is_frontend_active] Contacting: " + url + ", to check if it is alive")

    try:
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception("[is_frontend_active] status code: " + str(res.status_code) + " returned")
        if res.text is None or res.text != 'ok':
            raise Exception("[is_frontend_active] response body: " + str(res.text) + " returned")
        if res.text == 'ok':
            print("[is_frontend_active] " + url + " is alive")
            return True
    except Exception as e:
        status_msg = "[is_frontend_active] Error: " + str(e)
        print(status_msg)
        return False

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

        try:
            removeTriggerFromWorkflow(trigger_info, context)
        except Exception as e:
            print("Exception in removeTriggerFromWorkflow: " + str(e))

        remove_trigger_info(context, trigger_info["trigger_id"])


def removeTriggerFromFrontend(trigger_info, context):
    print("[removeTriggerFromFrontend] for trigger: " + str(trigger_info))
    trigger_id = trigger_info["trigger_id"]
    frontend_ip_port = trigger_info["frontend_ip_port"]

    # remove the trigger_id from frontend map
    frontend_info = get_frontend_info(context, frontend_ip_port)
    if frontend_info is not None and trigger_id in frontend_info:
        del frontend_info[trigger_id]
        add_frontend_info(context, frontend_ip_port, json.dumps(frontend_info))


def removeTriggerFromWorkflow(trigger_info,context):
    print("[removeTriggerFromWorkflow] for trigger: " + str(trigger_info))
    associated_workflows = trigger_info["associated_workflows"].copy()
    email = trigger_info["email"]
    trigger_name = trigger_info["trigger_name"]
    storage_userid = trigger_info["storage_userid"]
    trigger_id = trigger_info["trigger_id"]

    status_msg = ""

    # do the delete trigger processing

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

def select_random_active_frontend(tf_hosts):
    selected_tf = ""
    while len(tf_hosts) > 0:
        tf_ip_port = tf_hosts[random.randint(0,len(tf_hosts)-1)]
        if is_frontend_active(tf_ip_port):
            selected_tf = tf_ip_port
            break
        else:
            tf_hosts.remove(tf_ip_port)
    return selected_tf

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


def addTriggerToWorkflowMetadata(email, trigger_name, workflow_name, workflow_state, workflow_id, context):
    print("[addTriggerToWorkflowMetadata] called with: trigger_name: " + str(trigger_name) + ", workflow_name: " + str(workflow_name) + ", workflow_state: " + str(workflow_state) + ", workflow_id: " + str(workflow_id))
    wf = context.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        print("[addTriggerToWorkflowMetadata] User: " + email + ", Workflow: " +
              workflow_name + ": couldn't retrieve workflow metadata.")
        return False

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

def addWorkflowToTrigger(email, workflow_name, workflow_state, workflow_details, trigger_id, trigger_name, context):
    print("[addWorkflowToTrigger] called with: trigger_id: " + str(trigger_id) + ", trigger_name: " + str(trigger_name) + ", workflow_name: " + str(workflow_name) + ", workflow_state: " + str(workflow_state) + ", workflow_details: " + str(workflow_details))
    status_msg = ""
    try:
        workflow_endpoints = workflow_details["endpoints"]
        if len(workflow_endpoints) == 0:
            print("[addTriggerForWorkflow] No workflow endpoint available")
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

        # if the frontend with the trigger is available
        global_trigger_info = get_trigger_info(context, trigger_id)
        tf_ip_port = global_trigger_info["frontend_ip_port"]
        
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
            return True
        else:
            if "message" in res_obj:
                status_msg = status_msg + ", message: " + res_obj["message"]
            status_msg = "[addTriggerForWorkflow] Error: " + status_msg + ", response: " + str(res_obj)
            raise Exception(status_msg)
    except Exception as e:
        print("[addWorkflowToTrigger] exception: " + str(e))
        deleteTriggerFromWorkflowMetadata(email, trigger_name, workflow_name, workflow_details["id"], context)
        return False


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