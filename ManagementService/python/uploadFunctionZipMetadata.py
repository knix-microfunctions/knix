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

        if "id" in function and "metadata" in function and "format" in function:
            sapi.log(function["id"] + " " + function["format"])
            functions = sapi.get(email + "_list_grains", True)
            if functions is not None and functions != "":
                functions = json.loads(functions)
                if function["id"] in functions.values():
                    if function["format"] == "zipMetadata":
                        function["metadata"] = function["metadata"].replace(" ", "+")
                        #sapi.put(email + "_grain_source_zip_metadata_" + function["id"], function["metadata"], True, True)
                        #sapi.put(email + "_grain_source_zip_num_chunks_" + function["id"], str(function["chunks"]), True, True)

                        dlc = sapi.get_privileged_data_layer_client(storage_userid)
                        dlc.put("grain_source_zip_metadata_" + function["id"], function["metadata"])
                        dlc.put("grain_source_zip_num_chunks_" + function["id"], str(function["chunks"]))
                        dlc.shutdown()

                        sapi.log(email + " " + function["id"] + " stored zip metadata; num chunks: " + str(function["chunks"]))

                        response_data["message"] = "Function zip metadata uploaded successfully."
                        success = True

                    else:
                        response_data["message"] = "Couldn't upload function zip metadata; unsupported upload format."
                else:
                    response_data["message"] = "Couldn't upload function zip metadata; no such function."
            else:
                response_data["message"] = "Couldn't upload function zip metadata; no such function."
        else:
            response_data["message"] = "Couldn't upload function zip metadata; malformed input."
    else:
        response_data["message"] = "Couldn't upload function zip metadata; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(response["status"])

    return response

