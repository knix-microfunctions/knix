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
                    for fn in functions:
                        if functions[fn] == function["id"]:
                            del functions[fn]
                            break

                    sapi.delete(email + "_grain_" + function["id"], True, True)

                    #sapi.delete(email + "_grain_source_" + function["id"], True, True)
                    #sapi.delete(email + "_grain_source_zip_metadata_" + function["id"], True, True)
                    #sapi.delete(email + "_grain_requirements_" + function["id"], True, True)

                    #num_chunks_str = sapi.get(email + "_grain_source_zip_num_chunks_" + function["id"], True)

                    #if num_chunks_str is not None and num_chunks_str != "":
                    #    num_chunks = int(num_chunks_str)

                    #    for i in range(num_chunks):
                    #        sapi.delete(email + "_grain_source_zip_" + function["id"] + "_chunk_" + str(i), True, True)

                    #sapi.delete(email + "_grain_source_zip_num_chunks_" + function["id"], True, True)

                    dlc = sapi.get_privileged_data_layer_client(storage_userid)
                    dlc.delete("grain_source_" + function["id"])
                    dlc.delete("grain_source_zip_metadata_" + function["id"])
                    dlc.delete("grain_requirements_" + function["id"])

                    num_chunks_str = dlc.get("grain_source_zip_num_chunks_" + function["id"])

                    try:
                        num_chunks = int(num_chunks_str)
                    except Exception as e:
                        num_chunks = -1

                    for i in range(num_chunks):
                        dlc.delete("grain_source_zip_" + function["id"] + "_chunk_" + str(i))

                    dlc.delete("grain_source_zip_num_chunks_" + function["id"])
                    dlc.shutdown()

                    sapi.put(email + "_list_grains", json.dumps(functions), True, True)

                    response_data["message"] = "Deleted function " + function["id"] + "."

                    success = True

                else:
                    response_data["message"] = "Couldn't delete function; no such function."
            else:
                response_data["message"] = "Couldn't delete function; no such function."
        else:
            response_data["message"] = "Couldn't delete function; malformed input."
    else:
        response_data["message"] = "Couldn't delete function; malformed input."


    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

