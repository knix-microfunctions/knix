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

        sapi.log(json.dumps(workflow))

        if "id" in workflow and "json" in workflow:
            workflows = sapi.get(email + "_list_workflows", True)
            wf = sapi.get(email + "_workflow_" + workflow["id"], True)
            if workflows is not None and workflows != "" and wf is not None and wf != "":
                workflows = json.loads(workflows)
                wf = json.loads(wf)

                if workflow["id"] in workflows.values():
                    workflow["json"] = workflow["json"].replace(" ", "+")

                    wf["modified"] = time.time()
                    if "ASL_type" in workflow:
                        wf["ASL_type"] = workflow["ASL_type"]
                    else:
                        wf["ASL_type"] = "unknown"

                    sapi.put(email + "_workflow_" + workflow["id"], json.dumps(wf), True, True)

                    #sapi.put(email + "_workflow_json_" + workflow["id"], workflow["json"], True, True)
                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    dlc.put("workflow_json_" + workflow["id"], workflow["json"])
                    dlc.shutdown()

                    response_data["message"] = "Workflow JSON uploaded successfully."
                    response_data["workflow"] = wf

                    success = True

                else:
                    response_data["message"] = "Couldn't upload workflow JSON; no such workflow."
            else:
                response_data["message"] = "Couldn't upload workflow JSON; no such workflow."
        else:
            response_data["message"] = "Couldn't upload workflow JSON; malformed input."
    else:
        response_data["message"] = "Couldn't upload workflow JSON; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

