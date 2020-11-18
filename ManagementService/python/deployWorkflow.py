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
import base64
import hashlib
import os
import time
import traceback

import docker
from docker.types import LogConfig
import requests
import time
import random

WF_TYPE_SAND = 0
WF_TYPE_ASL = 1

def get_kv_pairs(testdict, keys, dicts=None):
    # find and return kv pairs with particular keys in testdict
    if not dicts:
        dicts = [testdict]
        testdict = [testdict]  
    data = testdict.pop(0)
    if isinstance(data, dict):
        data = data.values()
    for d in data:        
        if isinstance(d, dict) or isinstance(d, list): # check d for type        
            testdict.append(d)
            if isinstance(d, dict):
                dicts.append(d)
    if testdict: # no more data to search
        return get_kv_pairs(testdict, keys, dicts)
    return [(k, v) for d in dicts for k, v in d.items() if k in keys]

def is_asl_workflow(wfobj):
    return 'StartAt' in wfobj and 'States' in wfobj and isinstance(wfobj['States'], dict)

def check_workflow_functions(wf_type, wfobj, email, sapi):
    # this function does sanity checking:
    # check whether all resources/functions referred in the workflow have been uploaded
    success = True
    errmsg = ""
    wfexit = "end"

    resource_names_to_be_checked = {}

    if wf_type == WF_TYPE_ASL:
        wf_state_map = wfobj['States']
        for state_names in list(wf_state_map.keys()):
            if wf_state_map[state_names]["Type"] == "Parallel":
                parallelStateName = state_names

                for branches in wf_state_map[parallelStateName]['Branches']:
                    for state in list(branches['States'].keys()): # state is the key
                        wf_state_map[state] = branches['States'][state] # add the state to the state map root

            if wf_state_map[state_names]["Type"] == "Map":
                mapStateName = state_names
                iterator = wf_state_map[mapStateName]['Iterator'] # this is a dict

                states_dict = iterator['States'] # this is a also dict
                print (json.dumps(states_dict))
                for state in states_dict.keys():
                    print ("FOUND MAP STATE: "+str(state))
                    wf_state_map[state] = states_dict[state]

                """
                for iterators in wf_state_map[mapStateName]['Iterator']:
                    for state in list(iterators['States'].keys()): # state is the key
                        wf_state_map[state] = iterators['States'][state] # add the state to the state map root
                """

        for wfsname in wf_state_map:
            wfs = wf_state_map[wfsname]
            if wfs["Type"] == "Task":
                resource_names_to_be_checked[wfs["Resource"]] = True
    else:
        if "exit" in wfobj:
            wfexit = wfobj["exit"]
        elif "end" in wfobj:
            wfexit = wfobj["end"]

        # ensure that the state names or function names are unique (i.e., no duplication)
        function_map = {}
        wffunctions = wfobj["functions"]
        for wff in wffunctions:
            state_name = wff["name"]
            if wfexit == state_name:
                errmsg = "End of the workflow MUST NOT be a function: " + state_name
                success = False
                break

            if state_name in function_map.keys():
                errmsg = "The function names should be unique: " + state_name
                success = False
                break
            else:
                # keep track, so that we can check whether we've seen it before
                function_map[state_name] = True

            resource_name = state_name
            if "resource" in wff:
                resource_name = wff["resource"]

            resource_names_to_be_checked[resource_name] = True

    if success:
        if not resource_names_to_be_checked.keys():
            uploaded_resources = {}
        else:
            uploaded_resources = sapi.get(email + "_list_grains", True)
            if uploaded_resources is not None and uploaded_resources != "":
                uploaded_resources = json.loads(uploaded_resources)
            else:
                success = False
                errmsg = "Could not retrieve uploaded functions list."

    if success:
        for resource_name in list(resource_names_to_be_checked.keys()):
            if resource_name not in uploaded_resources:
                success = False
                errmsg += "\nResource has not been uploaded yet: " + resource_name

    return success, errmsg, resource_names_to_be_checked, uploaded_resources

