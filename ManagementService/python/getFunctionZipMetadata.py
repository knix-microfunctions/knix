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

        if "id" in function:
            functions = sapi.get(email + "_list_grains", True)
            if functions is not None and functions != "":
                functions = json.loads(functions)
                if function["id"] in functions.values():
                    #functionMetadata = sapi.get(email + "_grain_source_zip_metadata_" + function["id"], True)
                    #if functionMetadata == "":
                    #    sapi.put(email + "_grain_source_zip_metadata_" + function["id"], "", True, True)

                    #num_chunks_str = sapi.get(email + "_grain_source_zip_num_chunks_" + function["id"], True)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    functionMetadata = dlc.get("grain_source_zip_metadata_" + function["id"])
                    if functionMetadata is None:
                        dlc.put("grain_source_zip_metadata_" + function["id"], "")
                        functionMetadata = ""

                    num_chunks_str = dlc.get("grain_source_zip_num_chunks_" + function["id"])
                    dlc.shutdown()

                    g = {}
                    g["format"] = "zipMetadata"
                    g["metadata"] = functionMetadata
                    try:
                        g["chunks"] = int(num_chunks_str)
                    except Exception:
                        g["chunks"] = -1

                    response_data["function"] = g
                    response_data["message"] = "Retrieved zip metadata for function " + function["id"] + "."

                    success = True

                else:
                    response_data["message"] = "Couldn't retrieve function zip metadata; no such function."
            else:
                response_data["message"] = "Couldn't retrieve function zip metadata; no such function."
        else:
            response_data["message"] = "Couldn't retrieve function zip metadata; malformed input."
    else:
        response_data["message"] = "Couldn't retrieve function zip metadata; malformed input."


    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(response["status"])

    return response

