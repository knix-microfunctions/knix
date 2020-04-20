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

"""
  deploy: a script that sees for a workflow to be undeployed and deployed again
"""
import time
import logging
from mfn_sdk import MfnClient

c = MfnClient()

logging.basicConfig(level=logging.DEBUG)

workflow_name="echo_wf"

wf=None
for w in c.workflows:
  if w.name == workflow_name:
    wf=w
    break

# Just an example of undeploying
print("Workflow",wf.name,"is seen to be undeployed")

wf.undeploy()

# And an example of deploying
print("Workflow",wf.name,"is being deployed again")

wf.deploy()
