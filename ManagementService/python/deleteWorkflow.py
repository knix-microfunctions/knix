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
import os

import requests

MFN_ELASTICSEARCH = os.getenv("MFN_ELASTICSEARCH", os.getenv("MFN_HOSTNAME"))
ELASTICSEARCH_HOST = MFN_ELASTICSEARCH.split(':')[0]
try:
    ELASTICSEARCH_PORT = MFN_ELASTICSEARCH.split(':')[1]
except:
    ELASTICSEARCH_PORT = 9200

ELASTICSEARCH_URL = "http://" + ELASTICSEARCH_HOST + ":" + str(ELASTICSEARCH_PORT)

def delete_workflow_index(index_name):
    try:
        r = requests.delete(ELASTICSEARCH_URL + "/" + index_name, proxies={"http":None})
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            print('Could not connect to: ' + ELASTICSEARCH_URL)
        else:
            raise e

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
                    wf = sapi.get(email + "_workflow_" + workflow["id"], True)
                    if wf is not None and wf != "":
                        wf = json.loads(wf)
                        if wf["status"] == "undeployed" or wf["status"] == "failed":
                            for wn in workflows:
                                if workflows[wn] == workflow["id"]:
                                    del workflows[wn]
                                    break

                            # delete workflow logs
                            delete_workflow_index("mfnwf-" + workflow["id"])

                            sapi.delete(email + "_workflow_" + workflow["id"], True, True)
                            #sapi.delete(email + "_workflow_json_" + workflow["id"], True, True)
                            #sapi.delete(email + "_workflow_requirements_" + workflow["id"], True, True)

                            dlc = sapi.get_privileged_data_layer_client(storage_userid)
                            dlc.delete("workflow_json_" + workflow["id"])
                            dlc.delete("workflow_requirements_" + workflow["id"])
                            dlc.shutdown()

                            sapi.put(email + "_list_workflows", json.dumps(workflows), True, True)

                            response_data["message"] = "Deleted workflow " + workflow["id"] + "."

                            success = True

                        else:
                            response_data["message"] = "Couldn't delete workflow; workflow is still deployed. Undeploy workflow first."
                    else:
                        response_data["message"] = "Couldn't delete workflow; workflow metadata is not valid."
                else:
                    response_data["message"] = "Couldn't delete workflow; no such workflow."
            else:
                response_data["message"] = "Couldn't delete workflow; no such workflow."
        else:
            response_data["message"] = "Couldn't delete workflow; malformed input."
    else:
        response_data["message"] = "Couldn't delete workflow; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