def compile_resource_info_map(resource_names, uploaded_resources, email, sapi, dlc):
    # this function compiles the resource info map used by the deployment
    # initialization
    resource_info_map = {}

    for resource_name in list(resource_names.keys()):
        resource_info = {}
        if resource_name in uploaded_resources:
            resource_info["id"] = uploaded_resources[resource_name]
            resource_id = resource_info["id"]
            resource_metadata = sapi.get(email + "_grain_" + resource_id, True)
            if resource_metadata is not None and resource_metadata != "":
                resource_metadata = json.loads(resource_metadata)
                if "runtime" in resource_metadata:
                    resource_info["runtime"] = resource_metadata["runtime"]

            num_chunks_str = dlc.get("grain_source_zip_num_chunks_" + resource_id)
            try:
                num_chunks = int(num_chunks_str)
                is_zip = True
            except Exception as exc:
                is_zip = False

            resource_info["type"] = "code"
            resource_info["ref"] = "grain_source_" + resource_id
            if is_zip:
                resource_info["type"] = "zip"
                resource_info["ref"] = "grain_source_zip_num_chunks_" + resource_id

            resource_info_map[resource_name] = resource_info

    return resource_info_map

def start_docker_sandbox(host_to_deploy, uid, sid, wid, wname, sandbox_image_name):
    """ Launch the docker run command remotely
    Parameters:
    host_to_deploy set(hostname, ip): IP is used to connect docker, the pair is given as extra host (/etc/host) to the launched container
    uid - user id, typically cleansed email address, e.g. jdoe_at_example_com
    sid - sandbox id
    wid - workflow id
    """
    ulimit_nofile = docker.types.Ulimit(name='nofile', soft=262144, hard=262144)
    ulimit_list = [ulimit_nofile]

    # set up the env variables
    env_vars = {}
    env_vars["MFN_HOSTNAME"] = host_to_deploy[0]
    env_vars["MFN_ELASTICSEARCH"] = os.getenv("MFN_ELASTICSEARCH")
    env_vars["MFN_QUEUE"] = "127.0.0.1:"+os.getenv("MFN_QUEUE").split(':')[1]
    env_vars["MFN_DATALAYER"] = host_to_deploy[0]+":"+os.getenv("MFN_DATALAYER").split(':')[1]
    env_vars["USERID"] = uid
    env_vars["SANDBOXID"] = sid
    env_vars["WORKFLOWID"] = wid
    env_vars["WORKFLOWNAME"] = wname
    endpoint_key = hashlib.sha256(str(time.time()).encode()).hexdigest()
    env_vars["MFN_ENDPOINT_KEY"] = endpoint_key
    env_vars["HTTP_PROXY"] = os.getenv("HTTP_PROXY")
    env_vars["HTTPS_PROXY"] = os.getenv("HTTPS_PROXY")
    env_vars["http_proxy"] = os.getenv("http_proxy")
    env_vars["https_proxy"] = os.getenv("https_proxy")
    env_vars["no_proxy"] = os.getenv("no_proxy")

    lc = LogConfig(type=LogConfig.types.JSON, config={"max-size": "50m", "max-file": "5"})

    success = False
    try:
        client = docker.DockerClient(base_url="tcp://" + host_to_deploy[1] + ":2375") # use IP address
        success = True
    except Exception as exc:
        print("Error launching sandbox; can't connect to: " + host_to_deploy[1] + ":2375")
        print(traceback.format_exc())
        success = False

    if success:
        try:
            sandbox = client.containers.get(sid)
            sandbox.stop()
            sandbox.remove(force=True)
        except Exception as exc:
            pass

    if success:
        try:
            print("Starting sandbox docker container for: " + uid + " " + sid + " " + wid + " " + sandbox_image_name)
            print("Docker daemon: " + "tcp://" + host_to_deploy[1] + ":2375" + ", environment variables: " + str(env_vars))
            if sandbox_image_name.endswith("gpu"):
                client.containers.run(sandbox_image_name, init=True, detach=True, ports={"8080/tcp": None}, ulimits=ulimit_list, auto_remove=True, name=sid, environment=env_vars, extra_hosts={host_to_deploy[0]:host_to_deploy[1]}, log_config=lc, runtime="nvidia")
            else: 
                client.containers.run(sandbox_image_name, init=True, detach=True, ports={"8080/tcp": None}, ulimits=ulimit_list, auto_remove=True, name=sid, environment=env_vars, extra_hosts={host_to_deploy[0]:host_to_deploy[1]}, log_config=lc)
            # TEST/DEVELOPMENT: no auto_remove to access sandbox logs
        except Exception as exc:
            print("Error launching sandbox: " + str(host_to_deploy) + " " + uid + " " + sid + " " + wid)
            print(traceback.format_exc())
            success = False
        finally:
            client.close()

    return success, endpoint_key

