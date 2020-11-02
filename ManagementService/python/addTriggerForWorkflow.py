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

MAP_AVAILABLE_FRONTENDS = "available_triggers_frontned_map"
MAP_TRIGGERS_TO_INFO = "triggers_to_info_map"

def handle(value, context):
    assert isinstance(value, dict)
    data = value

    print("AddTriggerForWorkflow called with data: " + str(data))

    # data will have workflow_name, trigger_name
    # check if the trigger exists in both global and user's list
    # check if the workflow exists, if not return error
    # if workflow exists, then check if the trigger_name already exists in associated triggers for this workflow
        # if not then add it to the workflow
    # check if workflow is deployed. 
        #   If yes, then get workflow url, get the frontend_ip_port, send the add message
        #   if not then do nothing?


    response = {}
    response_data = {}
    errmsg = ""

    success = True

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"
        response_data["message"] = errmsg
    response["data"] = response_data
    return response
