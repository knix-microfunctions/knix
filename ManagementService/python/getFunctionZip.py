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
                    #num_chunks_str = sapi.get(email + "_grain_source_zip_num_chunks_" + function["id"], True)

                    #num_chunks = int(num_chunks_str)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    num_chunks_str = dlc.get("grain_source_zip_num_chunks_" + function["id"])

                    try:
                        num_chunks = int(num_chunks_str)
                    except Exception as e:
                        num_chunks = -1

                    if "chunk" in function and function["chunk"] < num_chunks:
                        #functionZip = sapi.get(email + "_grain_source_zip_" + function["id"] + "_chunk_" + str(function["chunk"]), True)

                        functionZip = dlc.get("grain_source_zip_" + function["id"] + "_chunk_" + str(function["chunk"]))

                        f = {}
                        f["format"] = "zip"
                        f["code"] = functionZip

                        sapi.log(function["id"] + " loaded zip chunk: " + str(function["chunk"]))

                        response_data["function"] = f
                        response_data["message"] = "Retrieved zip chunk for function " + function["id"] + ", chunk: " + str(function["chunk"]) + "."

                        success = True
                    else:
                        response_data["message"] = "Couldn't retrieve function zip chunk; no such chunk or function['chunk'] not set; should be between 0 and " + str(num_chunks - 1)  + "."

                    dlc.shutdown()

                else:
                    response_data["message"] = "Couldn't retrieve function zip chunk; no such function."
            else:
                response_data["message"] = "Couldn't retrieve function zip; no such function."
        else:
            response_data["message"] = "Couldn't retrieve function zip; malformed input."
    else:
        response_data["message"] = "Couldn't retrieve function zip; malformed input."


    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(response["status"])

    return response

