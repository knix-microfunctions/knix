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
  clear: a script that DELETES ALL workflows, functions and objects of a 
          MicroFunctions account
"""
import getpass

from mfn_sdk import MfnClient

c = MfnClient()

print("URL:  ", c.url)
print("USER: ", c.user)
print("THIS CLEARS ALL FUNCTIONS, WORKFLOWS AND DATA IN YOUR ACCOUNT")
if not input("Are you sure? (y/N): ").lower().strip()[:1] == "y": sys.exit(1)

for w in c.workflows:
  print("Deleting workflow",w.name)
  c.delete_workflow(w)
for g in c.functions:
  print("Deleting function",g.name)
  c.delete_function(g)
for k in list(c.keys()):
  print("Deleting object",k)
  c.delete(k)
