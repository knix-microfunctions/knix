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


def validate_and_get_trigger_info(trigger_info):
    completed_trigger_info = {}
    if "trigger_type" not in trigger_info or type(trigger_info["trigger_type"]) is not type(""):
        return False, "trigger_type is missing or is not a string", "", {}

    if trigger_info["trigger_type"] == "amqp":
        if "amqp_addr" not in trigger_info or type(trigger_info["amqp_addr"]) is not type(""):
            return False, "amqp_addr is missing or is not a string", {}
        completed_trigger_info["amqp_addr"] = trigger_info["amqp_addr"]

        if "routing_key" not in trigger_info or type(trigger_info["routing_key"]) is not type(""):
            return False, "routing_key is missing or is not a string", {}
        completed_trigger_info["routing_key"] = trigger_info["routing_key"]

        if "exchange" in trigger_info and type(trigger_info["exchange"]) is not type(""):
            return False, "exchange is not a string", {}
        completed_trigger_info["exchange"] = trigger_info["exchange"] if "exchange" in trigger_info else ""

        if "auto_ack" in trigger_info and type(trigger_info["auto_ack"]) is not type(True):
            return False, "auto_ack is not a boolean", {}
        completed_trigger_info["auto_ack"] = trigger_info["auto_ack"] if "auto_ack" in trigger_info else True

        if "durable" in trigger_info and type(trigger_info["durable"]) is not type(True):
            return False, "durable is not a boolean", {}
        completed_trigger_info["durable"] = trigger_info["durable"] if "durable" in trigger_info else False

        if "exclusive" in trigger_info and type(trigger_info["exclusive"]) is not type(True):
            return False, "exclusive is not a boolean", {}
        completed_trigger_info["exclusive"] = trigger_info["exclusive"] if "exclusive" in trigger_info else False
        
        return True, "Valid amqp trigger info", "amqp", completed_trigger_info

    elif trigger_info["trigger_type"] == "timer":
        if "timer_interval_ms" not in trigger_info or type(trigger_info["timer_interval_ms"]) is not type(0):
            return False, "timer_interval_ms is missing or is not an integer", {}
        completed_trigger_info["timer_interval_ms"] = trigger_info["timer_interval_ms"]
        return True, "Valid timer trigger info", "timer", completed_trigger_info

    else:
        return False, "unknown trigger type: " + trigger_info["trigger_type"], trigger_info["trigger_type"], {}


