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
import json
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
    print("get_frontend_info: data: " + str(ret))
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def is_trigger_registered(context, trigger_id):
    return context.containsMapKey(MAP_TRIGGERS_TO_INFO, trigger_id, True)

def get_trigger_info(context, trigger_id):
    ret = context.getMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)
    print("get_trigger_info: data: " + str(ret))
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def get_user_trigger_list(context, email):
    user_triggers_list = context.get(email + "_list_triggers", True)
    if user_triggers_list is not None and user_triggers_list != "":
        user_triggers_list = json.loads(user_triggers_list)
    else:
        user_triggers_list = {}
    return user_triggers_list


def handle(value, context):
    assert isinstance(value, dict)
    data = value
    print("[GetTriggerDetails] input data: " + str(data))
    status_msg = ""
    try:
        if "email" not in data or "trigger_names" not in data or type(data["trigger_names"]) is not type([]):
            raise Exception(
                "Couldn't get details of triggers; either user email or trigger_names array is missing")
        email = data["email"]
        trigger_names = data["trigger_names"]
        storage_userid = data["storage_userid"]

        if len(trigger_names) == 0:
            user_triggers_list = get_user_trigger_list(context, email)
            for trigger_name in user_triggers_list:
                trigger_names.append(trigger_name)

        all_details = {}
        for trigger_name in trigger_names:
            details = get_details_for_trigger_name(trigger_name, storage_userid, context)
            all_details[trigger_name] = details

        response_data = {}
        response_data["trigger_details"] = all_details
        status_msg = "Number of details included: " + str(len(all_details))

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't get details for triggers; " + str(e)
        response["data"] = response_data
        print("[GetTriggerDetails] Error: " + str(response))
        return response

    # finish successfully
    response = {}
    response["status"] = "success"
    response_data["message"] = status_msg
    response["data"] = response_data
    print("[GetTriggerDetails] response: " + str(response))
    return response


def get_details_for_trigger_name(trigger_name, storage_userid, context):
    details = {}
    trigger_id = storage_userid + "_" + trigger_name

    details["trigger_status"] = "non_existent"
    details["trigger_id"] = trigger_id
    details["status_msg"] = "Trigger not found"

    # check the global list for the trigger
    global_trigger_info = get_trigger_info(context, trigger_id)
    
    if global_trigger_info is not None:
        try:
            tf_ip_port = global_trigger_info["frontend_ip_port"]
            if not is_frontend_active(tf_ip_port):
                raise Exception("Frontend: " + tf_ip_port + " not active")

            # send the request and wait for response
            url = "http://" + tf_ip_port + "/trigger_details"
            res_obj = {}
            status_msg = ""
            try:
                res = requests.post(url, json={"trigger_id": trigger_id})
                if res.status_code != 200:
                    raise Exception("[get_details_for_trigger_name] status code: " + str(res.status_code) + " returned")
                res_obj = res.json()
            except Exception as e:
                status_msg = "[get_details_for_trigger_name] Error: trigger_id" + trigger_id + "," + str(e)
            
            if "status" in res_obj and "message" in res_obj:
                details = json.loads(res_obj["message"])
            else:
                raise Exception(status_msg)

        except Exception as e:
            msg = "[GetTriggerDetails] Exception: " + str(e)
            print(msg)
            details["status_msg"] = msg

    return details


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