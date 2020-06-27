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

import hashlib
import json
import time

# This will be set automatically to the current git tag during the build process. Do not change the variable name.
_VERSION_STRING = ""

_TIMEOUT = 6000000000

def get_storage_userid(email):
    storage_userid = email.replace("@", "AT")
    storage_userid = storage_userid.replace(".", "_")
    storage_userid = storage_userid.replace("-", "_")
    return storage_userid

def actionSignUp(user, sapi):
    response = {}
    response_data = {}

    if "email" in user and "password" in user and "name" in user:
        cur_email = user["email"]

        old_email = sapi.get(cur_email, True)

        if old_email is None or old_email == "":
            new_user = {}
            new_user["name"] = user["name"]
            new_user["email"] = cur_email
            storage_userid = get_storage_userid(cur_email)
            new_user["storage_userid"] = storage_userid
            new_user["passwordHash"] = hashlib.sha256(user["password"].encode()).hexdigest()
            new_user["storageEndpoint"] = "/storage/" + hashlib.sha256((cur_email + "secretsanda").encode()).hexdigest()

            sapi.put(cur_email, json.dumps(new_user), True, True)

            # this call will initialize user storage
            #global_dlc = sapi.get_privileged_data_layer_client(storage_userid, init_tables=True)
            # also create the "Results" and "Backups" maps
            # createMap() does not have an effect, so disable the call
            #global_dlc.createMap("Results")
            #global_dlc.createMap("Backups")
            #global_dlc.shutdown()

            response["status"] = "success"
            response_data["message"] = "User created successfully."
            response["data"] = response_data

            output = {"next": "ManagementServiceExit", "value": response}
            sapi.add_dynamic_workflow(output)
            return None

    response["status"] = "failure"
    response_data["message"] = "User already exists."
    response["data"] = response_data

    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return None


def actionLogin(user, sapi):
    response = {}
    response_data = {}

    if "email" in user and "password" in user:
        email = user["email"]
        password = user["password"]

        cur_user = sapi.get(email, True)

        if cur_user is not None and cur_user != "":
            cur_user = json.loads(cur_user)
            if cur_user["passwordHash"] == hashlib.sha256(password.encode()).hexdigest():
                timestamp = time.time()
                token = hashlib.sha256((email + " " + password + " " + str(timestamp)).encode()).hexdigest()

                authenticated_user = {}
                authenticated_user["email"] = email
                authenticated_user["timestamp"] = timestamp
                authenticated_user["storage_userid"] = cur_user["storage_userid"]

                sapi.put(token, json.dumps(authenticated_user), True, True)

                sapi.addSetEntry(email + "_session_tokens", token, is_private=True)

                storage_userid = cur_user["storage_userid"]
                global_dlc = sapi.get_privileged_data_layer_client(storage_userid, init_tables=True)
                global_dlc.shutdown()

                response["status"] = "success"
                response_data["message"] = "Logged in successfully."
                response_data["name"] = cur_user["name"]
                response_data["email"] = cur_user["email"]
                response_data["token"] = token
                response_data["storageEndpoint"] = cur_user["storageEndpoint"]
                response["data"] = response_data

                output = {"next": "ManagementServiceExit", "value": response}
                sapi.add_dynamic_workflow(output)
                return None
            else:
                response_data["message"] = "Authentication failed; wrong username and/or password."
        else:
            response_data["message"] = "Authentication failed; wrong username and/or password."
    else:
        response_data["message"] = "Authentication failed; wrong username and/or password."

    response["status"] = "failure"
    response["data"] = response_data

    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return None

def actionChangeName(user, sapi):
    response = {}
    response_data = {}

    success = False

    if "email" in user and "password" in user and "new_name" in user:
        email = user["email"]
        password = user["password"]
        new_name = user["new_name"]

        if not any(not (ord(c) < 128) for c in new_name):
            cur_user = sapi.get(email, True)

            if cur_user is not None and cur_user != "":
                cur_user = json.loads(cur_user)
                if cur_user["passwordHash"] == hashlib.sha256(password.encode()).hexdigest():
                    cur_user["name"] = new_name

                    sapi.put(email, json.dumps(cur_user), True, True)

                    response["status"] = "success"
                    response_data["message"] = "Name changed successfully."
                    response_data["name"] = cur_user["name"]
                    response_data["email"] = cur_user["email"]
                    response_data["storageEndpoint"] = cur_user["storageEndpoint"]
                    response["data"] = response_data

                    output = {"next": "ManagementServiceExit", "value": response}
                    sapi.add_dynamic_workflow(output)
                    success = True
                else:
                    response_data["message"] = "Authentication failed; wrong username and/or password."
            else:
                response_data["message"] = "Name could not be changed; non-ascii characters in name."

    if not success:
        response["status"] = "failure"
        response["data"] = response_data

        output = {"next": "ManagementServiceExit", "value": response}
        sapi.add_dynamic_workflow(output)

