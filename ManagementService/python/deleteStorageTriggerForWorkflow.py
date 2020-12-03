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
import time

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    try:
        if "email" not in data or "workflowname" not in data or "tablename" not in data:
            raise Exception("Couldn't delete storage trigger; either user email or workflow name or table name is missing")
        email = data["email"]
        workflowname = data["workflowname"]
        tablename = data["tablename"]
        storage_userid = data["storage_userid"]

        isTablePresent = isTriggerTablePresent(email, tablename, sapi)
        if isTablePresent == False:
            raise Exception("Table: " + tablename + " not found.")

        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        removeWorkflowFromTableMetadata(email, tablename, workflowname, dlc)
        dlc.shutdown()

        isWorkflowPresent, isWorkflowDeployed, details = isWorkflowPresentAndDeployed(email, workflowname, sapi)
        if isWorkflowPresent == False:
            raise Exception("Workflow: " + workflowname + " not found.")

        if isWorkflowPresent == True:
            # remove the name of the triggerable table from workflow's metadata
            removeTableToWorkflowMetadata(email, tablename, workflowname, details["id"], sapi)



    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't remove storage trigger; "+str(e)
        response["data"] = response_data
        print(str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = "Storage Trigger removed for workflow: " + workflowname + ", which was associated with table: " + tablename
    response["data"] = response_data
    #print(str(response))
    sapi.log(json.dumps(response))
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
            details["endpoints"] = list(sapi.retrieveSet(wf_id + "_workflow_endpoints", is_private=True))
            if "modified" in wf:
                details["modified"] = wf["modified"]
            if "associatedTriggerableTables" in wf:
                details["associatedTriggerableTables"] = wf["associatedTriggerableTables"]
            if wf["status"] == "deployed" or wf["status"] == "deploying":
                isWorkflowDeployed = True

    return isWorkflowPresent, isWorkflowDeployed, details

def isTriggerTablePresent(email, tablename, sapi):
    # add to the list of triggerable tables
    trigger_tables = sapi.get(email + "_list_trigger_tables", True)
    if trigger_tables is not None and trigger_tables != "":
        trigger_tables = json.loads(trigger_tables)
    else:
        trigger_tables = {}

    if tablename not in trigger_tables:
        return False
    else:
        return True

def removeWorkflowFromTableMetadata(email, tablename, workflowname, dlc):
    metadata_key = tablename
    triggers_metadata_table = 'triggersInfoTable'
    print("[removeWorkflowFromTableMetadata] User: " + email + ", removing Workflow: " + workflowname + ", from Table: " + tablename)

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


def removeTableToWorkflowMetadata(email, tablename, workflowname, workflow_id, sapi):
    wf = sapi.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        raise Exception("[removeTableToWorkflowMetadata] couldn't retrieve workflow metadata.")
    wf = json.loads(wf)
    print("Current workflow metadata: " + str(wf))
    if 'associatedTriggerableTables' in wf:
        associatedTables = wf['associatedTriggerableTables']
        if tablename in associatedTables:
            del associatedTables[tablename]
            wf['associatedTriggerableTables'] = associatedTables
            wf = sapi.put(email + "_workflow_" + workflow_id, json.dumps(wf), True)
            print("[removeTableToWorkflowMetadata] User: " + email + ", from Workflow: " + workflowname + ", removed Table: " + tablename)
