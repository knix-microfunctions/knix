#!/usr/bin/python3

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

""" Remove all Knative services
"""

import json
import os
import base64
import requests

with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
    token = f.read()
with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
    namespace = f.read()
with open("/opt/mfn/conf/new_workflow.conf","r") as f:
    conf = json.load(f)
app = conf["app"] #"microfunctions-workflow"
cafile = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
# offline
#with open("mgr-mfn1.json",'r') as f:
#    mgr = json.load(f)
#token = base64.b64decode(mgr["data"]["token"]).decode('utf-8')
#with open("ca.crt","wb") as f:
#    f.write(base64.b64decode(mgr["data"]["ca.crt"]))
#namespace = base64.b64decode(mgr["data"]["namespace"]).decode('ascii')
#print(token)
#os.environ["KUBERNETES_SERVICE_PORT_HTTPS"] = "6443"
#os.environ["KUBERNETES_SERVICE_HOST"] = "slsbell179167.nrt.lab"

kubeurl = "https://"+os.environ["KUBERNETES_SERVICE_HOST"]+":"+os.environ["KUBERNETES_SERVICE_PORT_HTTPS"]
if __name__ == "__main__":
    print('Checking if deployment exists')
    resp = requests.get(
        kubeurl+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services",
        headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
        verify=cafile,
        proxies={"https":""})
    
    if resp.status_code == 200:
        for d in resp.json()["items"]:
            if not d["metadata"]["labels"]["app"] == app:
                continue
            
            ksvcname = d["metadata"]["name"]
            print("Deleting MicroFunction Knative service "+d["metadata"]["name"])
            r = requests.delete(
                kubeurl+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services/"+ksvcname,
                headers={"Authorization": "Bearer "+token, "Content-Type": "application/yaml", "Accept": "application/json"},
                verify=cafile,
                json={"propagationPolicy": "Background"},
                proxies={"https":""})
            if r.status_code == 200:
                print("successfully deleted Knative service "+ksvcname)
            else:
                print("ERROR: "+resp.text)
