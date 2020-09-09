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
import time

#from random import randint

import docker

def stop_docker_sandbox(host_to_undeploy, sid):
    success = False
    hostname = host_to_undeploy[0]
    hostip = host_to_undeploy[1]
    try:
        client = docker.DockerClient(base_url="tcp://" + hostip + ":2375")
        success = True
    except Exception as exc:
        print("Error stopping sandbox: can't connect to: " + hostip + " " + str(exc))
        success = False

    if success:
        try:
            sandbox = client.containers.get(sid)
            print("Executing python3 /opt/mfn/SandboxAgent/shutdown.py command inside the sandbox: "+ hostname + " " + sid)
            retcode, output = sandbox.exec_run('python3 /opt/mfn/SandboxAgent/shutdown.py')
            if retcode > 0:
                print("Error executing a command inside the sandbox: " + hostname + " " + sid + " " + "Error code: " + str(retcode) + " Error output: " + str(output))
                sandbox.stop()
                #sandbox.remove(force=True)
        except Exception as exc:
            print("Error stopping sandbox: " + hostname + " " + sid)
            success = False
        finally:
            client.close()

    return success

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    try:
        if "workflow" not in data or "email" not in data:
            raise Exception("Couldn't undeploy workflow; malformed input.")

        email = data["email"]
        storage_userid = data["storage_userid"]
        workflow = data["workflow"]
        sapi.log(json.dumps(workflow))

        if "id" not in workflow:
            raise Exception("Couldn't undeploy workflow; malformed input.")

        wf = sapi.get(email + "_workflow_" + workflow["id"], True)

        if wf is None or wf == "":
            raise Exception("Couldn't undeploy workflow; workflow metadata is not valid.")
        try:
            wf = json.loads(wf)
        except:
            raise Exception("Couldn't undeploy workflow; workflow metadata seems not to be valid json ("+wf+")")

        print("Current workflow metadata: " + str(wf))
        if "associatedTriggerableTables" in wf:
            dlc = sapi.get_privileged_data_layer_client(storage_userid)
            tablenames = wf["associatedTriggerableTables"]
            print("Current set of tables associated: " + str(tablenames))
            for table in tablenames:
                removeWorkflowFromTableMetadata(email, table, wf["name"], dlc)
            dlc.shutdown()

        if 'KUBERNETES_PORT' not in os.environ:
            # BARE METAL

            # instruct hosts to stop the workflow
            deployed_hosts = sapi.get(email + "_workflow_hosts_" + workflow["id"], True)
            if deployed_hosts is not None and deployed_hosts != "":
                deployed_hosts = json.loads(deployed_hosts)
                for hostname in deployed_hosts:
                    hostip = deployed_hosts[hostname]
                    host_to_undeploy = (hostname, hostip)
                    success = stop_docker_sandbox(host_to_undeploy, workflow["id"])
                    if not success:
                        print("ERROR in stopping sandbox.")

                sapi.clearSet(workflow["id"] + "_workflow_endpoints", is_private=True)
                sapi.deleteMap(workflow["id"] + "_workflow_endpoint_map", is_private=True)
                sapi.deleteMap(workflow["id"] + "_sandbox_status_map", is_private=True)

            #sapi.delete(email + "_workflow_hosts_" + workflow["id"], True, True)
            wf["endpoints"] = []
        else:
            conf_file = '/opt/mfn/SandboxAgent/conf/new_workflow.conf'
            if not os.path.exists(conf_file):
                raise Exception("Unable to load /opt/mfn/SandboxAgent/conf/new_workflow.conf. Ensure that the configmap has been setup properly")

            new_workflow_conf = {}
            with open(conf_file, 'r') as fp:
                new_workflow_conf = json.load(fp)

            # Kubernetes labels cannot contain @ or _ and should start and end with alphanumeric characters
            wfNameSanitized = 'wf-' + wf["name"].replace('@', '-').replace('_', '-') + '-wf'
            emailSanitized = 'u-' + email.replace('@', '-').replace('_', '-') + '-u'

            # Pod, Deployment and Hpa names for the new workflow will have a prefix containing the workflow name and user name
            app_fullname_prefix = ''
            if 'app.fullname.prefix' in new_workflow_conf:
                app_fullname_prefix = new_workflow_conf['app.fullname.prefix']+'-'# + wfNameSanitized + '-' + emailSanitized + '-'

            with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
                token = f.read()
            with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
                namespace = f.read()

            ksvcname = app_fullname_prefix + wf["id"].lower()
            # DELETE KNative Service
            resp = requests.delete(
                "https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apis/serving.knative.dev/v1alpha1/namespaces/"+namespace+"/services/"+ksvcname,
                #"https://kubernetes.default:"+os.getenv("KUBERNETES_SERVICE_PORT_HTTPS")+"/apps/v1/namespaces/"+namespace+"/deployments/"+wf["id"],
                headers={"Authorization": "Bearer "+token},
                json={"propagationPolicy": "Background"},
                verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
                proxies={"https":""})
            try:
                resp.raise_for_status()
            except Exception as e:
                print("ERROR in stopping sandbox, url not found")
                print(resp.text)

            sapi.clearSet(workflow["id"] + "_workflow_endpoints", is_private=True)
            sapi.deleteMap(workflow["id"] + "_workflow_endpoint_map", is_private=True)
            sapi.deleteMap(workflow["id"] + "_sandbox_status_map", is_private=True)
            wf["endpoints"] = []
            sapi.log(str(resp.status_code)+" "+str(resp.text))


        # Eventually remove the host list that the workflow is deployed to
        sapi.delete(email + "_workflow_hosts_" + workflow["id"], True, True)

        wf["status"] = "undeployed"
        # Undeployed status will be set by the sandbox agent, since the deployed status is being set by the sandboxagent
        # No. we can't do that, because there may be other sandboxes running the same application.
        # For example, if there are 3 sandboxes and one shuts down, the other two other still deployed.
        # If the sandbox agent were to set the status to 'undeployed', it would be wrong.
        # Here, we are undeploying all sandboxes, so we can set here the status to undeployed.
        #dlc = sapi.get_privileged_data_layer_client(storage_userid)
        #dlc.put("workflow_status_" + workflow["id"], wf["status"])
        #dlc.shutdown()
        sapi.put("workflow_status_" + workflow["id"], "undeployed", True, True)

        sapi.put(email + "_workflow_" + workflow["id"], json.dumps(wf), True, True)

    except Exception as exc:
        response["status"] = "failure"
        response_data["message"] = "Couldn't undeploy workflow; "+ str(exc)
        response["data"] = response_data
        sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value": response})
        return {}


    # Finish successfully
    response_data["message"] = "Successfully undeployed workflow " + workflow["id"] + "."
    response["status"] = "success"
    response["data"] = response_data
    sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value": response})
    sapi.log(json.dumps(response))
    return {}

def removeWorkflowFromTableMetadata(email, tablename, workflowname, dlc):
    metadata_key = tablename
    triggers_metadata_table = 'triggersInfoTable'
    print("[removeWorkflowFromTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename)

    current_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    if current_meta == None or current_meta == '':
        meta_list = []
    else:
        meta_list = json.loads(current_meta)

    if type(meta_list == type([])):
        for i in range(len(meta_list)):
            meta=meta_list[i]
            if meta["wfname"] == workflowname:
                del meta_list[i]
                break

    dlc.put(metadata_key, json.dumps(meta_list), tableName=triggers_metadata_table)
    
    time.sleep(0.2)
    updated_meta = dlc.get(metadata_key, tableName=triggers_metadata_table)
    updated_meta_list = json.loads(updated_meta)
    print("[removeWorkflowFromTableMetadata] User: " + email + ", Workflow: " + workflowname + ", Table: " + tablename + ", Updated metadata: " + str(updated_meta_list))
