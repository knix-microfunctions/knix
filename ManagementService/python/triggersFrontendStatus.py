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

MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

def handle(value, context):
    assert isinstance(value, dict)
    data = value
    action = data["action"].lower()
    frontend_ip_port = data["self_ip_port"]
    trigger_status_map = data["trigger_status_map"]
    trigger_error_map = data["trigger_error_map"]

    print("TriggersFrontend status message, Action: " + action + ", frontend_ip_port: " + frontend_ip_port + ", trigger_status_map: " + str(trigger_status_map) + ", trigger_error_map: " + str(trigger_error_map))

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
    if ret is "":
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
    if ret is "":
        return None
    else:
        return json.loads(ret)

def add_trigger_info(context, trigger_id, data):
    print("add_trigger_info: " + trigger_id + ", data: " + data)
    context.putMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, data, True)

def remove_trigger_info(context, trigger_id):
    print("remove_trigger_info: " + trigger_id)
    context.deleteMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)

def handle_add_triggers(pending_triggers):
    print("TODO: add triggers: " + str(pending_triggers))


# called when a frontend starts
def handle_start(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("START Triggers Frontend: " + frontend_ip_port)
    assert(len(trigger_status_map) == 0) # frontend should not be running anything yet
    assert(len(trigger_error_map) == 0) # frontend should not be running anything yet

    pending_triggers = []
    frontend_available = is_frontend_registered(context, frontend_ip_port)
    if frontend_available:
        print("Frontend already registered!")
        # we have the frontend already registered with us. Why is it starting again,
        # without telling us that it stopped? Maybe because the stop message did not reach us?
        # check if we have any triggers that we think should be active, 
        # and were earlier assigned to this frontend which has just started up
        # such triggers will have to be re-assigned
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
    new_frontend_entry = '{}'
    add_frontend_info(frontend_ip_port, new_frontend_entry)

    if len(pending_triggers) > 0:
        handle_add_triggers(pending_triggers)

def handle_status(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    print("STATUS Triggers Frontend: " + frontend_ip_port)
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
        if len(pending_triggers) > 0:
            handle_add_triggers(pending_triggers)
    else:
        # we don't know about this frontend. Ideally it should not have any triggers
        print("Unknown frontend!")
        new_frontend_entry = '{}'
        # add all the triggers in the reported list to our list of triggers associated with frontend
        # also make sure that those triggers exist in the larger trigger map
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
        add_frontend_info(frontend_ip_port, json.dumps(new_frontend_entry))
    pass

def handle_stop(frontend_ip_port, trigger_status_map, trigger_error_map, context):
    assert(len(trigger_status_map) == 0)
    pending_triggers = []
    frontend_info = get_frontend_info(context, frontend_ip_port)
    assert(frontend_info is not None)

    for error_trigger_id in trigger_error_map:
        error_trigger_info = get_trigger_info(context, error_trigger_id)
        if error_trigger_id in frontend_info and error_trigger_info is not None:
            if error_trigger_info["status"] == "ready" or error_trigger_info["status"] == "starting":
                pending_triggers.append(error_trigger_info)
        remove_trigger_info(context, error_trigger_id)
    remove_frontend_info(context, frontend_ip_port)
    # a frontend is stopping. All the triggers will be forcefully stopped. 
    # all the triggers that are reported forcefully stopped and are known to the management, should be put in pending list

    if len(pending_triggers) > 0:
        handle_add_triggers(pending_triggers)
