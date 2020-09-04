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
        print("[addStorageTrigger] User: " + email + ", Table: " + tablename + ", Workflow: " + workflowname + ", storage_userid: " + storage_userid)

        isTablePresent = isTriggerTablePresent(email, tablename, sapi)
        if isTablePresent == False:
            print("[addStorageTrigger] User: " + email + ", Table: " + tablename + " not found.")
            raise Exception("Table: " + tablename + " not found.")
        
        isWorkflowPresent, isWorkflowDeployed, details = isWorkflowPresentAndDeployed(email, workflowname, sapi)
        if isWorkflowPresent == False:
            print("[addStorageTrigger] User: " + email + "Workflow: " + workflowname + " not found.")
            raise Exception("Workflow: " + workflowname + " not found.")

        if isWorkflowPresent == True:
            # add the name of the triggerable table in workflow's metadata
            addTableToWorkflowMetadata(email, tablename, workflowname, details["id"], sapi)
        
        if isWorkflowDeployed == True:
            # associate a deployed workflow with a triggerable table
            dlc = sapi.get_privileged_data_layer_client(storage_userid)
            addWorkflowToTableMetadata(email, tablename, workflowname, details["endpoints"], dlc)
            dlc.shutdown()


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
    if isWorkflowPresent == True and isWorkflowDeployed == False:
        response_data["message"] = "Trigger queued up for workflow: " + workflowname + ", to be associated in future with table: " + tablename
    else:
        response_data["message"] = "Trigger added for workflow: " + workflowname + ", urls: " + str(details['endpoints']) + ", associated with table: " + tablename
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
        raise Exception("Couldn't fetch details for workflow: " + workflowname)
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
    if "endpoints" in wf:
        details["endpoints"] = wf["endpoints"]
    if "modified" in wf:
        details["modified"] = wf["modified"]
    if "associatedTriggerableTables" in wf:
        details["associatedTriggerableTables"] = wf["associatedTriggerableTables"]

    return details

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


def addTableToWorkflowMetadata(email, tablename, workflowname, workflow_id, sapi):
    wf = sapi.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        print("[addTableToWorkflowMetadata] User: " + email + ", Workflow: " + workflowname + ": couldn't retrieve workflow metadata.")
        raise Exception("[addTableToWorkflowMetadata] User: " + email + ", Workflow: " + workflowname + ": couldn't retrieve workflow metadata.")
    
    wf = json.loads(wf)
    print("[addTableToWorkflowMetadata] User: " + email + ", Workflow: " + workflowname + ": Current workflow metadata: " +str(wf))

    if 'associatedTriggerableTables' not in wf:
        wf['associatedTriggerableTables'] = {}
    associatedTables = wf['associatedTriggerableTables']
    if tablename not in associatedTables:
        associatedTables[tablename] = ''
        wf['associatedTriggerableTables'] = associatedTables
        wf = sapi.put(email + "_workflow_" + workflow_id, json.dumps(wf), True)
        print("[addTableToWorkflowMetadata] User: " + email + ", Table: " + tablename + " added to Workflow: " + workflowname)
    else:
        print("[addTableToWorkflowMetadata] User: " + email + ", Table: " + tablename + " already present in Workflow: " + workflowname)


def addWorkflowToTableMetadata(email, tablename, workflowname, workflow_endpoints, dlc):
    metadata_key = tablename
    metadata_urls = workflow_endpoints
    triggers_metadata_table = 'triggersInfoTable'
    bucket_metadata = {"urltype": "url", "urls": metadata_urls, "wfname": workflowname}
    print("[addWorkflowToTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Adding metadata: " + str(bucket_metadata))

    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    if current_meta == None or current_meta == '':
        meta_list = []
    else:
        meta_list = json.loads(current_meta)

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
    print("[addWorkflowToTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Updated metadata: " + str(updated_meta_list))
