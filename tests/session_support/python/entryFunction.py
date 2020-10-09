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
            print("Updating all session functions with a given name: " + gname)
            context.send_to_all_running_functions_in_session_with_function_name(gname, event["sessionUpdateParams"], send_now)
        elif event["messageType"] == "session":
            print("Updating all session functions in a session")
            context.send_to_all_running_functions_in_session(event["sessionUpdateParams"], send_now)

    elif action == "--update-session-function":
        if "immediate" in event:
            send_now = event["immediate"]
        sgid = event["sessionFunctionId"]
        print("Updating specific session function instance: " + sgid)
        context.send_to_running_function_in_session(sgid, event["sessionUpdateParams"], send_now)

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
        if alias_type == "session":
            context.unset_session_alias()
        elif alias_type == "function":
            function_id = event["function_id"]
            context.unset_session_function_alias(function_id)

    elif action == "--update-session-function-with-alias":
        alias = event["alias"]
        message = event["sessionUpdateParams"]
        context.send_to_running_function_in_session_with_alias(alias, message, True)

    if retval is None:
        retval = context.get_session_id()

    if send_now:
        print("Sleeping for 5 seconds...")
        time.sleep(5.0)

    print("Finished regular function (entryFunction.py).")

    return retval

