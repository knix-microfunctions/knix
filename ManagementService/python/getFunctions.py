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

    functions = sapi.get(email + "_list_grains", True)

    if functions is not None and functions != "":
        #sapi.log(functions)
        functions = json.loads(functions)
        f_list = []
        for i in functions:
            f = sapi.get(email + "_grain_" + functions[i], True)
            if f is not None and f != "":
                f = json.loads(f)
                if "modified" not in f:
                    f["modified"] = 0

                f_list.append(f)

        response_data["functions"] = f_list
        response_data["message"] = "Found " + str(len(f_list)) + " functions."

    else:
        # no functions yet
        response_data["functions"] = []
        response_data["message"] = "No functions yet."

    success = True

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(json.dumps(response))

    return response

