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
        if "email" not in data or "bucketname" not in data:
            raise Exception(
                "Couldn't delete triggerable bucket; either user email or bucket name is missing")
        email = data["email"]
        tablename = data["bucketname"]
        storage_userid = data["storage_userid"]

        # get a list of workflows.
        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        associatedWorkflows = listAssociatedWorkflowsForTable(tablename, dlc)
        triggers_metadata_table = 'triggersInfoTable'
        dlc.delete(tablename, tableName=triggers_metadata_table)
        print("User: " + email + ", Deleting metadata for bucket: " + tablename)
        dlc.shutdown()

        # for each workflow, remove table from workflow metadata
        for workflowname in associatedWorkflows:
            wf_id = getWorkflowId(email, workflowname, sapi)
            if wf_id != '':
                removeTableFromWorkflowMetadata(
                    email, tablename, workflowname, wf_id, sapi)

        trigger_tables = sapi.get(email + "_list_trigger_tables", True)
        if trigger_tables is not None and trigger_tables != "":
            trigger_tables = json.loads(trigger_tables)
        else:
            trigger_tables = {}

        if tablename in trigger_tables:
            del trigger_tables[tablename]
            sapi.put(email + "_list_trigger_tables",
                     json.dumps(trigger_tables), True)
            print("User: " + email + ", Deleted bucket: " +
                  tablename + "  to the list of triggerable buckets")

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't delete a triggerable bucket; " + \
            str(e)
        response["data"] = response_data
        print(str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = "Bucket deleted: " + tablename
    response["data"] = response_data
    # print(str(response))
    sapi.log(json.dumps(response))
    return response


def listAssociatedWorkflowsForTable(tablename, dlc):
    metadata_key = tablename
    triggers_metadata_table = 'triggersInfoTable'
    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    meta_list = json.loads(current_meta)

    workflow_list = []
    if type(meta_list == type([])):
        for i in range(len(meta_list)):
            meta = meta_list[i]
            workflow_list.append(meta["wfname"])
    return workflow_list


def getWorkflowId(email, workflowname, sapi):
    workflows = sapi.get(email + "_list_workflows", True)
    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
    else:
        workflows = {}

    wf_id = ''
    if workflowname in workflows:
        wf_id = workflows[workflowname]
    return wf_id


def removeTableFromWorkflowMetadata(email, tablename, workflowname, workflow_id, sapi):
    wf = sapi.get(email + "_workflow_" + workflow_id, True)
    if wf is None or wf == "":
        raise Exception(
            "removeTableToWorkflowMetadata: couldn't retrieve workflow metadata.")
    wf = json.loads(wf)
    print("Current workflow metadata: " + str(wf))
    if 'associatedTriggerableTables' in wf:
        associatedTables = wf['associatedTriggerableTables']
        if tablename in associatedTables:
            del associatedTables[tablename]
            wf['associatedTriggerableTables'] = associatedTables
            wf = sapi.put(email + "_workflow_" +
                          workflow_id, json.dumps(wf), True)
            print("User: " + email + ", Removed bucket: " + tablename +
                  ", from the metadata of workflow: " + workflowname)
