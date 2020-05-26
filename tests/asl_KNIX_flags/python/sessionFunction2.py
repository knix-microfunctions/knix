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

SLEEP_TIME = 10.0
FUNCTION_NAME = "sessionFunction2"

def doStuff(sgid):
    #print("Doing actual stuff (" + FUNCTION_NAME + ")..." + " session function id: " + sgid)
    return "telemetry_" + FUNCTION_NAME + "::doStuff()"

def doSomethingElse(sgid):
    #print("Doing something else (" + FUNCTION_NAME + ")..." + " session function id: " + sgid)
    return "telemetry_" + FUNCTION_NAME + "::doSomethingElse()"

def handle(event, context):

    sgid = context.get_session_function_id()

    print("Starting long-running function (" + FUNCTION_NAME + ") with input: " + str(event) + " session function id: " + sgid)

    params = event["sessionStartParams"]

    while context.is_still_running():
        print("New loop iteration (" + FUNCTION_NAME + ")... " + " session function id: " + sgid)
        # 1. check for a new update message
        msgs = context.get_session_update_messages()

        # 2. do something with that new message
        for msg in msgs:
            if msg != None:
                print("Received new message (" + FUNCTION_NAME + "): " + str(msg) + " session function id: " + sgid)
                params = msg

        telemetry = {}
        telemetry["action"] = "--telemetry"
        telemetry["function_name"] = FUNCTION_NAME
        telemetry["session_id"] = context.get_session_id()
        telemetry["session_function_id"] = sgid
        telemetry["timestamp"] = time.time() * 1000.0
        # 3. do other stuff
        if params == "config1":
            telemetry["telemetry"] = doStuff(sgid)
        elif params == "config2":
            telemetry["telemetry"] = doSomethingElse(sgid)
        else:
            print("Undefined configuration parameter (" + FUNCTION_NAME + "); not doing anything..." + " session function id: " + sgid)
            telemetry["telemetry"] = FUNCTION_NAME + "::None"

        # send the telemetry
        context.send_to_function_now("telemetryHandler", telemetry)

        #print("Sleeping (" + FUNCTION_NAME + ")... " + str(SLEEP_TIME) + " seconds." + " session function id: " + sgid)
        time.sleep(SLEEP_TIME)

    print("Finished long-running function (" + FUNCTION_NAME + ")." + " session function id: " + sgid)

    return "end of " + FUNCTION_NAME
