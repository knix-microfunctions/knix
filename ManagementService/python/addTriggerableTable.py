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
        if "email" not in data or "tablename" not in data:
            raise Exception("Couldn't add a triggerable table; either user email or table name is missing")
        email = data["email"]
        tablename = data["tablename"]
        storage_userid = data["storage_userid"]

        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        dlc.createTriggerableTable(tablename)

        # store empty metadata
        bucket_metadata = []
        triggers_metadata_table = 'triggersInfoTable'
        metadata_key = tablename
        current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
        print("fetched data: " + str(current_meta))
        print("Getting existing key: " + metadata_key)
        print("  in table: " + triggers_metadata_table)
        keyfound = False
        if current_meta != None:
            try:
                meta_list = json.loads(current_meta)
                if type(meta_list) == type([]):
                    keyfound = True
                    print("  found with value: " + str(meta_list))
            except Exception as e:
                pass
        
        if keyfound == False:
            print("Key not found: " + str(metadata_key))
            # store metadata
            print("Creating key: " + metadata_key)
            print("  in table: " + triggers_metadata_table)
            print("  with value: " + str(bucket_metadata))
            dlc.put(metadata_key, json.dumps(bucket_metadata), tableName=triggers_metadata_table)

        # add to the list of triggerable tables
        trigger_tables = sapi.get(email + "_list_trigger_tables")
        if trigger_tables is not None and trigger_tables != "":
            trigger_tables = json.loads(trigger_tables)
        else:
            trigger_tables = {}

        if tablename not in trigger_tables:
            trigger_tables[tablename] = ''
            sapi.put(email + "_list_trigger_tables", json.dumps(trigger_tables))

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't add a triggerable table; "+str(e)
        response["data"] = response_data
        print(str(response))
        return response

    # finish successfully
    response_data = {}
    response = {}
    response["status"] = "success"
    response_data["message"] = "Table created: " + tablename
    response["data"] = response_data
    print(str(response))
    sapi.log(json.dumps(response))
    return response
