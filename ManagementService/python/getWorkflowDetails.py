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
        if "email" not in data or "workflowname" not in data:
            raise Exception("Couldn't retrieve workflow details; either user email or name of the workflow is missing")
        email = data["email"]
        workflowname = data["workflowname"]
        storage_userid = data["storage_userid"]

        details = getWorkflowDetails(email, workflowname, sapi)
        response_data = details

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't retrieve workflow details; "+str(e)
        response["data"] = response_data
        return response

    response = {}
    response["status"] = "success"
    response["data"] = response_data
    return response


def getWorkflowDetails(email, workflowname, sapi):
    workflows = sapi.get(email + "_list_workflows", True)
    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
    else:
        workflows = {}

    if workflowname not in workflows:
        raise Exception("Couldn't fetch details for workflow: " + workflowname)
    wf_id = workflows[workflowname]

    wf = sapi.get(email + "_workflow_" + wf_id, True)
    if wf is None or wf == "":
        raise Exception("Couldn't retrieve workflow status.")
    wf = json.loads(wf)
    wf_status = sapi.get("workflow_status_" + wf_id, True)

    details = {}
    details["email"] = email
    details["name"] = workflowname
    details["id"] = wf_id
    details["status"] = wf_status
    if "endpoints" in wf:
        details["endpoints"] = wf["endpoints"]
    if "modified" in wf:
        details["modified"] = wf["modified"]
    if "associatedTriggerableTables" in wf:
        details["associatedTriggerableTables"] = wf["associatedTriggerableTables"]

    return details