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

    response = {}
    response_data = {}

    success = False

    email = data["email"]
    storage_userid = data["storage_userid"]

    if "workflow" in data:
        workflow = data["workflow"]

        sapi.log(json.dumps(workflow))

        if "id" in workflow:
            workflows = sapi.get(email + "_list_workflows", True)
            if workflows is not None and workflows != "":
                workflows = json.loads(workflows)

                if workflow["id"] in workflows.values():
                    #workflowJSON = sapi.get(email + "_workflow_json_" + workflow["id"], True)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    workflowJSON = dlc.get("workflow_json_" + workflow["id"])
                    dlc.shutdown()

                    if workflowJSON is None:
                        workflowJSON = ""

                    wf = {}
                    wf["json"] = workflowJSON

                    response_data["workflow"] = wf
                    response_data["message"] = "Retrieved JSON for workflow " + workflow["id"] + "."

                    success = True

                else:
                    response_data["message"] = "Couldn't retrieve workflow JSON; no such workflow."
            else:
                response_data["message"] = "Couldn't retrieve workflow JSON; no such workflow."
        else:
            response_data["message"] = "Couldn't retrieve workflow JSON; malformed input."
    else:
        response_data["message"] = "Couldn't retrieve workflow JSON; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

