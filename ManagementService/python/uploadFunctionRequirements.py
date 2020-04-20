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

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False

    email = data["email"]
    storage_userid = data["storage_userid"]

    if "function" in data:
        function = data["function"]

        sapi.log(json.dumps(function))

        if "id" in function and "requirements" in function:
            functions = sapi.get(email + "_list_grains", True)
            if functions is not None and functions != "":
                functions = json.loads(functions)

                if function["id"] in functions.values():
                    function["requirements"] = function["requirements"].replace(" ", "+")
                    #sapi.put(email + "_grain_requirements_" + function["id"], function["requirements"], True, True)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    if function["requirements"] == "":
                        dlc.delete("grain_requirements_" + function["id"])
                    else:
                        dlc.put("grain_requirements_" + function["id"], function["requirements"])
                    dlc.shutdown()

                    response_data["message"] = "Function requirements uploaded successfully."

                    success = True

                else:
                    response_data["message"] = "Couldn't upload function requirements; no such function."
            else:
                response_data["message"] = "Couldn't upload function requirements; no such function."
        else:
            response_data["message"] = "Couldn't upload function requirements; malformed input."
    else:
        response_data["message"] = "Couldn't upload function requirements; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

