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
import uuid
import hashlib
import time

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False
    errmsg = "some error occurred."

    email = data["email"]

    if "function" in data:
        function = data["function"]

        sapi.log(json.dumps(function))

        f = {}
        if function["name"] == "exit" or function["name"] == "end":
            errmsg = "[ERROR]: '" + function["name"] + "' is reserved; its use as a function name is not allowed."
        elif any(c.isspace() or c == ":" for c in function["name"]):
            errmsg = "[ERROR]: Whitespace/colons(:) in function names is not allowed: '" + function["name"] + "'"
        else:
            f["name"] = function["name"]
            f["runtime"] = function["runtime"]
            f["gpu_usage"] = function["gpu_usage"]
            f["gpu_mem_usage"] = function["gpu_mem_usage"]
            f["modified"] = time.time()

            f["id"] = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

            sapi.put(email + "_grain_" + f["id"], json.dumps(f), True, True)
            #sapi.put(email + "_grain_source_" + f["id"], "", True, True)
            #sapi.put(email + "_grain_source_zip_metadata_" + f["id"], "", True, True)
            #sapi.put(email + "_grain_requirements_" + f["id"], "", True, True)

            functions = sapi.get(email + "_list_grains", True)
            if functions is not None and functions != "":
                functions = json.loads(functions)
            else:
                functions = {}

            functions[f["name"]] = f["id"]

            sapi.put(email + "_list_grains", json.dumps(functions), True, True)

            response_data["message"] = "Function added successfully."
            response_data["function"] = f

            success = True

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"
        response_data["message"] = "Couldn't add function: " + errmsg

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

