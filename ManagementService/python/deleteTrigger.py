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

        if global_trigger_info is not None and trigger_name in user_triggers_list:
            # we know about the trigger. delete it

            # get the list of available frontends. Select one
            tf_hosts = get_available_frontends(context)
            if len(tf_hosts) == 0:
                raise Exception("No available TriggersFrontend found")
            tf_ip_port = global_trigger_info["frontend_ip_port"]
            if tf_ip_port not in tf_hosts:
                raise Exception("Frontend: " + tf_ip_port + " not available")
            url = "http://" + tf_ip_port + "/delete_trigger"
            # send the request and wait for response

            res_obj = {}
            try:
                res = requests.post(url, json={"trigger_id": trigger_id})
                if res.status_code != 200:
                    raise Exception("status code: " + str(res.status_code) + " returned")
                res_obj = res.json()
            except Exception as e:
                status_msg = "Error: trigger_id" + trigger_id + "," + str(e)
            
            if "status" in res_obj and res_obj["status"].lower() == "success":
                # add the trigger_id to frontend map
                frontend_info = get_frontend_info(context, tf_ip_port)
                assert(frontend_info is not None)
                if trigger_id in frontend_info:
                    del frontend_info[trigger_id]
                add_frontend_info(context, tf_ip_port, json.dumps(frontend_info))

                remove_trigger_info(context, trigger_id)

                # add the trigger_name to user's list of triggers
                if trigger_name in user_triggers_list:
                    del user_triggers_list[trigger_name]
                update_user_trigger_list(context, email, json.dumps(user_triggers_list))

                #TODO: look up workflows associated with this trigger and remove the trigger from 
                # associatedTriggers
                
                # write the user's list
                status_msg = "Trigger deleted successfully. Message: " + res_obj["message"]
            else:
                if "message" in res_obj:
                    status_msg = status_msg + ", message: " + res_obj["message"]
                status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
                remove_trigger_info(context, trigger_id)
                raise Exception(status_msg)

        elif global_trigger_info is None and trigger_name not in user_triggers_list:
            # both the global list has the trigger and user_trigger_list dont have the trigger.
            status_msg = "Could not find Trigger " + trigger_name
        else:
            # only one of the list has has the trigger. Should not happen
            raise Exception("Error: mismatch between global trigger list and user's trigger list")

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