def get_workflow_host_port(host_to_deploy, sid):

    success = False
    try:
        apiclient = docker.APIClient(base_url="tcp://" + host_to_deploy[1] + ":2375") # use IP address
        success = True
    except Exception as exc:
        print("Error updating workflow endpoints; " + host_to_deploy[1] + ":2375")
        print(traceback.format_exc())
        success = False

    if success:
        try:
            settings = apiclient.inspect_container(sid)
            ports = settings["NetworkSettings"]["Ports"]
            port_map = ports["8080/tcp"][0]
            host_port = port_map["HostPort"]
            success = True
        except Exception as exc:
            print("Error updating workflow endpoints; can't connect to: " + str(host_to_deploy) + " " + sid)
            print(traceback.format_exc())
            success = False
        finally:
            apiclient.close()

    return success, host_port

def create_k8s_deployment(email, workflow_info, runtime, gpu_usage, management=False):
    # KUBERNETES MODE
    new_workflow_conf = {}
    conf_file = '/opt/mfn/SandboxAgent/conf/new_workflow.conf'
    try:
        with open(conf_file, 'r') as fp:
            new_workflow_conf = json.load(fp)
    except IOError as e:
        raise Exception("Unable to load "+conf_file+". Ensure that the configmap has been setup properly", e)
    ksvc_file = '/opt/mfn/SandboxAgent/conf/kservice.json'
    try:
        with open(ksvc_file, 'r') as fp:
            kservice = json.load(fp)
    except IOError as e:
        raise Exception("Unable to load "+ksvc_file+". Ensure that the configmap has been setup properly", e)

    # Kubernetes labels cannot contain @ or _ and should start and end with alphanumeric characters
    wfNameSanitized = 'wf-' + workflow_info["workflowId"].replace('@', '-').replace('_', '-').replace('/','-').lower() + '-wf'
    #wfActualNameSanitized = 'wf-' + workflow_info["workflowName"].replace('@', '-').replace('_', '-').replace('/','-').lower() + '-wf'
    if len(wfNameSanitized) > 63:
       print("Error creating kubernetes deployment for "+email+" "+workflow_info["workflowId"] + ", workflow name too long")
 
    emailSanitized = 'u-' + email.replace('@', '-').replace('_', '-').lower() + '-u'
    # Pod, Deployment and Hpa names for the new workflow will have a prefix containing the workflow name and user name
    app_fullname_prefix = ''
    if 'app.fullname.prefix' in new_workflow_conf:
        app_fullname_prefix = new_workflow_conf['app.fullname.prefix']+'-'# + wfNameSanitized + '-' + emailSanitized + '-'

    # Create a Deployment
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
        token = f.read()
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
        namespace = f.read()

    ksvcname = app_fullname_prefix + workflow_info["workflowId"].lower()
    endpoint_key = hashlib.sha256(str(time.time()).encode()).hexdigest()

    kservice['metadata']['name'] = ksvcname
    kservice['metadata']['namespace'] = namespace
    labels = kservice['metadata']['labels']
    labels['user'] = emailSanitized
    labels['workflow'] = wfNameSanitized
    labels['workflowid'] = workflow_info["workflowId"]
    labels = kservice['spec']['template']['metadata']['labels']
    labels['user'] = emailSanitized
    labels['workflowid'] = workflow_info["workflowId"]
    kservice['spec']['template']['spec']['containers'][0]['image'] = new_workflow_conf['image.'+runtime]
    env = kservice['spec']['template']['spec']['containers'][0]['env']
    env.append({'name': 'MFN_ENDPOINT_KEY', 'value': endpoint_key})
    env.append({'name': 'USERID', 'value': email})
    env.append({'name': 'SANDBOXID','value': workflow_info["sandboxId"]})
    env.append({'name': 'WORKFLOWID', 'value': workflow_info["workflowId"]})
    env.append({'name': 'WORKFLOWNAME', 'value': workflow_info["workflowName"]})

    # apply gpu_usage fraction to k8s deployment configuration
    print("GPU sage in create_k8s_service: "+ str(gpu_usage))
    use_gpus = gpu_usage

    if runtime=="Java": # non gpu python function
        # overwrite values from values.yaml for new workflows
        #kservice['spec']['template']['spec']['containers'][0]['resources']['limits']['nvidia.com/gpu'] = str(use_gpus)
        #kservice['spec']['template']['spec']['containers'][0]['resources']['requests']['nvidia.com/gpu'] = str(use_gpus)
        kservice['spec']['template']['spec']['containers'][0]['image'] = "localhost:5000/microfn/sandbox_java" 

    if not management and use_gpus == 0. and runtime=="Python": # non gpu python function
        # overwrite values from values.yaml for new workflows
        kservice['spec']['template']['spec']['containers'][0]['resources']['limits'].pop('nvidia.com/gpu', None) # ['nvidia.com/gpu'] = str(use_gpus)
        kservice['spec']['template']['spec']['containers'][0]['resources']['requests'].pop('nvidia.com/gpu', None) # ['nvidia.com/gpu'] = str(use_gpus)
        kservice['spec']['template']['spec']['containers'][0]['image'] = "localhost:5000/microfn/sandbox" 

    if not management and use_gpus > 0. and runtime=="Python": # gpu using python function
        # overwrite values from values.yaml for new workflows
        kservice['spec']['template']['spec']['containers'][0]['resources']['limits']['nvidia.com/gpu'] = str(use_gpus)
        kservice['spec']['template']['spec']['containers'][0]['resources']['requests']['nvidia.com/gpu'] = str(use_gpus)
        kservice['spec']['template']['spec']['containers'][0]['image'] = "localhost:5000/microfn/sandbox_gpu" 
     
    # Special handling for the management container: never run on gpu
    if management:
        kservice['spec']['template']['spec']['volumes'] = [{ 'name': 'new-workflow-conf', 'configMap': {'name': new_workflow_conf['configmap']}}]
        kservice['spec']['template']['spec']['containers'][0]['volumeMounts'] = [{'name': 'new-workflow-conf', 'mountPath': '/opt/mfn/SandboxAgent/conf'}]
        kservice['spec']['template']['spec']['serviceAccountName'] = new_workflow_conf['mgmtserviceaccount']
        
        # management container should not consume a CPU and use standard sandbox image
        if (labels['workflowid'] == "Management"):
            kservice['spec']['template']['spec']['containers'][0]['resources']['limits']['nvidia.com/gpu'] = "0"
            kservice['spec']['template']['spec']['containers'][0]['resources']['requests']['nvidia.com/gpu'] = "0"
            kservice['spec']['template']['spec']['containers'][0]['image'] = "localhost:5000/microfn/sandbox"  

        if 'HTTP_GATEWAYPORT' in new_workflow_conf:
            env.append({'name': 'HTTP_GATEWAYPORT', 'value': new_workflow_conf['HTTP_GATEWAYPORT']})
        if 'HTTPS_GATEWAYPORT' in new_workflow_conf:
            env.append({'name': 'HTTPS_GATEWAYPORT', 'value': new_workflow_conf['HTTPS_GATEWAYPORT']})

    for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if not k in os.environ:
            continue
        for container in kservice['spec']['template']['spec']['containers']:
            container['env'].append({'name': k, 'value': os.getenv(k)})
    print('Checking if kservice exists')
    resp = requests.get(
        "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services/"+ksvcname,
        headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
        verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
        proxies={"https":""})
    if resp.status_code == 200:
        print('Deleting existing kservice')
        resp = requests.delete(
            "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services/"+ksvcname,
            headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
            verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
            proxies={"https":""})
        try:
            resp.raise_for_status()
        except Exception as e:
            print("ERROR deleting existing kservice")
            print(resp.text)

    # no change for Java function
    print('Creating new kservice')
    resp = requests.post(
        "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services",
        headers={"Authorization": "Bearer "+token, "Content-Type": "application/yaml", "Accept": "application/json"},
        verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
        data=json.dumps(kservice),
        proxies={"https":""})
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(json.dumps(kservice))
        print(resp.text)
        raise Exception("Error creating kubernetes deployment for "+email+" "+workflow_info["workflowId"], e)

    # Wait for the URL
    url = None
    retry = 60
    while retry > 0:
        try:
            resp = requests.get(
                "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1/namespaces/"+namespace+"/services/"+ksvcname,
                headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
                verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
                proxies={"https":""})
            resp.raise_for_status()
            status = resp.json().get("status",{})
            if "url" in status:
                url = status["url"]
                if "HTTPS_GATEWAYPORT" in os.environ:
                    url = "https://" + url.split("://",1)[1] + ":" + os.environ["HTTPS_GATEWAYPORT"]
                elif "HTTP_GATEWAYPORT" in os.environ:
                    url = "http://" + url.split("://",1)[1] + ":" + os.environ["HTTP_GATEWAYPORT"]
                break
        except requests.exceptions.HTTPError as e:
            print(e)
            print(resp.text)
        time.sleep(2)
        retry -= 1
    print("Workflow endpoint URL: "+str(url))
    return url, endpoint_key

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    try:
        if "email" not in data or "workflow" not in data:
            raise Exception("malformed input")
        email = data["email"]
        # iea: I think it's okay to have the storage_userid inside the incoming value
        # it is NOT coming from the client (e.g., browser) but actually derived
        # in ManagementServiceEntry.py when the user has authenticated and put into the value
        # that is passed to the next functions.
        storage_userid = data["storage_userid"]
        workflow = data["workflow"]
        if "id" not in workflow:
            raise Exception("malformed input")
        sapi.log(json.dumps(workflow))
        wfmeta = sapi.get(email + "_workflow_" + workflow["id"], True)
        print("WFMETA in deployWorkflow: "+ str(wfmeta))
        
        if wfmeta is None or wfmeta == "":
            raise Exception("workflow metadata is not valid.")
        try:
            wfmeta = json.loads(wfmeta)
        except:
            raise Exception("workflow metadata is invalid json ("+wfmeta+")")
        #if wfmeta["status"] != "undeployed" and wfmeta["status"] != "failed":
        #    raise Exception("workflow status is not undeployed: " + str(wfmeta["status"]))

        dlc = sapi.get_privileged_data_layer_client(storage_userid)

        # check workflow description and make sure that the functions are available
        # compile the requirements for the workflow
        #wfjson = sapi.get(email + "_workflow_json_" + wfmeta["id"], True)
        wfjson = dlc.get("workflow_json_" + wfmeta["id"])
        if wfjson is None or wfjson == "":
            raise Exception("workflow JSON does not exist.")

        wfjson = base64.b64decode(wfjson).decode()
        try:
            wfobj = json.loads(wfjson)
        except:
            raise Exception("workflow JSON is not valid.")

        wf_type = WF_TYPE_SAND
        if is_asl_workflow(wfobj):
            wf_type = WF_TYPE_ASL

        #use_gpus = int(wfmeta._gpu_usage)

        success, errmsg, resource_names, uploaded_resources = check_workflow_functions(wf_type, wfobj, email, sapi)
        if not success:
            raise Exception("Couldn't deploy workflow; " + errmsg)

        # compile the single key workflow deployment info
        # given such a key, the sandbox agent can retrieve the following information
        # it is stored in the user's storage,
        # just like all workflow and resource information
        # it includes:
        # - workflow info (ref, id)
        # - map of resources
        # - resource info for each (id, name, ref, type, runtime)
        resource_info_map = compile_resource_info_map(resource_names, uploaded_resources, email, sapi, dlc)

        workflow_info = {}
        workflow_info["sandboxId"] = workflow["id"]
        workflow_info["workflowId"] = workflow["id"]
        workflow_info["workflowType"] = wf_type
        workflow_info["json_ref"] = "workflow_json_" + wfmeta["id"]
        workflow_info["workflowName"] = wfmeta["name"]
        workflow_info["usertoken"] = data["usertoken"]
        req = {}
        req["installer"] = "pip"
        workflow_info["sandbox_requirements"] = req

        deployment_info = {}
        deployment_info["workflow"] = workflow_info
        deployment_info["resources"] = resource_info_map

        #dlc.put("deployment_info_workflow_" + workflow["id"], json.dumps(deployment_info))
        # _XXX_: important!
        # put must not be queued as the function currently waits for the container to become ready

        if "gpu_usage" in wfmeta and wfmeta["gpu_usage"] != "None":
            gpu_usage = float(wfmeta["gpu_usage"])
        else:
            gpu_usage = 0.

        print("deduced gpu_usage: " + str(gpu_usage))

        sapi.put("deployment_info_workflow_" + workflow["id"], json.dumps(deployment_info), True, False)

        status = "deploying"

        sapi.clearMap(workflow_info["workflowId"] + "_sandbox_status_map", is_private=True)

        if 'KUBERNETES_SERVICE_HOST' in os.environ:
            if any(resource_info_map[res_name]["runtime"] == "Java" for res_name in resource_info_map):
                runtime = "Java"
            else:
                runtime = "Python"

            url, endpoint_key = create_k8s_deployment(email, workflow_info, runtime, gpu_usage)
            if url is not None and len(url) > 0:
                status = "deploying"
                sapi.addSetEntry(workflow_info["workflowId"] + "_workflow_endpoints", str(url), is_private=True)
                sapi.putMapEntry(workflow_info["workflowId"] + "_workflow_endpoint_map", endpoint_key, str(url), is_private=True)
                urlset = set(wfmeta.get("endpoints",[]))
                urlset.add(url)
                wfmeta["endpoints"] = list(urlset)
            else:
                status = "failed"
        else:
            # We're running BARE METAL mode
            # _XXX_: due to the queue service still being in java in the sandbox

            if gpu_usage == 0:
                sandbox_image_name = "microfn/sandbox" # default value
            elif gpu_usage > 0:
                sandbox_image_name = "microfn/sandbox_gpu" # sandbox uses GPU
            if any(resource_info_map[res_name]["runtime"] == "Java" for res_name in resource_info_map):
                sandbox_image_name = "microfn/sandbox_java"

            # TODO: intelligence on how to pick hosts
            hosts = sapi.get("available_hosts", True)
            print("available_hosts: " + str(hosts))
            if hosts is not None and hosts != "":
                hosts = json.loads(hosts)
                deployed_hosts = {}
                gpu_hosts = {}
                picked_hosts = {}

                for hostname in hosts:
                    #if hostname.endswith("_gpu"):
                    if "has_gpu" in hosts[hostname]:
                        hostip = hosts[hostname]
                        gpu_hosts[hostname] = hostip

                # instruct hosts to start the sandbox and deploy workflow
                if sandbox_image_name == "microfn/sandbox" or sandbox_image_name=="microfn/sandbox_java": # can use any host 
                    picked_hosts = hosts
                elif len(gpu_hosts) > 0:
                    picked_hosts = gpu_hosts 
                else:
                    picked_hosts = hosts # fallback as there are no gpu hosts available
                    print("available GPU hosts is empty. Deploying on general purpose host")

                for hostname in picked_hosts: # loop over all hosts, need to pich gpu hosts for python/gpu workflows
                    hostip = hosts[hostname]
                    host_to_deploy = (hostname, hostip)
                    success, endpoint_key = start_docker_sandbox(host_to_deploy, email, workflow_info["sandboxId"], workflow_info["workflowId"], workflow_info["workflowName"], sandbox_image_name)
                    if success:
                        deployed_hosts[hostname] = hostip
                        success, host_port = get_workflow_host_port(host_to_deploy, workflow_info["sandboxId"])

                    if success:
                        #sapi.log(str(hostip) + ", host_port: " + str(host_port))
                        url="http://"+str(hostip)+":"+str(host_port)
                        sapi.addSetEntry(workflow_info["workflowId"] + "_workflow_endpoints", url, is_private=True)
                        sapi.putMapEntry(workflow_info["workflowId"] + "_workflow_endpoint_map", endpoint_key, str(url), is_private=True)
                        urlset = set(wfmeta.get("endpoints",[]))
                        urlset.add(url)
                        wfmeta["endpoints"] = list(urlset)

                        status = "deploying"
                        sbinfo = {}
                        sbinfo["status"] = "deploying"
                        sbinfo["errmsg"] = ""
                        sapi.putMapEntry(workflow_info["workflowId"] + "_sandbox_status_map", endpoint_key, json.dumps(sbinfo), is_private=True)
                        #endpoints = sapi.retrieveMap(workflow_info["workflowId"] + "_workflow_endpoints", True)
                        #sapi.log(str(endpoints))

                if not bool(deployed_hosts):
                    status = "failed"
                else:
                    #sapi.log("deployed on hosts: " + json.dumps(deployed_hosts))
                    sapi.put(email + "_workflow_hosts_" + workflow["id"], json.dumps(deployed_hosts), True, True)
            else:
                print("available_hosts is empty. Not deploying")
                status = "failed"

        # Update workflow status
        wfmeta["status"] = status

        # somebody needs to update the workflow deployment status after
        # successfully starting a sandbox
        # in BARE_METAL and KUBERNETES mode
        # put the workflow's status to the user storage
        # so that the sandbox agent running on any host can update it
        #dlc.put("workflow_status_" + workflow["id"], wfmeta["status"])
        sapi.put("workflow_status_" + workflow["id"], wfmeta["status"], True, True)

        print("Current workflow metadata: " + str(wfmeta))
        if status is not "failed" and "associatedTriggerableTables" in wfmeta:
            for table in wfmeta["associatedTriggerableTables"]:
                addWorkflowToTableMetadata(email, table, wfmeta["name"], wfmeta["endpoints"], dlc)

        sapi.put(email + "_workflow_" + workflow["id"], json.dumps(wfmeta), True)
        dlc.shutdown()

        # deploy queued up triggers
        if status is not "failed" and "associatedTriggers" in wfmeta:
            associatedTriggers = wfmeta["associatedTriggers"].copy()
            for trigger_name in associatedTriggers:
                trigger_id = storage_userid + "_" + trigger_name
                print("Adding trigger_id: " + str(trigger_id) + "  to workflow")
                if isTriggerPresent(email, trigger_id, trigger_name, sapi) == True:
                    trigger_info = get_trigger_info(sapi, trigger_id)
                    if wfmeta["name"] in trigger_info["associated_workflows"]:
                        print("[deployWorkflow] Strangely global trigger info already has workflow_name: " + str(wfmeta["name"]) + ", in associated_workflows")
                    workflow_state = associatedTriggers[trigger_name]
                    addWorkflowToTrigger(email, wfmeta["name"], workflow_state, wfmeta, trigger_id, trigger_name, sapi)
                else:
                    # workflow has an associated trigger name, but the trigger may have been deleted
                    # so remove the associated trigger name
                    print("Trigger_id: " + str(trigger_id) + "  info not found. Removing trigger name: " + str(trigger_name) + ", from workflow's associatedTriggers")
                    assocTriggers = wfmeta['associatedTriggers']
                    del assocTriggers[trigger_name]
                    wfmeta['associatedTriggers'] = assocTriggers
                    print("Updating workflow meta to: " + str(wfmeta))
                    sapi.put(email + "_workflow_" + wfmeta["id"], json.dumps(wfmeta), True)
                    #deleteTriggerFromWorkflowMetadata(email, trigger_name, wfmeta["name"],  workflow["id"], sapi)


    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't deploy workflow; " + str(e)
        response["data"] = response_data
        sapi.log(traceback.format_exc())
        return response

    # Finish successfully
    response = {}
    response_data = {}
    response_data["message"] = "Successfully deployed workflow " + workflow["id"] + "."
    response_data["workflow"] = workflow
    response["status"] = "success"
    response["data"] = response_data
    sapi.log(json.dumps(response))
    return response

