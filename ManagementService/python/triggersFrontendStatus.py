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
import time

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value
    #sapi.log(json.dumps(data))
    action = data["action"]
    self_ip_port = data["self_ip_port"]

    if action is "start":
        print("START Triggers Frontend: " + self_ip_port)
        pass
        #handle_start(data)
    elif action is "status":
        print("STATUS Triggers Frontend: " + self_ip_port)
        pass
        #handle_status(data)
    elif action is "stop":
        print("STOP Triggers Frontend: " + self_ip_port)
        pass
        #handle_stop(data)
    else:
        pass

    success = False
    errmsg = "some error occurred."
    response = {}
    response_data = {}

    success = True
    response_data["message"] = "Triggers Frontend added successfully."
    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"
        response_data["message"] = "Couldn't add Triggers Frontend add successfully: " + errmsg

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response
