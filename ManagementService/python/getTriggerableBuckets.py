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


def handle(value, sapi):
    assert isinstance(value, dict)
    data = value
    print(str(data))
    try:
        if "email" not in data:
            raise Exception("User email is missing")
        email = data["email"]
        storage_userid = data["storage_userid"]

        # add to the list of triggerable tables
        trigger_tables = sapi.get(email + "_list_trigger_tables", True)
        if trigger_tables is not None and trigger_tables != "":
            trigger_tables = json.loads(trigger_tables)
        else:
            trigger_tables = {}

        # finish successfully
        table_info = {}
        table_details = {}
        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        for table in trigger_tables:
            table_info[table], table_details[table] = listAssociatedWorkflowsForTable(
                table, dlc)
        dlc.shutdown()

        response_data = {}
        response_data["buckets"] = table_info
        response_data["buckets_details"] = table_details
        response_data["message"] = "Found " + \
            str(len(table_info)) + " buckets."

        response = {}
        response["status"] = "success"
        response["data"] = response_data
        # print(str(response))
        sapi.log(json.dumps(response))
        return response

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't list triggerable buckets; "+str(e)
        response["data"] = response_data
        print(str(response))
        return response


def listAssociatedWorkflowsForTable(tablename, dlc):
    metadata_key = tablename
    triggers_metadata_table = 'triggersInfoTable'
    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    if current_meta == None or current_meta == '':
        print("[getTriggerableTable,listAssociatedWorkflowsForTable] Metadata = None for Table: " + str(metadata_key))
        return [], []
    meta_list = json.loads(current_meta)
    workflow_list = []
    if type(meta_list == type([])):
        for i in range(len(meta_list)):
            meta = meta_list[i]
            workflow_list.append(meta["wfname"])
        return workflow_list, meta_list
    else:
        return [], []
