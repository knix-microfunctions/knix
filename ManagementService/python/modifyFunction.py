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

    response = {}
    response_data = {}

    success = False

    email = data["email"]

    if "function" in data:
        function = data["function"]

        sapi.log(json.dumps(function))

        if "id" in function and "name" in function and "runtime" in function:
            f = sapi.get(email + "_grain_" + function["id"], True)

            if f is not None and f != "":
                f = json.loads(f)

                functions = sapi.get(email + "_list_grains", True)
                if functions is not None and functions != "":
                    functions = json.loads(functions)
                    del functions[f["name"]]
                else:
                    functions = {}

                functions[function["name"]] = function["id"]

                f["name"] = function["name"]
                f["runtime"] = function["runtime"]
                f["modified"] = time.time()
                f["gpu_usage"] = function["gpu_usage"]
                f["gpu_mem_usage"] = function["gpu_mem_usage"]
 
                sapi.put(email + "_grain_" + function["id"], json.dumps(f), True, True)

                sapi.put(email + "_list_grains", json.dumps(functions), True, True)

                response_data["message"] = "Updated function " + function["id"] + "."
                response_data["function"] = f

                success = True

            else:
                response_data["message"] = "Couldn't modify function; function metadata is not valid."
        else:
            response_data["message"] = "Couldn't modify function; malformed input."
    else:
        response_data["message"] = "Couldn't modify function; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