### Main entry ###
def handle(value, context):
    assert isinstance(value, dict)
    data = value
    print("[AddTrigger] input data: " + str(data))
    status_msg = ""
    try:
        if "email" not in data or "trigger_name" not in data or "trigger_info" not in data:
            raise Exception(
                "Couldn't add trigger; either user email or trigger_name or trigger_info is missing")
        email = data["email"]
        trigger_name = data["trigger_name"]
        storage_userid = data["storage_userid"]
        trigger_info = data["trigger_info"]
        trigger_id = storage_userid + "_" + trigger_name

        # check the global list for the trigger
        global_trigger_info = get_trigger_info(context, trigger_id)
        print("Retrieved global_trigger_info: " + str(global_trigger_info))
        
        # check the user's storage area for the trigger name
        user_triggers_list = get_user_trigger_list(context, email)
        print("Retrieved user_triggers_list: " + str(user_triggers_list))

        if global_trigger_info is None:
            # we dont know about the trigger. Create it
            # valid user provided trigger_info
            status, msg, trigger_type, completed_trigger_info = validate_and_get_trigger_info(trigger_info)
            if status == False:
                raise Exception("Invalid trigger_info object: " + msg)
            
            print("Validated trigger_info: " + str(trigger_type) + ", " + str(completed_trigger_info))
            
            # get the list of available frontends. Select one
            tf_hosts = get_available_frontends(context)
            if len(tf_hosts) == 0:
                raise Exception("No available TriggersFrontend found")
            tf_hosts = list(tf_hosts)
            tf_ip_port = tf_hosts[random.randint(0,len(tf_hosts)-1)]
            print("[AddTrigger] selected frontend: " + tf_ip_port)
            # create the global trigger info all the information, and status set of starting, and not workflow associated
            global_trigger_info = \
                {
                    "status": "starting",
                    "frontend_ip_port": tf_ip_port,
                    "email": email,
                    "trigger_id": trigger_id,
                    "storage_userid": storage_userid,
                    "trigger_name": trigger_name,
                    "associated_workflows": {}, # key = workflow_name, value: {"workflow_url": "", "workflow_name": "", "workflow_state": ""}
                    "frontend_command_info": \
                        {
                            "trigger_type": trigger_type,
                            "trigger_id": trigger_id,
                            "trigger_name": trigger_name,
                            "trigger_info": completed_trigger_info
                        }
                }

            # add the global_trigger_info to global map
            add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))
            
            url = "http://" + tf_ip_port + "/create_trigger"
            # send the request and wait for response
            print("Contacting: " + url + ", with data: " + str(global_trigger_info["frontend_command_info"]))

            res_obj = {}
            try:
                res = requests.post(url, json=global_trigger_info["frontend_command_info"])
                if res.status_code != 200:
                    raise Exception("status code: " + str(res.status_code) + " returned")
                res_obj = res.json()
            except Exception as e:
                status_msg = "Error: trigger_id: " + trigger_id + "," + str(e)
                #print("[AddTrigger] " + status_msg)
            
            if "status" in res_obj and res_obj["status"].lower() == "success":
                # add the trigger_id to frontend map
                print("Success response from frontend")
                frontend_info = get_frontend_info(context, tf_ip_port)
                #print("get_frontend_info: " + str(frontend_info))
                assert(frontend_info is not None)
                frontend_info[trigger_id] = ''
                add_frontend_info(context, tf_ip_port, json.dumps(frontend_info))

                global_trigger_info["status"] = "ready"
                add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))

                # add the trigger_name to user's list of triggers
                user_triggers_list[trigger_name] = ''
                update_user_trigger_list(context, email, json.dumps(user_triggers_list))

                # write the user's list
                status_msg = "Trigger created successfully. Message: " + res_obj["message"] + ", details: " + str(global_trigger_info)
            else:
                if "message" in res_obj:
                    status_msg = status_msg + ", message: " + res_obj["message"]
                status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
                remove_trigger_info(context, trigger_id)
                raise Exception(status_msg)

        else:
            # both the global list has the trigger and user_trigger_list has the trigger.
            status_msg = "Not creating trigger again. Trigger " + trigger_name + " already exists, with information: " + str(global_trigger_info)

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't create the trigger; " + str(e)
        response["data"] = response_data
        print("[AddTrigger] Error: " + str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = status_msg
    response["data"] = response_data
    print("[AddTrigger] response: " + str(response))
    return response


    # Consider trigger_name similar to table name to be created to storage triggers
    # get user suid, get a datalayer for it. 
    # generate a globally unique trigger_id = storage_suid + "!" + trigger_name
    # map of global triggers, which have all the info related to the trigger
        # global info for trigger = key = trigger_id_global
            #       value = status, frontend_ip_port, storage_suid, email, trigger_name_user, 
            #               list of workflow names,
            #               trigger_info - trigger_type, trigger_id, trigger_name_user, trigger_info =     
            #                                   "amqp_addr": "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost",
            #                                   "routing_key": "rabbit.routing.key",
            #                                   "exchange": "rabbitexchange",
            #                                   "durable": true,
            #                                   "exclusive": true,
            #                                   "auto_ack": true
    # list of triggers in this user storage area - just store trigger_name (and no additional info)
    # if the trigger_id exists in the global list and trigger_name exists in the list of trigger for this user then return false

    # if does not exist at both places then create a new trigger
    # pick an available frontend, geneate the POST message, add the message to the global table with status starting
        # send message, check for response. 
            # If success then, update status of global trigger, add it to the list of triggers for this user
            # If failure, then remove this trigger from global triggers
