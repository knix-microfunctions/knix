#!/usr/bin/python
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
import json
import base64

def handle(event, context):
    if type(event) == type([]):
        return event
    else:
        if type(event) == type({}) \
            and 'trigger_status' in event \
            and 'trigger_type' in event  \
            and 'trigger_name' in event \
            and 'workflow_name' in event \
            and 'source' in event \
            and 'data' in event:
                assert(event["trigger_type"] == "timer")
                assert(event["trigger_status"] == "ready" or event["trigger_status"] == "error")
                print("_!_TRIGGER_START_" + event['trigger_name'] + ";triggers_timer_state2;" + event['workflow_name'] + ";" + event['source'] + ";" + event['data'])
                time.sleep(1)
                return {}
        elif type(event) == type({}):
            return event
        else:
            print("ERROR: received event: " + str(event))
            assert(0)


