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

    print("Delete trigger called with data: " + str(data))

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
