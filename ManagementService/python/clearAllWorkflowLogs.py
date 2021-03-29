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

def create_workflow_index(index_name):
    index_data = \
    {
        "mappings": {
            "properties": {
                "indexed": {"type": "long"},
                "timestamp": {"type": "long"},
                "loglevel": {"type": "keyword"},
                "hostname": {"type": "keyword"},
                "containername": {"type": "keyword"},
                "uuid": {"type": "keyword"},
                "userid": {"type": "keyword"},
                "workflowname": {"type": "keyword"},
                "workflowid": {"type": "keyword"},
                "function": {"type": "keyword"},
                "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
                "message": {"type": "text"}
            }
        }
    }

    print("Deleting workflow index: " + index_name)
    try:
        r = requests.put(ELASTICSEARCH_URL + "/" + index_name, json=index_data, proxies={"http":None})
        #response = r.json()
        #print(str(response))
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

    if "workflow" in data:
        workflow = data["workflow"]
        if "id" in workflow:
            workflows = sapi.get(email + "_list_workflows", True)
            if workflows is not None and workflows != "":
                workflows = json.loads(workflows)
                if workflow["id"] in workflows.values():
                    # first, delete the workflow logs
                    delete_workflow_index("mfnwf-" + workflow["id"])

                    # second, create the same index
                    create_workflow_index("mfnwf-" + workflow["id"])

                    success = True
                else:
                    response_data["message"] = "Couldn't clear logs; no such workflow."
            else:
                response_data["message"] = "Couldn't clear logs; no such workflow."
        else:
            response_data["message"] = "Couldn't clear logs; malformed input."
    else:
        response_data["message"] = "Couldn't clear logs; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response
