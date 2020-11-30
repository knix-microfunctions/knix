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
import os

import requests

MFN_ELASTICSEARCH = os.getenv("MFN_ELASTICSEARCH", os.getenv("MFN_HOSTNAME"))
ELASTICSEARCH_HOST = MFN_ELASTICSEARCH.split(':')[0]
try:
    ELASTICSEARCH_PORT = MFN_ELASTICSEARCH.split(':')[1]
except:
    ELASTICSEARCH_PORT = 9200

ELASTICSEARCH_URL = "http://" + ELASTICSEARCH_HOST + ":" + str(ELASTICSEARCH_PORT)

def delete_workflow_index(index_name):
    try:
        r = requests.delete(ELASTICSEARCH_URL + "/" + index_name, proxies={"http":None})
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            print('Could not connect to: ' + ELASTICSEARCH_URL)
        else:
            raise e

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False

    email = data["email"]
    storage_userid = data["storage_userid"]

    if "workflow" in data:
        workflow = data["workflow"]
        if "id" in workflow:
            workflows = sapi.get(email + "_list_workflows", True)
            if workflows is not None and workflows != "":
                workflows = json.loads(workflows)
                if workflow["id"] in workflows.values():
                    wf = sapi.get(email + "_workflow_" + workflow["id"], True)
                    if wf is not None and wf != "":
                        wf = json.loads(wf)
                        if wf["status"] == "undeployed" or wf["status"] == "failed":
                            for wn in workflows:
                                if workflows[wn] == workflow["id"]:
                                    del workflows[wn]
                                    break

                            # delete workflow logs
                            delete_workflow_index("mfnwf-" + workflow["id"])

                            #sapi.delete(email + "_workflow_json_" + workflow["id"], True, True)
                            #sapi.delete(email + "_workflow_requirements_" + workflow["id"], True, True)

                            dlc = sapi.get_privileged_data_layer_client(storage_userid)
                            dlc.delete("workflow_json_" + workflow["id"])
                            dlc.delete("workflow_requirements_" + workflow["id"])

                            print("Current workflow metadata: " + str(wf))
                            if "associatedTriggerableTables" in wf:
                                for table in wf["associatedTriggerableTables"]:
                                    removeWorkflowFromTableMetadata(email, table, wf["name"], dlc)

                            if "associatedTriggers" in wf:
                                for trigger_name in wf["associatedTriggers"]:
                                    trigger_id = storage_userid + "_" + trigger_name
                                    if isTriggerPresent(email, trigger_id, trigger_name, sapi) == True:
                                        try:
                                            removeTriggerFromWorkflow(trigger_name, trigger_id, wf["name"], sapi)
                                        except Exception as e:
                                            print("Removing associated triggers error: " + str(e))
                            
                            
                            sapi.delete(email + "_workflow_" + workflow["id"], True, True)

                            dlc.shutdown()

                            sapi.put(email + "_list_workflows", json.dumps(workflows), True, True)

                            response_data["message"] = "Deleted workflow " + workflow["id"] + "."

                            success = True

                        else:
                            response_data["message"] = "Couldn't delete workflow; workflow is still deployed. Undeploy workflow first."
                    else:
                        response_data["message"] = "Couldn't delete workflow; workflow metadata is not valid."
                else:
                    response_data["message"] = "Couldn't delete workflow; no such workflow."
            else:
                response_data["message"] = "Couldn't delete workflow; no such workflow."
        else:
            response_data["message"] = "Couldn't delete workflow; malformed input."
    else:
        response_data["message"] = "Couldn't delete workflow; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

def removeWorkflowFromTableMetadata(email, tablename, workflowname, dlc):
    metadata_key = tablename
    triggers_metadata_table = 'triggersInfoTable'
    print("[removeWorkflowFromTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename)

    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)

    meta_list = json.loads(current_meta)

    if type(meta_list == type([])):
        for i in range(len(meta_list)):
            meta=meta_list[i]
            if meta["wfname"] == workflowname:
                del meta_list[i]
                break

    dlc.put(metadata_key, json.dumps(meta_list), tableName=triggers_metadata_table)

    time.sleep(0.2)
    updated_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    updated_meta_list = json.loads(updated_meta)
    print("[removeWorkflowFromTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Updated metadata: " + str(updated_meta_list))


MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

### Utility functions ###
def get_available_frontends(context):
    tf_hosts = context.getMapKeys(MAP_AVAILABLE_FRONTENDS, True)
    return tf_hosts

def get_frontend_info(context, frontend_ip_port):
    ret = context.getMapEntry(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, True)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

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


def isTriggerPresent(email, trigger_id, trigger_name, context):
    # check if the global trigger is present
    global_trigger_info = get_trigger_info(context, trigger_id)

    # check if the trigger does not exist in global and user's list
    if global_trigger_info is None:
        return False

    return True

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
            print("[removeTriggerFromWorkflow] " + status_msg)
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
        #print("[removeTriggerFromWorkflow] " + str(e))
