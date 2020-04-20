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

import os

content = ""

try:
    curdir = os.path.dirname(__file__)
    print("function's current directory: " + curdir)
    with open("data.dat", "r") as f:
        content = f.readlines()
    content = ''.join(content).strip()
except Exception as exc:
    content = "It didn't work."
    #raise exc


def handle(event, context):

    return content

