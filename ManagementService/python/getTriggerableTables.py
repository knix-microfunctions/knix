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

        # add to the list of triggerable tables
        trigger_tables = sapi.get(email + "_list_trigger_tables")
        if trigger_tables is not None and trigger_tables != "":
            trigger_tables = json.loads(trigger_tables)
        else:
            trigger_tables = {}

        list_tables = []
        for table in trigger_tables:
            list_tables.append(table)

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't list triggerable tables; "+str(e)
        response["data"] = response_data
        print(str(response))
        return response

    # finish successfully
    response_data["tables"] = list_tables
    response_data["message"] = "Found " + str(len(list_tables)) + " functions."

    response = {}
    response["status"] = "success"
    response["data"] = response_data
    print(str(response))
    sapi.log(json.dumps(response))
    return response
