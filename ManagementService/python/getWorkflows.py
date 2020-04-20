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

    workflows = sapi.get(email + "_list_workflows", True)

    if workflows is not None and workflows != "":
        sapi.log(workflows)
        workflows = json.loads(workflows)
        wf_list = []
        for w in workflows:
            wf = sapi.get(email + "_workflow_" + workflows[w], True)
            if wf is not None and wf != "":
                wf = json.loads(wf)

                wf_status = sapi.get("workflow_status_" + wf["id"], True)

                if wf_status is not None and wf_status != "" and wf["status"] != wf_status:
                    wf["status"] = wf_status
                    sapi.put(email + "_workflow_" + wf["id"], json.dumps(wf), True, True)

                if "modified" not in wf:
                    wf["modified"] = 0

                wf_list.append(wf)

        response_data["workflows"] = wf_list
        response_data["message"] = "Found " + str(len(wf_list)) + " workflows."

    else:
        # no workflows yet
        response_data["workflows"] = []
        response_data["message"] = "No workflows yet."

    success = True

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

