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

    try:
        if "email" not in data or "name" not in data:
            raise Exception("Couldn't retrieve workflow details; either user email or name of the workflow is missing")
        email = data["email"]
        name = data["name"]
        storage_userid = data["storage_userid"]

        workflows = sapi.get(email + "_list_workflows", True)
        if workflows is not None and workflows != "":
            workflows = json.loads(workflows)
        else:
            workflows = {}

        if name not in workflows:
            raise Exception("Couldn't retrieve workflow details; workflow: " + name + " not found.")
        wf_id = workflows[name]

        wf = sapi.get(email + "_workflow_" + wf_id, True)
        if wf is None or wf == "":
            raise Exception("Couldn't retrieve workflow status.")
        wf = json.loads(wf)
        wf_status = sapi.get("workflow_status_" + wf_id, True)

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't retrieve workflow details; "+str(e)
        response["data"] = response_data
        return response

    # finish successfully
    response_data = {}
    response_data["email"] = email
    response_data["name"] = name
    response_data["id"] = wf_id
    response_data["status"] = wf_status
    details["endpoints"] = wf["endpoints"]
    response_data["modified"] = wf["modified"]

    response = {}
    response["status"] = "success"
    response["data"] = response_data
    sapi.log(json.dumps(response))
    return response
