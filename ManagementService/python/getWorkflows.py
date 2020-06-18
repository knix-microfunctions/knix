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

IN_KUBERNETES = False

if 'KUBERNETES_SERVICE_HOST' in os.environ:
    IN_KUBERNETES = True
    new_workflow_conf = {}
    conf_file = '/opt/mfn/SandboxAgent/conf/new_workflow.conf'
    try:
        with open(conf_file, 'r') as fp:
            new_workflow_conf = json.load(fp)
    except IOError as e:
        raise Exception("Unable to load "+conf_file+". Ensure that the configmap has been setup properly", e)
    app_fullname_prefix = ''
    if 'app.fullname.prefix' in new_workflow_conf:
        app_fullname_prefix = new_workflow_conf['app.fullname.prefix']+'-'

    with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
        token = f.read()
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
        namespace = f.read()

def get_knative_status(wf):
    # derive service name
    ksvcname = app_fullname_prefix + wf["id"].lower()
    resp = requests.get(
        "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1alpha1/namespaces/"+namespace+"/services/"+ksvcname,
        headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
        verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
        proxies={"https":""})
    if resp.status_code == 200:
        status = resp.json().get("status", {})
        for c in status.get("conditions", {}):
            #print(c)
            if c["type"] == "Ready" and c["status"] == "True":
                return "deployed"
        return "deploying"
    elif resp.status_code == 404:
        return "undeployed"
    else:
        resp.raise_for_status()

def get_sandbox_statuses(wf, sapi):
    workflow_id = wf["id"]

    status_map = sapi.retrieveMap(workflow_id + "_sandbox_status_map", is_private=True)

    sapi.log(status_map)

    num_running = 0
    num_failed = 0
    num_in_progress = 0
    num_stopped = 0
    errmsg_list = []
    for sb in status_map:
        sbinfo = status_map[sb]
        sbinfo = json.loads(sbinfo)
        if sbinfo["status"] == "deployed":
            num_running += 1
        elif sbinfo["status"] == "failed":
            num_failed += 1
            errmsg_list.append(sbinfo["errmsg"])
        elif sbinfo["status"] == "deploying":
            num_in_progress += 1
        elif sbinfo["status"] == "stopped":
            num_stopped += 1

    new_status = "deploying"
    if num_running > 0:
        new_status = "deployed"
    else:
        if num_failed != 0 and num_failed == len(status_map):
            new_status = "failed"
        elif (num_stopped + num_failed) == len(status_map):
            new_status = "undeployed"

    return new_status, errmsg_list

def check_and_update_workflow_status(email, wf, sapi):
    errmsg = ""
    wf_status, errmsg_list = get_sandbox_statuses(wf, sapi)

    # If there is a wf_status, i.e. if the wf exists and if we're running on k8s, then check Knative status
    if IN_KUBERNETES:
        k_status = get_knative_status(wf)
        #sapi.log("wfstatus:"+wf_status+" - knativestatus:"+k_status)
        # If ksvc status doesn't match wf_status, we might need to correct wf_status
        if k_status != wf_status:
            # if k_status is undeployed and wf_status is anything but failed, then overwrite wf_status with undeployed
            if k_status == "undeployed" and wf_status != "failed":
                wf_status = k_status
            # if k_status is anything but deployed but wf_status thinks it's deployed, then overwrite wf_status
            if k_status != "deployed" and wf_status == "deployed":
                wf_status = k_status

    if wf_status == "failed":
        errmsg = '\n'.join(errmsg_list).strip()

    if wf["status"] != wf_status:
        wf["status"] = wf_status
        sapi.put(email + "_workflow_" + wf["id"], json.dumps(wf), True, True)
        sapi.put("workflow_status_" + wf["id"], wf_status, is_private=True)

        wf["deployment_error"] = errmsg

    if wf_status == "deployed":
        wf["endpoints"] = list(sapi.retrieveSet(wf["id"] + "_workflow_endpoints", is_private=True))

    return wf


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
        if "workflow" in data and "id" in data["workflow"]:
            wfid = data["workflow"]["id"]
            if wfid not in workflows.values():
                raise Exception("Couldn't retrieve workflow status; no such workflow.")
            wf = sapi.get(email + "_workflow_" + wfid, True)
            if wf is None or wf == "":
                raise Exception("Couldn't retrieve workflow status; no such workflow.")

            if "modified" not in wf:
                wf["modified"] = 0

            if "ASL_type" not in wf:
                wf["ASL_type"] = "unknown"

            wf = json.loads(wf)
            wf = check_and_update_workflow_status(email, wf, sapi)

            response_data["workflow"] = wf
            response_data["message"] = "Retrieved workflow status " + wfid + "."
            response["status"] = "success"
            response["data"] = response_data
        else:
            wf_list = []
            for wfname in workflows:
                wfid = workflows[wfname]
                wf = sapi.get(email + "_workflow_" + wfid, True)
                if wf is None or wf == "":
                    continue

                wf = json.loads(wf)

                if "modified" not in wf:
                    wf["modified"] = 0

                if "ASL_type" not in wf:
                    wf["ASL_type"] = "unknown"

                wf = check_and_update_workflow_status(email, wf, sapi)

                wf_list.append(wf)

            response_data["workflows"] = wf_list
            if wf_list:
                response_data["message"] = "Found " + str(len(wf_list)) + " workflows."
            else:
                response_data["message"] = "No workflows yet."

            response["status"] = "success"
            response["data"] = response_data
    except Exception as exc:
        response["status"] = "failure"
        response_data["message"] = "Couldn't retrieve workflows and their status: " + str(exc)
        response["data"] = response_data

    sapi.log(json.dumps(response))

    return response
