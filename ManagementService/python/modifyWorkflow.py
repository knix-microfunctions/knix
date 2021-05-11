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

'''
# sample input 
{
  "action": "modifyWorkflow",
  "data": {
    "user": {
      "token": "...."
    },
    "workflow": {
            # to update workflow name, specify both id and name
            # to update workflows resources/annotations specify id and/or name and the optional field below

      "id": "asdf",
      "name": "qwerty",
      "knative": {
        "annotations": {                        # <if specified will merge with 'spec.template.metadata.annotations'>
          "autoscaling.knative.dev/target": "10",
          "autoscaling.knative.dev/panicWindowPercentage": "5.0",
          "autoscaling.knative.dev/panicThresholdPercentage": "110.0",
          "autoscaling.knative.dev/targetUtilizationPercentage": "70",
          "autoscaling.knative.dev/targetBurstCapacity": "10",
          "autoscaling.knative.dev/...": "..."
        },
        "container": {                          # <if specified will merge with 'spec.template.spec.containers[0]'>
          "image": "asdfasdfdf",                # <optional, overwrites 'spec.template.spec.containers[0].image'>
          "resources": {                        # <optional, overwrites 'spec.template.spec.containers[0].resources'>
            "requests": {
              "memory": "64Mi",
              "cpu": "250m",
              "tencent.com/vcuda-core": 4,
              "tencent.com/vcuda-memory": 3,
              "....": "..."
            },
            "limits": {
              "tencent.com/vcuda-core": 4,
              "tencent.com/vcuda-memory": 3,
              "memory": "128Mi",
              "cpu": "500m",
              "....": "..."
            }
          }
        },
        "spec": {                                   # <if specified, will merge with 'spec.template.spec>'
          "containerConcurrency": 50
        }
      }
    }
  }
}
'''


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

        if "id" in workflow and "name" in workflow:
            wf = sapi.get(email + "_workflow_" + workflow["id"], True)

            if wf is not None and wf != "":
                wf = json.loads(wf)

                workflows = sapi.get(email + "_list_workflows", True)
                if workflows is not None and workflows != "":
                    workflows = json.loads(workflows)
                    if wf["name"] in workflows:
                        del workflows[wf["name"]]
                else:
                    workflows = {}

                workflows[workflow["name"]] = workflow["id"]

                wf["name"] = workflow["name"]
                wf["modified"] = time.time()
                if "ASL_type" in workflow:
                    wf["ASL_type"] = workflow["ASL_type"]
                else:
                    wf["ASL_type"] = "unknown"

                sapi.put(email + "_workflow_" + wf["id"], json.dumps(wf), True)

                sapi.put(email + "_list_workflows", json.dumps(workflows), True)

                response_data["message"] = "Successfully modified workflow " + workflow["id"] + "."
                response_data["workflow"] = wf
                success = True
        elif "knative" in workflow and ("id" in workflow or "name" in workflow):
            id = None
            if "id" not in workflow:
                id = get_workflow_id(workflow["name"], email, sapi)
            else:
                id = workflow["id"]
            
            if id is not None:
                wf = sapi.get(email + "_workflow_" + id, True)
                wf = json.loads(wf)
                wf["knative"] = workflow["knative"]
                sapi.put(email + "_workflow_" + id, json.dumps(wf), True)
                success = True
                response_data["message"] = "New knative resource and annotation specifications will be applied next time the workflow is deployed."
            else:
                response_data["message"] = "Couldn't modify workflow resources; Unable to find workflow id."
        else:
            response_data["message"] = "Couldn't modify workflow; malformed input."
    else:
        response_data["message"] = "Couldn't modify workflow; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response


def get_workflow_id(workflow_name, email, context):
    id = None
    workflows = context.get(email + "_list_workflows", True)
    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
        if workflow_name in workflows:
            id = workflows[workflow_name]
    return id