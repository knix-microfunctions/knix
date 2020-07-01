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

WF_TYPE_SAND = 0
WF_TYPE_ASL = 1

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
        if len(resource_names_to_be_checked.keys()) == 0:
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
            client.containers.run(sandbox_image_name, init=True, detach=True, ports={"8080/tcp": None}, ulimits=ulimit_list, auto_remove=True, name=sid, environment=env_vars, extra_hosts={host_to_deploy[0]:host_to_deploy[1]}, log_config=lc)
            # TEST/DEVELOPMENT: no auto_remove to access sandbox logs
            #client.containers.run(sandbox_image_name, init=True, detach=True, ports={"8080/tcp": None}, ulimits=ulimit_list, name=sid, environment=env_vars, extra_hosts={host_to_deploy[0]:host_to_deploy[1]}, log_config=lc)
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

def create_k8s_deployment(email, workflow_info, runtime, management=False):
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
    wfNameSanitized = 'wf-' + workflow_info["workflowId"].replace('@', '-').replace('_', '-').lower() + '-wf'
    wfActualNameSanitized = 'wf-' + workflow_info["workflowName"].replace('@', '-').replace('_', '-').lower() + '-wf'
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
    labels['workflow'] = wfActualNameSanitized
    labels['workflowid'] = workflow_info["workflowId"]
    kservice['spec']['template']['spec']['containers'][0]['image'] = new_workflow_conf['image.'+runtime]
    env = kservice['spec']['template']['spec']['containers'][0]['env']
    env.append({'name': 'MFN_ENDPOINT_KEY', 'value': endpoint_key})
    env.append({'name': 'USERID', 'value': email})
    env.append({'name': 'SANDBOXID','value': workflow_info["sandboxId"]})
    env.append({'name': 'WORKFLOWID', 'value': workflow_info["workflowId"]})
    env.append({'name': 'WORKFLOWNAME', 'value': workflow_info["workflowName"]})

    # Special handling for the management container
    if management:
        kservice['spec']['template']['spec']['volumes'] = [{ 'name': 'new-workflow-conf', 'configMap': {'name': new_workflow_conf['configmap']}}]
        kservice['spec']['template']['spec']['containers'][0]['volumeMounts'] = [{'name': 'new-workflow-conf', 'mountPath': '/opt/mfn/SandboxAgent/conf'}]
        kservice['spec']['template']['spec']['serviceAccountName'] = new_workflow_conf['mgmtserviceaccount']
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
        sapi.put("deployment_info_workflow_" + workflow["id"], json.dumps(deployment_info), True, False)

        if 'KUBERNETES_SERVICE_HOST' in os.environ:
            if any(resource_info_map[res_name]["runtime"] == "Java" for res_name in resource_info_map):
                runtime = "Java"
            else:
                runtime = "Python"
            url, endpoint_key = create_k8s_deployment(email, workflow_info, runtime)
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
            sandbox_image_name = "microfn/sandbox"
            if any(resource_info_map[res_name]["runtime"] == "Java" for res_name in resource_info_map):
                sandbox_image_name = "microfn/sandbox_java"

            # TODO: intelligence on how to pick hosts
            hosts = sapi.get("available_hosts", True)
            print("available_hosts: " + str(hosts))
            if hosts is not None and hosts != "":
                hosts = json.loads(hosts)
                deployed_hosts = {}
                # instruct hosts to start the sandbox and deploy workflow
                for hostname in hosts:
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

                sapi.put(email + "_workflow_hosts_" + workflow["id"], json.dumps(deployed_hosts), True, True)
            else:
                print("available_hosts is empty. Not deploying")

        # Update workflow status
        wfmeta["status"] = status

        # somebody needs to update the workflow deployment status after
        # successfully starting a sandbox
        # in BARE_METAL and KUBERNETES mode
        # put the workflow's status to the user storage
        # so that the sandbox agent running on any host can update it
        #dlc.put("workflow_status_" + workflow["id"], wfmeta["status"])
        sapi.put("workflow_status_" + workflow["id"], wfmeta["status"], True, True)

        dlc.shutdown()

        sapi.put(email + "_workflow_" + workflow["id"], json.dumps(wfmeta), True, True)

    except Exception as e:
        response = {}
        response_data = {}
        response["status"] = "failure"
        response_data["message"] = "Couldn't deploy workflow; " + str(e)
        response["data"] = response_data
        sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value": response})
        sapi.log(traceback.format_exc())
        return {}

    # Finish successfully
    response = {}
    response_data = {}
    response_data["message"] = "Successfully deployed workflow " + workflow["id"] + "."
    response["status"] = "success"
    response["data"] = response_data
    sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value": response})
    sapi.log(json.dumps(response))
    return {}