def actionChangePassword(user, sapi):
    response = {}
    response_data = {}

    success = False

    if "email" in user and "password" in user and "new_password" in user:
        email = user["email"]
        password = user["password"]
        new_password = user["new_password"]

        cur_user = sapi.get(email, True)

        if cur_user is not None and cur_user != "":
            cur_user = json.loads(cur_user)
            if cur_user["passwordHash"] == hashlib.sha256(password.encode()).hexdigest():
                cur_user["passwordHash"] = hashlib.sha256(new_password.encode()).hexdigest()

                sapi.put(email, json.dumps(cur_user), True, True)

                timestamp = time.time()
                token = hashlib.sha256((email + " " + new_password + " " + str(timestamp)).encode()).hexdigest()

                authenticated_user = {}
                authenticated_user["email"] = email
                authenticated_user["timestamp"] = timestamp
                authenticated_user["storage_userid"] = cur_user["storage_userid"]

                sapi.put(token, json.dumps(authenticated_user), True, True)

                response["status"] = "success"
                response_data["message"] = "Password changed successfully."
                response_data["name"] = cur_user["name"]
                response_data["email"] = cur_user["email"]
                response_data["token"] = token
                response_data["storageEndpoint"] = cur_user["storageEndpoint"]
                response["data"] = response_data

                output = {"next": "ManagementServiceExit", "value": response}
                sapi.add_dynamic_workflow(output)
                success = True

    if not success:
        response_data["message"] = "Authentication failed; wrong username and/or password."

        response["status"] = "failure"
        response["data"] = response_data

        output = {"next": "ManagementServiceExit", "value": response}
        sapi.add_dynamic_workflow(output)

def actionResetPassword(user, sapi):
    # TODO: send email to user
    response = {}
    response_data = {}

    response["status"] = "failure"
    response_data["message"] = "Work in Progress -- Unsupported feature."
    response["data"] = response_data

    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return None

def verifyUser(user, sapi, extendTokenExpiry=True):
    status = False
    if "token" not in user:
        return status, "No token supplied", None, None

    token = user["token"]
    authenticated_user = sapi.get(token, True)
    if authenticated_user is None or authenticated_user == "":
        return status, "No user information found for supplied token", token, None
    authenticated_user = json.loads(authenticated_user)

    timestamp = authenticated_user["timestamp"]
    cur_time = time.time()
    if (cur_time - timestamp) >= _TIMEOUT:
        return status, "User token expired", token, authenticated_user

    status = True
    if extendTokenExpiry:
        authenticated_user["timestamp"] = cur_time
        sapi.put(token, json.dumps(authenticated_user), True, True)

    return status, "User verified successfully.", token, authenticated_user

def actionVerifyUser(user, sapi):
    response = {}
    response_data = {}
    status, statusmessage, token, authenticated_user = verifyUser(user, sapi, extendTokenExpiry=True)
    if status:
        response["status"] = "success"
        response_data["message"] = statusmessage
        response_data["email"] = authenticated_user["email"]
        response_data["token"] = token
        response_data["storageEndpoint"] = authenticated_user["storage_userid"]
        response["data"] = response_data

        output = {"next": "ManagementServiceExit", "value": response}
        sapi.add_dynamic_workflow(output)
        return {}
    else:
        response_data["message"] = "User verification failed: " + statusmessage
        sapi.log(response_data["message"])

    response["status"] = "failure"
    response["data"] = response_data
    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return None

def actionVersion(sapi):
    response = {}
    response_data = {}
    response["status"] = "success"
    response_data["message"] = _VERSION_STRING
    response["data"] = response_data

    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return {}

