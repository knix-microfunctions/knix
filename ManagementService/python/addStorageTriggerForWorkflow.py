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
import os
import random
import time

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    try:
        if "email" not in data or "workflowname" not in data or "tablename" not in data:
            raise Exception("Couldn't add storage trigger; either user email or workflow name or table name is missing")
        email = data["email"]
        workflowname = data["workflowname"]
        tablename = data["tablename"]
        storage_userid = data["storage_userid"]

        details = getWorkflowDetails(email, workflowname, sapi)

        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        metadata_key = tablename
        metadata_url = random.choice(details["endpoints"])
        triggers_metadata_table = 'triggersInfoTable'
        bucket_metadata = {"urltype": "url", "url": metadata_url, "wfname": workflowname}
        print("Adding metadata: " + str(bucket_metadata))

        current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
        print("fetched data: " + str(current_meta))
        print("Getting existing key: " + metadata_key)
        print("  in table: " + triggers_metadata_table)

        meta_list = json.loads(current_meta)
        print(str(type(meta_list)))
        print("  with value: " + str(meta_list))

        if type(meta_list == type([])):
            for i in range(len(meta_list)):
                meta=meta_list[i]
                if meta["wfname"] == bucket_metadata["wfname"]:
                    del meta_list[i]
                    break
            meta_list.append(bucket_metadata)

        dlc.put(metadata_key, json.dumps(meta_list), tableName=triggers_metadata_table)

        time.sleep(0.2)
        updated_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
        updated_meta_list = json.loads(updated_meta)
        print("  Updated value: " + str(updated_meta_list))

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't add storage trigger; "+str(e)
        response["data"] = response_data
        print(str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = "Trigger added for workflow: " + workflowname + ", url: " + metadata_url + ", associated with table: " + tablename
    response["data"] = response_data
    print(str(response))
    sapi.log(json.dumps(response))
    return response

def getWorkflowDetails(email, workflowname, sapi):
    workflows = sapi.get(email + "_list_workflows", True)
    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
    else:
        workflows = {}

    if workflowname not in workflows:
        raise Exception("Couldn't add storage trigger: " + workflowname + " not found.")
    wf_id = workflows[workflowname]

    wf = sapi.get(email + "_workflow_" + wf_id, True)
    if wf is None or wf == "":
        raise Exception("Couldn't retrieve workflow status.")
    wf = json.loads(wf)
    wf_status = sapi.get("workflow_status_" + wf_id, True)

    details = {}
    details["email"] = email
    details["name"] = workflowname
    details["id"] = wf_id
    details["status"] = wf_status
    details["endpoints"] = wf["endpoints"]
    details["modified"] = wf["modified"]

    return details
