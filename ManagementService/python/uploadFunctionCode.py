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
    storage_userid = data["storage_userid"]

    if "function" in data:
        function = data["function"]

        if "id" in function and "code" in function and "format" in function:
            sapi.log(function["id"] + " " + function["format"])
            functions = sapi.get(email + "_list_grains", True)
            f = sapi.get(email + "_grain_" + function["id"], True)
            if functions is not None and functions != "" and f is not None and f != "":
                functions = json.loads(functions)
                f = json.loads(f)

                if function["id"] in functions.values():
                    function["code"] = function["code"].replace(" ", "+")

                    f["modified"] = time.time()
                    sapi.put(email + "_grain_" + function["id"], json.dumps(f), True, True)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)

                    if function["format"] == "text":
                        #sapi.put(email + "_grain_source_" + function["id"], function["code"], True, True)

                        dlc.put("grain_source_" + function["id"], function["code"])

                        response_data["message"] = "Function code uploaded successfully."
                        response_data["function"] = f
                        success = True

                    elif function["format"] == "zip":
                        #sapi.put(email + "_grain_source_zip_" + function["id"] + "_chunk_" + str(function["chunk"]), function["code"], True, True)

                        dlc.put("grain_source_zip_" + function["id"] + "_chunk_" + str(function["chunk"]), function["code"])

                        sapi.log(function["id"] + " stored zip chunk: " + str(function["chunk"]))

                        response_data["message"] = "Function code zip chunk uploaded successfully:" + str(function["chunk"])
                        response_data["function"] = f
                        success = True

                    else:
                        response_data["message"] = "Couldn't upload function code; unsupported upload format."

                    dlc.shutdown()

                else:
                    response_data["message"] = "Couldn't upload function code; no such function."
            else:
                response_data["message"] = "Couldn't upload function code; no such function."
        else:
            response_data["message"] = "Couldn't upload function code; malformed input."
    else:
        response_data["message"] = "Couldn't upload function code; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