def addWorkflowToTableMetadata(email, tablename, workflowname, workflow_endpoints, dlc):
    metadata_key = tablename
    metadata_urls = workflow_endpoints
    triggers_metadata_table = 'triggersInfoTable'
    bucket_metadata = {"urltype": "url", "urls": metadata_urls, "wfname": workflowname}
    print("[addWorkflowToTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Adding metadata: " + str(bucket_metadata))

    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    if current_meta == None or current_meta == '':
        meta_list = []
    else:
        meta_list = json.loads(current_meta)

    if type(meta_list == type([])):
        for i in range(len(meta_list)):
            meta=meta_list[i]
            if meta["wfname"] == bucket_metadata["wfname"]:
                del meta_list[i]
                break
        meta_list.append(bucket_metadata)

    dlc.put(metadata_key, json.dumps(meta_list), tableName=triggers_metadata_table)

    time.sleep(0.2)
    updated_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    updated_meta_list = json.loads(updated_meta)
    print("[addWorkflowToTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Updated metadata: " + str(updated_meta_list))


MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

### Utility functions ###
def get_available_frontends(context):
    tf_hosts = context.getMapKeys(MAP_AVAILABLE_FRONTENDS, True)
    return tf_hosts

def get_frontend_info(context, frontend_ip_port):
    ret = context.getMapEntry(MAP_AVAILABLE_FRONTENDS, frontend_ip_port, True)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def get_trigger_info(context, trigger_id):
    ret = context.getMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)
    if ret is "" or ret is None:
        return None
    else:
        return json.loads(ret)

