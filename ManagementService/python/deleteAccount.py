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

def delete_single_workflow(email, wid, sapi):
    # delete
    # 1. endpoint map/set
    sapi.deleteSet(wid + "_workflow_endpoints", True, True)
    sapi.deleteMap(wid + "_workflow_endpoint_map", True, True)

    # 2. sandbox status map
    sapi.deleteMap(wid + "_sandbox_status_map", True, True)

    sapi.delete("workflow_status_" + wid, True, True)

    # 3. deployed hosts
    sapi.delete(email + "_workflow_hosts_" + wid, True, True)

    # 4. deployment info
    sapi.delete("deployment_info_workflow_" + wid, True, True)

    # 5. workflow json
    sapi.delete(email + "_workflow_json_" + wid, True, True)

    # 6. workflow metadata
    sapi.delete(email + "_workflow_" + wid, True, True)

    # global data layer entries for each workflow
    # the following use the same keyspace: "sbox_" + sandboxid (or workflowid)
    # 1. workflow private keyspace
    # 2. mfn metadata store keyspace
    # just drop the keyspace
    dlc = sapi.get_privileged_data_layer_client(sid=wid, drop_keyspace=True)
    dlc.shutdown()

    # TODO: local data layer entries for each workflow
    # (i.e., at each host/node where this workflow had been deployed)
    # _XXX_: alternatively, when the sandbox agent shuts down, it can delete the local storage
    # if so, then what about deploy/undeploy sequences for scaling up / down?
    # need to think about it.
    # one strategy would be do the deletion delayed, so that in case there is a new allocation for scaling up
    # soon after the de-allocation the local storage will still be valid

    # _XXX_: alternatively, record which workflows have been deleted,
    # and periodically clean the local data layer storage by removing their keyspace

def delete_workflows(email, sapi):
    # get list of workflows
    workflows = sapi.get(email + "_list_workflows", True)

    if workflows is not None and workflows != "":
        workflows = json.loads(workflows)
        for i in workflows:
            wid = workflows[i]

            wf_status = sapi.get("workflow_status_" + wid, True)
            if wf_status is not None and wf_status != "" and wf_status == "undeployed":
                delete_single_workflow(email, wid, sapi)

    sapi.delete(email + "_list_workflows", True)

'''
_XXX_: calling this function is unneeded because each user's functions are stored in her storage
when the keyspace is dropped, they will be deleted

def delete_single_function(email, dlc, fid, sapi):
    # delete
    # 1. function zip
    num_chunks_str = dlc.get("grain_source_zip_num_chunks_" + fid)

    try:
        num_chunks = int(num_chunks_str)
        for i in range(num_chunks):
            dlc.delete("grain_source_zip_" + fid + "_chunk_" + str(i))
        dlc.delete("grain_source_zip_num_chunks_" + fid)
    except Exception as exc:
        # no zip info, so not a zip
        pass

    # 2. function zip metadata
    dlc.delete("grain_source_zip_metadata_" + fid)

    # 3. function code
    dlc.delete("grain_source_" + fid)

    # 4. function requirements
    dlc.delete("grain_requirements_" + fid)

    # 5. function environment variables
    dlc.delete("grain_environment_variables_" + fid)
'''

def delete_functions(email, sapi):
    # get list of functions
    functions = sapi.get(email + "_list_grains", True)

    if functions is not None and functions != "":
        functions = json.loads(functions)
        for i in functions:
            fid = functions[i]
            # _XXX_: each function's actual data is stored in the user storage
            # it will be deleted when the user keyspace is dropped (in delete_user())
            # 1. function metadata
            sapi.delete(email + "_grain_" + fid, True, True)

    sapi.delete(email + "_list_grains", True, True)

def delete_user(email, storage_userid, sapi):
    # global data layer entries for user storage
    # 1. user keyspace
    # delete user data,
    # including functions and their data
    # including triggerable tables and storage triggers for workflows
    dlc = sapi.get_privileged_data_layer_client(storage_userid, drop_keyspace=True)
    dlc.shutdown()

    # delete also the metadata about triggerable tables
    sapi.delete(email + "_list_trigger_tables", True, True)

    # TODO: local data layer entries for user storage for each host

    # delete user login
    sapi.delete(email, True, True)

def handle(value, sapi):
    data = value

    response = {}
    response_data = {}

    sapi.log(data)

    try:

        if "password" not in data["user"]:
            raise Exception("Password parameter missing.")

        email = data["email"]
        password = data["user"]["password"]
        cur_user = sapi.get(email, True)

        if cur_user is not None and cur_user != "":
            cur_user = json.loads(cur_user)
            if cur_user["passwordHash"] != hashlib.sha256(password.encode()).hexdigest():
                raise Exception("Invalid password.")
        else: raise Exception("Invalid email.")

        success = False
        
        storage_userid = data["storage_userid"]

        delete_workflows(email, sapi)

        delete_functions(email, sapi)

        delete_user(email, storage_userid, sapi)

        # finally, delete the authenticated tokens that belong to all sessions of this user
        session_tokens = sapi.retrieveSet(email + "_session_tokens", is_private=True)
        for token in session_tokens:
            sapi.delete(token, True, True)

        sapi.delete(data["usertoken"], True, True)

        sapi.deleteSet(email + "_session_tokens", is_private=True)

        success = True

        if success:
            response["status"] = "success"
        else:
            response["status"] = "failure"

        response["data"] = response_data

    except Exception as exc:
        response["status"] = "failure"
        response_data["message"] = str(exc)
        response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

