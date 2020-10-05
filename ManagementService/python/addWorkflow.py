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
import uuid
import hashlib
import time

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False

    email = data["email"]
    

    if "workflow" in data:
        workflow = data["workflow"]

        sapi.log(json.dumps(workflow))

        wf = {}
        wf["name"] = workflow["name"]
        wf["status"] = "undeployed"
        wf["modified"] = time.time()
        wf["endpoints"] = []
        #wf["gpu_usage"] = None
        if "gpu_usage" in workflow:
            wf["gpu_usage"] = str(workflow["gpu_usage"])

        wf["id"] = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

        #wf["on_gpu"] = True # add metadata on GPU requirements for this workflow. ToDo: make this configurable via GUI

        sapi.put(email + "_workflow_" + wf["id"], json.dumps(wf), True, True)
        #sapi.put(email + "_workflow_json_" + wf["id"], "", True, True)
        #sapi.put(email + "_workflow_requirements_" + wf["id"], "", True, True)

        workflows = sapi.get(email + "_list_workflows", True)
        if workflows is not None and workflows != "":
            workflows = json.loads(workflows)
        else:
            workflows = {}

        workflows[wf["name"]] = wf["id"]

        sapi.put(email + "_list_workflows", json.dumps(workflows), True, True)

        response_data["message"] = "Workflow added successfully."
        response_data["workflow"] = wf

        success = True

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"
        response_data["message"] = "Couldn't add workflow."

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

