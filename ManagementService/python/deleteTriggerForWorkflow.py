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

    print("DeleteTriggerForWorkflow called with data: " + str(data))

    # data must have, trigger_type, trigger_tag, workflow name, function-name, trigger_type_info - amqp_addr, routing-key, exchange name, bools,
    # generate trigger metadata info
        # trigger_type
        # tag
        # trigger_type_info
    # get workflow info
    # if workflow does not exist then return error
    # if workflow exists then check if the trigger metadata already exists 
    # now check whether the workflow is deployed or not. If not then queue up, else get info and register trigger


    # register trigger will first pick a frontend, construct the message (along with a trigger_id based on time) and send it
    # if the response is success, then it will add the trigger_id to frontend_info.
    # if will also create an entry in the global trigger_id map, with: trigger id -->  status, frontend ip address, associated workflows, metadata required to re-create the trigger if needed

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