def actionOther(action, data, sapi):
    response = {}
    response_data = {}

    possibleActions = {}
    possibleActions["addFunction"] = True
    possibleActions["addWorkflow"] = True
    possibleActions["deleteFunction"] = True
    possibleActions["deleteWorkflow"] = True
    possibleActions["deployWorkflow"] = True
    possibleActions["getExecutionDescription"] = True
    possibleActions["getFunctionCode"] = True
    possibleActions["getFunctionEnvironmentVariables"] = True
    possibleActions["getFunctionRequirements"] = True
    possibleActions["getFunctions"] = True
    possibleActions["getFunctionZipMetadata"] = True
    possibleActions["getFunctionZip"] = True
    possibleActions["getWorkflowJSON"] = True
    possibleActions["getWorkflows"] = True
    possibleActions["modifyFunction"] = True
    possibleActions["modifyWorkflow"] = True
    possibleActions["executeWorkflow"] = True
    possibleActions["undeployWorkflow"] = True
    possibleActions["uploadFunctionCode"] = True
    possibleActions["uploadFunctionEnvironmentVariables"] = True
    possibleActions["uploadFunctionRequirements"] = True
    possibleActions["uploadFunctionZipMetadata"] = True
    possibleActions["uploadWorkflowJSON"] = True
    possibleActions["retrieveAllWorkflowLogs"] = True
    possibleActions["clearAllWorkflowLogs"] = True
    possibleActions["addTriggerableTable"] = True
    possibleActions["addStorageTriggerForWorkflow"] = True
    possibleActions["getTriggerableTables"] = True
    possibleActions["deleteAccount"] = True

    deprecatedActions = {}
    deprecatedActions["clearWorkflowLog"] = True
    deprecatedActions["prepareWorkflowLog"] = True
    deprecatedActions["prepareAllWorkflowLogs"] = True
    deprecatedActions["retrieveWorkflowLog"] = True
    deprecatedActions["getWorkflowDetails"] = True

    if action in deprecatedActions:
        message = "[WARNING] Deprecated action: '" + action + "'"
        if action == "clearWorkflowLog":
            message += "; use 'clearAllWorkflowLogs'"
        elif action == "prepareWorkflowLog" or action == "prepareAllWorkflowLogs" or action == "retrieveWorkflowLog":
            message += "; use 'retrieveAllWorkflowLogs'"

        response["status"] = "success"
        response_data["message"] = message
        response["data"] = response_data

        output = {"next": "ManagementServiceExit", "value": response}
        sapi.add_dynamic_workflow(output)
        return {}

    elif action in possibleActions:
        user = data["user"]
        status, statusmessage, token, authenticated_user = verifyUser(user, sapi, extendTokenExpiry=True)
        if status:
            sapi.log(statusmessage + " Authenticated user: " + str(authenticated_user))
            # pass the email to the next function,
            # so that they don't have to re-authenticate the again
            data["email"] = authenticated_user["email"]
            data["usertoken"] = token
            data["storage_userid"] = authenticated_user["storage_userid"]

            output = {"next": action, "value": data}
            sapi.add_dynamic_workflow(output)
            return {}
        else:
            response_data["message"] = "User verification failed: " + statusmessage
            sapi.log(response_data["message"])
    else:
        response_data["message"] = "Unsupported action."

    response["status"] = "failure"
    response["data"] = response_data

    output = {"next": "ManagementServiceExit", "value": response}
    sapi.add_dynamic_workflow(output)
    return None

def handle(event, context):
    assert isinstance(event, dict)
    request = event

    action = request["action"]
    data = request["data"]

    context.log(action)

    errmsg = ""
    if action == "version":
        return actionVersion(context)
    elif "user" in data:
        user = data["user"]
        unsupported_chars = False
        for key in user:
            if any(not (ord(c) < 128) for c in user[key]):
                unsupported_chars = True
            elif key == "email" and any(c == " " for c in user[key]):
                unsupported_chars = True

        if not unsupported_chars:
            if action == "signUp":
                return actionSignUp(user, context)

            elif action == "logIn":
                return actionLogin(user, context)

            elif action == "changePassword":
                return actionChangePassword(user, context)

            elif action == "changeName":
                return actionChangeName(user, context)

            elif action == "resetPassword":
                return actionResetPassword(user, context)

            elif action == "verifyUser":
                return actionVerifyUser(user, context)

            return actionOther(action, data, context)
        else:
            errmsg = "Non-ascii characters in name or email, or space characters in email."
            context.log(errmsg)

    response = {}
    response["status"] = "failure"
    response["data"] = {}
    response["data"]["message"] = "Invalid input parameters: " + errmsg
    context.add_workflow_next("ManagementServiceExit", response)
    return None
