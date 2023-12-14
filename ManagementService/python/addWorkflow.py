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
import hashlib
import os
import time
import uuid

import requests

MFN_ELASTICSEARCH = os.getenv("MFN_ELASTICSEARCH", os.getenv("MFN_HOSTNAME"))
ELASTICSEARCH_HOST = MFN_ELASTICSEARCH.split(':')[0]
try:
    ELASTICSEARCH_PORT = MFN_ELASTICSEARCH.split(':')[1]
except:
    ELASTICSEARCH_PORT = 9200

ELASTICSEARCH_URL = "http://" + ELASTICSEARCH_HOST + ":" + str(ELASTICSEARCH_PORT)

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

    print("Creating workflow index: " + index_name)
    try:
        r = requests.put(ELASTICSEARCH_URL + "/" + index_name, json=index_data, proxies={"http":None})
        response = r.json()
        print(str(response))
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            print('Could not connect to: ' + ELASTICSEARCH_URL)
        else:
            raise e

def initialize_storage(sapi, wid):
    #sapi.get_privileged_data_layer_client(storage_userid, init_tables=True)
    # mfn internal tables
    #global_dlc = DataLayerClient(locality=1, for_mfn=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
    print("Initializing global mfn internal storage for workflow: " + wid)
    global_dlc = sapi.get_privileged_data_layer_client(for_mfn=True, sid=wid, init_tables=True)
    global_dlc.shutdown()

    # workflow private tables
    print("Initializing global workflow-private storage: " + wid)
    #global_dlc = DataLayerClient(locality=1, is_wf_private=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
    global_dlc = sapi.get_privileged_data_layer_client(is_wf_private=True, sid=wid, init_tables=True)
    global_dlc.shutdown()


def handle(value, sapi):
    assert isinstance(value, dict)
    data = value # data may contain "null" value

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
            #if "gpu_mem_usage" in workflow:
            wf["gpu_mem_usage"] = str(workflow["gpu_mem_usage"])
        wf['associatedTriggerableTables'] = {}
        wf['associatedTriggers'] = {}
        wf["id"] = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest().lower()

        # make a request to elasticsearch to create the workflow index
        create_workflow_index("mfnwf-" + wf["id"])

        #wf["on_gpu"] = True # add metadata on GPU requirements for this workflow. ToDo: make this configurable via GUI

        # initialize global workflow related storage (workflow-private and mfn internal tables)
        initialize_storage(sapi, wf["id"])

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
