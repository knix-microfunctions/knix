#   Copyright 2021 The KNIX Authors
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

"""
  trigger: a script that sets up a triggerable bucket and a function and workflow
  
  The workflow is associated with the triggerable bucket.
  Upon writing to the triggerable bucket, the workflow is executed.
  The function then writes the data to the general storage.
  The script tries to retrieve the data from the general storage.
"""
import base64
import time

from mfn_sdk import MfnClient

c = MfnClient()

function = c.add_function("transform")
function.code = """
def handle(event, context):
    context.log("Triggered "+str(event))

    if 'key' in event and 'value' in event:
      context.put(event['key'], event['value'])

    return None
"""

workflow = c.add_workflow("workflow")
workflow.json = """{
  "name": "workflow",
  "entry": "transform",
  "functions": [
    {
      "name": "transform",
      "next": ["end"]
    }
  ]
}"""

### Create triggerable bucket, deploy workflow and associate it 
inbox = c.add_bucket("inbox")
workflow.deploy(60)
inbox.associate_workflow(workflow)

### Delete the key from general storage (if it exists)
c.delete("foo")

### Write the key to the inbox
inbox.put("foo", base64.b64encode("bar".encode()).decode())

### Wait for the key to appear in the general storage
while True:
  foo = c.get("foo")
  if foo == "bar":
    print("Found key in general storage: foo="+foo)
    break
  else:
    print("Waiting for key foo")
    time.sleep(1)