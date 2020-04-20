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
  transfer: a script that transfers all functions, workflows and objects from
            an existing account at one microfunctions platform to another
"""
from mfn_sdk import MfnClient

import logging
logging.basicConfig(level=logging.DEBUG)

# The account to read from (tries to find default settings)
c1 = MfnClient()

# The account to write to
c2 = MfnClient.load_json(filename="settings_target.json")

print("Copying all contents of")
print("User",c1.user,"at microfunctions",c1.url)
print(" TO")
print("User",c2.user,"at microfunctions",c2.url)

for fn1 in c1.functions:
  print("Syncing function",fn1.name)
  fn2 = c2.add_function(fn1.name,fn1.runtime)
  s = fn1.source
  if 'zip' in s:
    print("Function ",fn1.name,"has type zip with",str(len(s['zip'])),"chunks")
  fn2.source = fn1.source
  fn2.requirements = fn1.requirements

for w1 in c1.workflows:
  print("Syncing workflow",w1.name)
  w2 = c2.add_workflow(w1.name)
  w2.json = w1.json

for key in list(c1.keys()):
  print("Syncing key",key)
  c2.put(key,c1.get(key))
