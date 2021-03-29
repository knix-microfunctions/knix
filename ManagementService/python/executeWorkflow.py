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
import re

def execute_workflow(wfurl, wfinput):
    result = None
    if 'KUBERNETES_SERVICE_HOST' in os.environ:
        namespace = ""
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            namespace = f.read()
        # on k8s replace the wfurl with the local service url
        wfurl = re.sub(r'^.*://([^.]+).*', r'http://\1', wfurl)+"."+namespace+".svc"
    try:
        result = requests.post(wfurl, params={}, json=wfinput)
    except Exception as exc:
        raise

    return result

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    email = data["email"]

    try:
        workflows = sapi.get(email + "_list_workflows", True)
        if workflows is None or workflows == "":
            workflows = {}
        else:
            workflows = json.loads(workflows)

        # get single workflow status
        if "workflow" not in data and "id" not in data["workflow"] and "wfurl" not in data["workflow"] and "wfinput" not in data["workflow"]:
            raise Exception("Can't execute workflow; invalid parameters.")

        wfid = data["workflow"]["id"]
        if wfid not in workflows.values():
            raise Exception("Can't execute workflow; no such workflow.")

        wfurl = data["workflow"]["wfurl"]
        wfinput = data["workflow"]["wfinput"]

        # execute workflow here
        result = execute_workflow(wfurl, wfinput)

        response_data["result"] = result.json()
        response_data["message"] = "Executed workflow " + wfid + "."
        response["status"] = "success"
        response["data"] = response_data
    except Exception as exc:
        response["status"] = "failure"
        response_data["message"] = "Couldn't execute workflow: " + str(exc)
        response["data"] = response_data

    sapi.log(json.dumps(response))

    return response
