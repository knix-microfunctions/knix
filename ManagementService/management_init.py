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

""" Deploy microfunctions's Management workflow inside the datalayer

This script creates the appropriate datalayer keys to deploy the microfunctions Management workflow. It borrows code from Management service's
addFunction, uploadFunctionCode, addWorkflow, uploadWorkflowJson, deployWorkflow

"""

import base64
import hashlib
import json
import os
import requests
import socket
import stat
import subprocess
import sys
import time
import traceback
import uuid
from DataLayerClient import DataLayerClient

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TCompactProtocol

from data_layer.message.ttypes import KeyValuePair
from data_layer.message.ttypes import Metadata
from data_layer.service import DataLayerService

### Management workflow configuration
email = "admin@management"
workflowid = "Management"
sandboxid = "Management"
workflowfile = "./workflow_management_service.json"
workflowdir = "python"
WF_TYPE_SAND = 0
WF_TYPE_ASL = 1

def get_storage_userid(email):
    storage_userid = email.replace("@", "AT")
    storage_userid = storage_userid.replace(".", "_")
    storage_userid = storage_userid.replace("-", "_")
    return storage_userid

### global variables set at runtime
DLCLIENT=None
DLCLIENT_MANAGEMENT=None

MANAGEMENT_SERVICE_EXPOSED_PORT = 80

def parse_states(state_map):
    functions = []
    states = []
    for wfsname in state_map:
        wfs = state_map[wfsname]
        stype = wfs["Type"]
        sresource = wfsname

        if stype == "Task":
            functions.append(wfs["Resource"])

        elif stype == 'Parallel':
            # add the parallel state function worker
            states.append({'name':sresource,'type':stype})
            # find recursively everything that is in the branches
            for branch in state_map[sresource]['Branches']:
                sub_functions, sub_states = parse_states(branch['States'])
                # add found functions to list of function workers
                functions.extend(sub_functions)
                states.extend(sub_states)

        elif stype == 'Map':
            # add the Map state iterator function worker
            states.append({'name':sresource,'type':stype})
            # find recursively everything that is in the branch
            branch = state_map[sresource]['Iterator']
            sub_functions, sub_states = parse_states(branch['States'])
            # add found functions to list of function workers
            functions.extend(sub_functions)
            states.extend(sub_states)

        elif stype in {'Choice', 'Pass', 'Wait', 'Fail', 'Succeed'}:
            states.append({'name':sresource,'type':stype})
        else:
            raise Exception("Unknown state type: " + stype)
    return functions, states


def parse_workflow(wfobj):
    if 'StartAt' in wfobj:
        # ASL
        wf_state_map = {}
        resource_path_map = {}
        resource_type_map = {}
        errmsg = ""
        wfexit = "end"
        return parse_states(wfobj['States'])
    else:
        functions = []
        states = []
        # microfunctions workflow (i.e., non-ASL)
        wffunctions = wfobj["functions"]
        for wff in wffunctions:
            fname = wff["name"]
            functions.append(fname)
        return functions, states

def getAndPrintKey(key):
    v = DLCLIENT.get(key)
    print("[" + key + "] " + str(v))

def printWorkflowKeys(workflowid):
    getAndPrintKey("workflow_"+workflowid)
    getAndPrintKey("workflow_json_"+workflowid)
    getAndPrintKey("workflow_requirements_"+workflowid)
    getAndPrintKey("list_grains")

def printFunctionKeys():
    gdv = DLCLIENT.get("list_grains")
    if gdv != "" and gdv != None:
        gd = json.loads(gdv)
    else:
        gd = {}

    for key in gd.keys():
        fid = gd[key]
        getAndPrintKey("grain_" + fid)
        getAndPrintKey("grain_source_" + fid)
        getAndPrintKey("grain_requirements_" + fid)

def printDeploymentKey(workflowid):
    getAndPrintKey("deployment_info_workflow_" + workflowid)

def create_workflow_index(index_name):
    '''
    curl --header "Content-Type: application/json" \
    --request PUT \
    --data '
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
    }' \
    http://$(hostname):9200/mfnwf
    '''
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
    hostname = os.getenv("MFN_HOSTNAME", socket.gethostname().split('.',1)[0])
    ELASTICSEARCH_URL = "http://" + os.getenv("ELASTICSEARCH_CONNECT", hostname+":9200")
    try:
        r=requests.put(ELASTICSEARCH_URL + "/" + index_name, json=index_data, proxies={"http":None})
        response = r.json()
        print(str(response))
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            return False, 'Could not connect to: ' + ELASTICSEARCH_URL, None, None
        else:
            raise e

