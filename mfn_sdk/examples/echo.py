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

import time
import logging
from mfn_sdk import MfnClient

c = MfnClient()

logging.basicConfig(level=logging.DEBUG)

fn = c.add_function("echo")
fn.source = {'code': """
def handle(event, context):
    context.log("Echoing event: "+str(event))
    return event
"""}

workflow = c.add_workflow("echo_wf")
workflow.json = """{
  "name": "echo_wf",
  "entry": "echo",
  "functions": [
    {
      "name": "echo",
      "next": ["end"]
    }
  ]
}"""

workflow.deploy(600)
request = {"hui":"hoi","blue":True,"Five":5}
response = workflow.execute(request,timeout=5)
print(response)
assert response == request

logdata = workflow.logs()
print("Exceptions:")
print(logdata['exceptions'])
print("Logs:")
print(logdata['log'])
print("Progress:")
print(logdata['progress'])

