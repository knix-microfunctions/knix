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

function = c.add_function("react")
function.code = """
def handle(event, context):
    context.log("Triggered "+str(event))

    return None
"""

workflow = c.add_workflow("eventdriven_workflow")
workflow.json = """{
  "name": "eventdriven_workflow",
  "entry": "react",
  "functions": [
    {
      "name": "react",
      "next": ["end"]
    }
  ]
}"""

workflow.deploy(60)

### Create Trigger
trigger = c.add_trigger("amqptrigger",{
    "trigger_type": "amqp", 
    "amqp_addr": "amqp://<user>:<pass>@<host>:5672//test", 
    "routing_key": "my_topic",
    "exchange": "my_exchange",
    "with_ack": False,
    "durable": False,
})

trigger.associate_workflow(workflow)

time.sleep(3)

trigger.disassociate_workflow(workflow)

print(workflow.logs()['log'])