def upload_workflow(email, workflowid, workflowfile, workflowdir, sandboxid = None):
    """ Upload functions and workflow description to the storage of the ManagementService (SBOX: Management, WFID: Management) """

    print("Uploading workflow from "+workflowfile)

    # create workflow
    wf = {}
    wf["name"] = workflowid
    wf["status"] = "undeployed"
    wf["modified"] = time.time()
    wf["id"] = workflowid
    wf["log_index_name"] = "mfnwf-" + wf["id"].lower()

    create_workflow_index(wf["log_index_name"])

    DLCLIENT.put("workflow_"+workflowid, json.dumps(wf))

    # set workflow_json
    with open(workflowfile,"r") as f:
        wfobj = json.load(f)
    DLCLIENT.put("workflow_json_"+workflowid, base64.b64encode(json.dumps(wfobj).encode()).decode())

    is_asl_workflow = False
    if 'StartAt' in wfobj:
        is_asl_workflow = True

    # set workflow_requirements
    wf_requirements = DLCLIENT.get("workflow_requirements_"+workflowid)
    if wf_requirements is None:
        DLCLIENT.put("workflow_requirements_"+workflowid,"")

    # get list of functions
    functions, states = parse_workflow(wfobj)
    gdv = DLCLIENT.get("list_grains")
    if gdv != "" and gdv != None:
        gd = json.loads(gdv)
    else:
        gd = {}

    resource_info_map = {}
    for fname in functions:
        print("Uploading function "+fname)
        # store function info
        g={"name":fname,
           "runtime":"Python 3.6"}
        if fname in gd:
            if isinstance(gd[fname], dict):
                g["id"] = gd[fname]["id"]
            else:
                g["id"] = gd[fname]
        else:
            g["id"] = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        g["modified"]=time.time()
        DLCLIENT.put("grain_" + g["id"], json.dumps(g))
        gd[fname] = g["id"]

        ### Python source code file source
        if os.path.exists(workflowdir+"/"+fname+".py"):
            ### Function python file to upload
            with open(workflowdir+"/"+fname+".py","r") as f:
                DLCLIENT.put("grain_source_" + g["id"], base64.b64encode(f.read().encode()).decode())

        isZip = False
        if os.path.exists(workflowdir+"/"+fname+".zip"):
            isZip = True
            # upload ZIP file in chunks
            chunks=[]
            with open(workflowdir+"/"+fname+".zip", 'rb') as zf:
                content = base64.b64encode(zf.read()).decode()
                for pos in range(0,len(content),1024*1024):
                    chunks.append(content[pos:pos+1024*1024])
            for c in range(len(chunks)):
                DLCLIENT.put("grain_source_zip_" + g["id"] + "_chunk_" + str(c), chunks[c])
            function_source_zip_num_chunks = DLCLIENT.put("grain_source_zip_num_chunks_" + g["id"], str(len(chunks)))

            # create metadata information on the ZIP file contents
            filename = workflowdir+"/"+fname+".zip"
            metadata = "Last uploaded Zip file: <b>%s</b><br><br><table border='1'>" % (filename.split('/')[-1]) # what is this hack?
            metadata += "</table>"
            DLCLIENT.put("grain_source_zip_metadata_" + g["id"], base64.b64encode(metadata.encode()).decode())

        # function requirements
        function_requirements = str('').encode()
        if os.path.exists(workflowdir+"/"+fname+"_requirements.txt"):
            with open(workflowdir+"/"+fname+"_requirements.txt", "r") as f:
                reqs = f.read()
                DLCLIENT.put("grain_requirements_" + g["id"], base64.b64encode(reqs.encode()).decode())
        else:
            DLCLIENT.put("grain_requirements_" + g["id"], "")

        resource_info = {}
        resource_info["name"] = g["name"]
        resource_info["id"] = g["id"]
        resource_info["runtime"] = g["runtime"]
        resource_info["type"] = "code"
        resource_info["ref"] = "grain_source_" + g["id"]
        if isZip == True:
            resource_info["type"] = "zip"
            resource_info["ref"] = "grain_source_zip_num_chunks_" + g["id"]

        resource_info_map[g["name"]] = resource_info

    # eventually store function list with new function infos
    DLCLIENT.put("list_grains", json.dumps(gd))


    # generate a deployment dict + key in datalayer to be used by sandboxagent
    workflow_info = {}
    if sandboxid is None:
        workflow_info["sandboxId"] = workflowid
    else:
        workflow_info["sandboxId"] = sandboxid
    workflow_info["workflowId"] = workflowid
    workflow_info["workflowName"] = workflowid
    workflow_info["usertoken"] = "unused"
    if is_asl_workflow:
        workflow_info["workflowType"] = WF_TYPE_ASL
    else:
        workflow_info["workflowType"] = WF_TYPE_SAND
    workflow_info["json_ref"] = "workflow_json_" + workflowid
    req = {}
    req["installer"] = "pip"
    workflow_info["sandbox_requirements"] = req

    deployment_info = {}
    deployment_info["workflow"] = workflow_info
    deployment_info["resources"] = resource_info_map
    deployment_info["username"] = email
    DLCLIENT_MANAGEMENT.put("deployment_info_workflow_" + workflowid, json.dumps(deployment_info))
    # if we've come here, the workflow and its functions should have been updated
    return deployment_info

