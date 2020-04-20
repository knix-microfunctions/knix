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

    if "workflow" in data:
        workflow = data["workflow"]

        sapi.log(json.dumps(workflow))
        '''
        if "id" in workflow:
            wfhosts = sapi.get(email + "_workflow_hosts_" + workflow["id"], True)

            if wfhosts is not None and wfhosts != "":
                # check each host's output to the data layer
                wfhosts = json.loads(wfhosts)

                clear_log_instruction = {}
                clear_log_instruction["action"] = "--clear-log"
                clear_log_instruction["sandboxId"] = workflow["id"]
                clear_log_instruction["workflowId"] = workflow["id"]
                clear_log_instruction["logType"] = "log"

                for host in wfhosts:
                    sapi.delete("workflow_log_log_" + host + "_" + workflow["id"], True, True)
                    sapi.add_dynamic_workflow({"next": "HMQ_" + host, "value": clear_log_instruction})

                success = True

            else:
                response_data["message"] = "Couldn't clear log; workflow is not active."
        else:
            response_data["message"] = "Couldn't clear log; malformed input."
        '''
        success = True
    else:
        response_data["message"] = "Couldn't clear log; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value":response})

    sapi.log(response["status"])

    return {}