def add_trigger_info(context, trigger_id, data):
    print("add_trigger_info: " + trigger_id + ", data: " + data)
    context.putMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, data, True)

def remove_trigger_info(context, trigger_id):
    print("remove_trigger_info: " + trigger_id)
    context.deleteMapEntry(MAP_TRIGGERS_TO_INFO, trigger_id, True)

def get_user_trigger_list(context, email):
    user_triggers_list = context.get(email + "_list_triggers", True)
    if user_triggers_list is not None and user_triggers_list != "":
        user_triggers_list = json.loads(user_triggers_list)
    else:
        user_triggers_list = {}
    return user_triggers_list

def isTriggerPresent(email, trigger_id, trigger_name, context):
    # check if the global trigger is present
    global_trigger_info = get_trigger_info(context, trigger_id)
    print("[isTriggerPresent] global_trigger_info = " + str(global_trigger_info))

    # check if the trigger does not exist in global and user's list
    if global_trigger_info is None:
        return False

    return True


def addWorkflowToTrigger(email, workflow_name, workflow_state, workflow_details, trigger_id, trigger_name, context):
    print("[addTriggerForWorkflow] called with workflow_name: " + str(workflow_name) + ", workflow_state: " + str(workflow_name) + ", workflow_details: " + str(workflow_details) + ", trigger_id: " + str(trigger_id) + ", trigger_name: " + trigger_name)
    status_msg = ""
    try:
        workflow_endpoints = workflow_details["endpoints"]
        if len(workflow_endpoints) == 0:
            raise Exception("[addTriggerForWorkflow] No workflow endpoint available")
        # TODO: [For bare metal clusters] send all workflow endpoints to frontend to let is load balance between wf endpoints. For k8s there will only be one name
        selected_workflow_endpoint = workflow_endpoints[random.randint(0,len(workflow_endpoints)-1)]
        print("[addTriggerForWorkflow] selected workflow endpoint: " + selected_workflow_endpoint)

        workflow_to_add = \
        {
            "workflow_url": selected_workflow_endpoint,
            "workflow_name": workflow_name,
            "workflow_state": workflow_state
        }

        # get the list of available frontends.
        tf_hosts = get_available_frontends(context)
        if len(tf_hosts) == 0:
            raise Exception("[addTriggerForWorkflow] No available TriggersFrontend found")

        # if the frontend with the trigger is available
        global_trigger_info = get_trigger_info(context, trigger_id)
        tf_ip_port = global_trigger_info["frontend_ip_port"]
        if tf_ip_port not in tf_hosts:
            raise Exception("Frontend: " + tf_ip_port + " not available")
        
        url = "http://" + tf_ip_port + "/add_workflows"
        # send the request and wait for response

        req_obj = {"trigger_id": trigger_id, "workflows": [workflow_to_add]}
        print("[addTriggerForWorkflow] Contacting: " + url + ", with data: " + str(req_obj))
        res_obj = {}
        try:
            res = requests.post(url, json=req_obj)
            if res.status_code != 200:
                raise Exception("status code: " + str(res.status_code) + " returned")
            res_obj = res.json()
        except Exception as e:
            status_msg = "Error: trigger_id" + trigger_id + "," + str(e)
        
        if "status" in res_obj and res_obj["status"].lower() == "success":
            # if success then update the global trigger table to add a new workflow.
            print("[addTriggerForWorkflow] Success response from " + url)
            global_trigger_info["associated_workflows"][workflow_name] = workflow_to_add
            add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))

            status_msg = "[addTriggerForWorkflow] Trigger " + trigger_name + " added successfully to workflow:" + workflow_name + ". Message: " + res_obj["message"]
        else:
            if "message" in res_obj:
                status_msg = status_msg + ", message: " + res_obj["message"]
            status_msg = "[addTriggerForWorkflow] Error: " + status_msg + ", response: " + str(res_obj)
            raise Exception(status_msg)
    except Exception as e:
        print("[addTriggerForWorkflow] exception: " + str(e))
        if 'associatedTriggers' in workflow_details and trigger_name in workflow_details['associatedTriggers']:            
            associatedTriggers = workflow_details['associatedTriggers']
            del associatedTriggers[trigger_name]
            workflow_details['associatedTriggers'] = associatedTriggers
            print("Removing trigger_name: " + str(trigger_name) + ", from associatedTriggers for the workflow. Updated workflow metadata: " + str(workflow_details))
            context.put(email + "_workflow_" + workflow_details["id"], json.dumps(workflow_details), True)

