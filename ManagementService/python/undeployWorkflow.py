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
import traceback

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

        # remove workflow from associatedTriggers from the frontend
        if "associatedTriggers" in wf:
            for trigger_name in wf["associatedTriggers"]:
                trigger_id = storage_userid + "_" + trigger_name
                if isTriggerPresent(email, trigger_id, trigger_name, sapi) == True:
                    try:
                        removeTriggerFromWorkflow(trigger_name, trigger_id, wf["name"], sapi)
                        # at this point, the trigger_name is still associated with the workflow
                        # frontend does not know about the trigger
                        # workflow name has also been removed from global trigger table

                    except Exception as e:
                        print("Removing associated triggers error: " + str(e))
                        pass


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

            # Pod, Deployment and Hpa names for the new workflow will have a prefix containing the workflow name and user name
            app_fullname_prefix = ''
            if 'app.fullname.prefix' in new_workflow_conf:
                app_fullname_prefix = new_workflow_conf['app.fullname.prefix']

            with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
                token = f.read()
            with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
                namespace = f.read()

            ksvcname = app_fullname_prefix + '-' + wf["id"].lower()
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
        sapi.log(traceback.format_exc())
        return response


    # Finish successfully
    response_data["message"] = "Successfully undeployed workflow " + workflow["id"] + "."
    response["status"] = "success"
    response["data"] = response_data
    sapi.log(json.dumps(response))
    return response

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
    # check the user's storage area for the trigger name
    user_triggers_list = get_user_trigger_list(context, email)

    # check if the trigger does not exist in global and user's list
    if global_trigger_info is None and trigger_name not in user_triggers_list:
        return False

    # check if the trigger is missing in one of the lists
    elif global_trigger_info is None or trigger_name not in user_triggers_list:
        print("[addTriggerForWorkflow] User: " + email +
                "Mismatch between global and user's trigger list for Trigger: " + trigger_name)
        raise Exception("Mismatch between global and user's trigger list for Trigger: " + trigger_name)
    
    # trigger is present in both global and user's list
    assert(global_trigger_info is not None)
    assert(trigger_name in user_triggers_list)
    return True

def removeTriggerFromWorkflow(trigger_name, trigger_id, workflow_name, context):
    status_msg = ""
    global_trigger_info = get_trigger_info(context, trigger_id)
    workflow_to_remove = global_trigger_info["associated_workflows"][workflow_name]

    # get the list of available frontends.
    tf_hosts = get_available_frontends(context)
    if len(tf_hosts) == 0:
        raise Exception("No available TriggersFrontend found")

    # if the frontend with the trigger is available
    tf_ip_port = global_trigger_info["frontend_ip_port"]
    if tf_ip_port not in tf_hosts:
        raise Exception("Frontend: " + tf_ip_port + " not available")
    
    url = "http://" + tf_ip_port + "/remove_workflows"
    # send the request and wait for response

    req_obj = {"trigger_id": trigger_id, "workflows": [workflow_to_remove]}
    print("Contacting: " + url + ", with data: " + str(req_obj))
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
        print("Success response from " + url)
        if workflow_name in global_trigger_info["associated_workflows"]:
            del global_trigger_info["associated_workflows"][workflow_name]
        add_trigger_info(context, trigger_id, json.dumps(global_trigger_info))
        status_msg = "Trigger " + trigger_name + " removed successfully from workflow:" + workflow_name + ". Message: " + res_obj["message"]
    else:
        if "message" in res_obj:
            status_msg = status_msg + ", message: " + res_obj["message"]
        status_msg = "Error: " + status_msg + ", response: " + str(res_obj)
        raise Exception(status_msg)
