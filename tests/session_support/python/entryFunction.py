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

import time

def printSessionInfo(context):
    print("#### Session info ####")
    print("Session id: " + context.get_session_id())
    print("Session function ids: " + str(context.get_all_session_function_ids()))
    print("#############")

def test_session_alias_operations(event, context):
    print("Testing session alias operations...")
    print("All aliases should be printed without single quotes (i.e., '')")

    session_id = context.get_session_id()
    session_alias = context.get_session_alias()
    print("Current session's old session alias; should be none; got: " + str(session_id) + "->" + str(session_alias))

    context.set_session_alias("mySession")
    session_alias = context.get_session_alias()
    print("Current session's current session alias; should be 'mySession'; got: " + str(session_id) + "->" + str(session_alias))

    context.unset_session_alias()
    session_alias = context.get_session_alias()
    print("Unset current session's alias; should be none; got: " + str(session_id) + "->" + str(session_alias))

    print("------------------")

def test_session_function_alias_operations(event, context):
    print("Testing session function alias operations...")
    print("All aliases should be printed without single quotes (i.e., '')")

    sgidlist = context.get_all_session_function_ids()
    print(str(sgidlist))
    alias_list = []
    for sgid in sgidlist:
        sga = context.get_session_function_alias(sgid)
        print("Session function's old alias; should be none: " + str(sgid) + "->" + str(sga))

        context.set_session_function_alias("alias_" + sgid[0:8], sgid)
        sga = context.get_session_function_alias(sgid)
        print("Session function's new alias; should be 'alias_'" + sgid[0:8] + "; got: " + str(sgid) + "->" + str(sga))

        alias_list.append(sga)

        sgid2 = context.get_session_function_id_with_alias("alias_" + sgid[0:8])
        flag = False
        if sgid == sgid2:
            flag = True

        print("Got session function id with alias, flag should be True; flag: " + str(flag))
        print("---")

    context.set_session_alias("mySession")

    alias_summary = context.get_alias_summary()
    print("Summary should include aliases of all function ids and the alias of the session: " + str(alias_summary))

    print("Sending messages to session function instances with alias to change their heartbeat...")
    #"{\"action\":\"--update-heartbeat\",\"heartbeat_parameters\":{\"heartbeat_interval_ms\":2000,\"heartbeat_function\":\"heartbeatHandler\"}}"
    message = {}
    message["action"] = "--update-heartbeat"
    message["heartbeat_parameters"] = {}
    message["heartbeat_parameters"]["heartbeat_function"] = "heartbeatHandler"

    for sga in alias_list:
        print("Making heartbeat faster for session function instance with alias: " + str(sga))
        message["heartbeat_parameters"]["heartbeat_interval_ms"] = 1000
        context.send_to_running_function_in_session_with_alias(sga, message, True)

    print("Heartbeat should be sent every second; sleeping 5 seconds...")

    time.sleep(5)

    print("Woke up; slowing down heartbeat to one every 5 seconds...")

    for sga in alias_list:
        print("Making heartbeat slower for session function instance with alias: " + str(sga))
        message["heartbeat_parameters"]["heartbeat_interval_ms"] = 5000
        context.send_to_running_function_in_session_with_alias(sga, message, True)

    for sgid in sgidlist:
        context.unset_session_function_alias(sgid)

        sga = context.get_session_function_alias(sgid)
        print("Unset session function's alias; should be none: " + str(sgid) + "->" + str(sga))

        print("---")

    context.unset_session_alias()

    alias_summary = context.get_alias_summary()
    print("Summary should include aliases of all function ids and the alias of the session, should be none: " + str(alias_summary))

    print("------------------")

def handle(event, context):

    print("Starting regular function (entryFunction.py) with input: " + str(event))
    retval = None
    action = event["action"]

    send_now = False

    if action == "--create-new-session":
        print("Creating new session...")
        # should be a list of session functions to be initiated with their params
        session_description = event["session"]
        for sg in session_description:
            if "name" in sg and "parameters" in sg:
                sgname = sg["name"]
                sgparams = sg["parameters"]

                event2 = {}
                event2["sessionStartParams"] = sgparams

                context.add_workflow_next(sgname, event2)

    elif action == "--update-session":
        if "immediate" in event:
            send_now = event["immediate"]
        print("Updating existing session...")
        if event["messageType"] == "name":
            gname = event["messageToFunction"]
            print("updating all session functions with a given name: " + gname)
            context.send_to_all_running_functions_in_session_with_function_name(gname, event["sessionUpdateParams"], send_now)
        elif event["messageType"] == "session":
            print("updating all session functions in a session")
            context.send_to_all_running_functions_in_session(event["sessionUpdateParams"], send_now)

    elif action == "--update-session-function":
        if "immediate" in event:
            send_now = event["immediate"]
        sgid = event["sessionFunctionId"]
        print("Updating specific session function instance: " + sgid)
        context.send_to_running_function_in_session(sgid, event["sessionUpdateParams"], send_now)

    # alias setting and getting
    # sending messages with with aliases
    elif action == "--test-alias-operations":
        test_session_alias_operations(event, context)
        test_session_function_alias_operations(event, context)

    elif action == "--get-session-info":
        print("Getting session info...")
        sid = context.get_session_id()
        rgidlist = context.get_all_session_function_ids()

        info = {}
        info["session_id"] = sid
        info["session_function_ids"] = rgidlist
        retval = info

    elif action == "--get-session-alias-summary":
        print("Getting session alias info...")
        alias_summary = context.get_alias_summary()

        #print(alias_summary)
        retval = alias_summary

    elif action == "--set-alias":
        alias_type = event["alias_type"]
        alias = event["alias"]
        if alias_type == "session":
            context.set_session_alias(alias)
        elif alias_type == "function":
            function_id = event["function_id"]
            context.set_session_function_alias(alias, function_id)

    elif action == "--unset-alias":
        alias_type = event["alias_type"]
        alias = event["alias"]
        if alias_type == "session":
            context.unset_session_alias()
        elif alias_type == "function":
            function_id = event["function_id"]
            context.unset_session_function_alias(function_id)

    elif action == "--update-session-function-with-alias":
        alias = event["alias"]
        message = event["sessionUpdateParams"]
        context.send_to_running_function_in_session_with_alias(alias, message, True)

    elif action == "--print-session-info":
        print("Printing session info...")
        printSessionInfo(context)

    if retval is None:
        retval = context.get_session_id()

    if send_now:
        print("Sleeping for 5 seconds...")
        time.sleep(5.0)

    print("Finished regular function (entryFunction.py).")

    return retval