def printKeys(workflowid):
    printWorkflowKeys(workflowid)
    printFunctionKeys()
    printDeploymentKey(workflowid)

def printUsage():
    print("""usage: %s [start|stop|print]
environment variables:
\tMFN_HOSTNAME - name of the docker host to deploy to (default: short hostname)
\tELASTICSEARCH_CONNECT - elasticsearch connect string (default <MFN_HOSTNAME>:9200)
\tMFN_DATALAYER - datalayer service local to the deployment host (default <MFN_HOSTNAME>:4998)
                  should use the physical host name when queue is running on bare-metal
                  on kubernetes, this should be the headless service name of the datalayer service
""" % (sys.argv[0]))

if __name__ == "__main__":
    # we're run from the command line (as a program)
    if len(sys.argv) > 1:
        action = str(sys.argv[1])
    else:
        printUsage()
        sys.exit(1)


    hostname = os.getenv("MFN_HOSTNAME", socket.gethostname().split('.',1)[0])
    # Wait on Datalayer to be resolvable
    print("Waiting on DataLayer")
    while True:
        host,port = os.getenv("MFN_DATALAYER",hostname+":4998").rsplit(":",1)
        try:
            addr = socket.gethostbyname(host)
            connect = addr+":"+port
            break
        except:
            traceback.print_exc()
            print("Waiting another 5s for "+host+" to be resolvable")
            time.sleep(5)

    # client for bucket "storage_" + get_storage_userid(email) + ";defaultTable"
    DLCLIENT = DataLayerClient(locality=1, suid="adminATmanagement", connect=connect, init_tables=True)
    # client for bucket "sbox_Management;wf_Management"
    DLCLIENT_MANAGEMENT = DataLayerClient(locality=1, sid="Management", wid="Management", is_wf_private=True, connect=connect, init_tables=True)
    # client for mfn internal storage (for completeness)
    DLCLIENT_MFN = DataLayerClient(locality=1, sid="Management", for_mfn=True, connect=connect, init_tables=True)
    DLCLIENT_MFN.shutdown()

    '''
    keyspace = "storage_" + get_storage_userid(email)
    tablename = "defaultTable"
    BUCKETNAME = keyspace + ";" + tablename

    keyspace_management = "sbox_Management"
    tablename_management = "wf_Management"
    BUCKETNAME_MANAGEMENT = keyspace_management + ";" + tablename_management

    # Create tables in the Datalayer server
    host,port = os.getenv("DATALAYER_CONNECT",hostname+":4998").rsplit(":",1)
    _socket = TSocket.TSocket(host, int(port))
    _transport = TTransport.TFramedTransport(_socket)
    _protocol = TCompactProtocol.TCompactProtocol(_transport)
    _datalayer = DataLayerService.Client(_protocol)
    _transport.open()

    _datalayer.createKeyspace(keyspace, Metadata(replicationFactor=3), 1)
    _datalayer.createTable(keyspace, tablename, Metadata(tableType="default"), 1)
    #time.sleep(1)
    _datalayer.createKeyspace(keyspace_management, Metadata(replicationFactor=3), 1)
    _datalayer.createTable(keyspace_management, tablename_management, Metadata(tableType="default"), 1)

    _transport.close()
    '''

    if action == "start":
        # Manually creates and deploys a workflow like the management action deployWorkflow would
        # Upload the workflow and its functions to the data layer
        deployment_info = upload_workflow(email, workflowid, workflowfile, workflowdir, sandboxid)

        # Create the container that runs the workflow using the wf metadata
        workflow_info = deployment_info["workflow"]

        sys.path.append(workflowdir)
        if os.getenv("KUBERNETES_PORT", None) != None:
            import deployWorkflow
            url, endpoint_key = deployWorkflow.create_k8s_deployment(email, workflow_info, "Python", 0, 0, management=True)
            DLCLIENT_MANAGEMENT.putMapEntry("Management_workflow_endpoint_map", endpoint_key, url)
            # Kubernetes mode only has one url
            endpoint_list = [url]
            DLCLIENT_MANAGEMENT.put("management_endpoints", json.dumps(endpoint_list))
        else:
            host_to_deploy=(hostname,socket.gethostbyname(hostname))
            #Container in the bare metal case will be started by start_management.sh
            #deployWorkflow.start_docker_sandbox(host_to_deploy, email, workflow_info["sandboxId"], workflow_info["workflowId"], workflow_info["workflowName"])
            url = "http://" + host_to_deploy[1] + ":" + str(MANAGEMENT_SERVICE_EXPOSED_PORT)
            endpoint_key = hashlib.sha256(str(time.time()).encode()).hexdigest()
            DLCLIENT_MANAGEMENT.putMapEntry("Management_workflow_endpoint_map", endpoint_key, url)

            endpoint_list = DLCLIENT_MANAGEMENT.get("management_endpoints")
            if endpoint_list is None or endpoint_list == "":
                endpoint_list = []
            else:
                endpoint_list = json.loads(endpoint_list)

            endpoint_set = set(endpoint_list)
            endpoint_set.add(url)
            endpoint_list = list(endpoint_set)
            DLCLIENT_MANAGEMENT.put("management_endpoints", json.dumps(endpoint_list))

            print("endpoint urls: " + json.dumps(endpoint_list))
            print("endpoint_key: " + endpoint_key)
            print(os.getenv("HTTP_PROXY"))
            with open(".env", "w") as f:
                f.write("MFN_HOSTNAME="+ hostname + "\n")
                f.write("USERID="+ email + "\n")
                f.write("SANDBOXID="+ workflow_info["sandboxId"] + "\n")
                f.write("WORKFLOWID="+ workflow_info["workflowId"] + "\n")
                f.write("WORKFLOWNAME="+ workflow_info["workflowName"] + "\n")
                f.write("MFN_QUEUE=/opt/mfn/redis-server/redis.sock\n")
                f.write("MFN_DATALAYER="+ os.getenv("DATALAYER_CONNECT",hostname+":4998") + "\n")
                f.write("MFN_ELASTICSEARCH="+ os.getenv("ELASTICSEARCH_CONNECT",hostname+":9200") + "\n")
                f.write("MFN_ENDPOINT_KEY=" + endpoint_key + "\n")
                #f.write("MFN_NGINX="+ os.getenv("NGINX_CONNECT",hostname+":80") + "\n")
                f.write("HTTP_PROXY="+ os.getenv("HTTP_PROXY", "") + "\n")
                f.write("HTTPS_PROXY="+ os.getenv("HTTPS_PROXY", "") + "\n")
                f.write("http_proxy="+ os.getenv("http_proxy", "") + "\n")
                f.write("https_proxy="+ os.getenv("https_proxy", "") + "\n")
                f.write("no_proxy="+ os.getenv("no_proxy", "") + "\n")
                f.write("NO_PROXY="+ os.getenv("NO_PROXY", "") + "\n")
            os.chmod(".env", 0o0755)

            with open("start_management.sh", "w") as f:
                #f.write("docker run --network host -d --ulimit nofile=262144:262144 --name Management --env-file .env --log-opt max-size=500m --log-opt max-file=5 microfn/sandbox\n")
                f.write("docker run -d --ulimit nofile=262144:262144 --name Management --env-file .env --log-opt max-size=500m --log-opt max-file=5 -P -p " + str(MANAGEMENT_SERVICE_EXPOSED_PORT) + ":8080 microfn/sandbox\n")
            os.chmod("start_management.sh", 0o0775)

        DLCLIENT.shutdown()
        DLCLIENT_MANAGEMENT.shutdown()
    elif action == "print":
        printKeys(workflowid)
    else:
        printUsage()
