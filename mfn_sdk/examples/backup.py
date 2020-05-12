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
  backup: a script that downloads all workflows, functions and data of a 
          MicroFunctions account and pickles the main info to a file
"""
import requests
import os
import base64
import pickle
import sys

from mfn_sdk import MfnClient

c = MfnClient()

data = dict()

with open("backup.p","wb") as backup:
    fns = c.functions
    for f in fns:
        f.source # to retrieve _code _zip and _metadata
        fobj = {
            '_runtime':f._runtime,
            '_name':f._name,
            '_modified':f._modified,
            'requirements':f.requirements,
            'source':f.source
            }
        pickle.dump(fobj,backup)
    ws = c.workflows
    for w in ws:
        wobj = {
            'name':w.name,
            'json':w.json
        }
        pickle.dump(wobj,backup)
    for k in list(c.keys()):
        sobj = {
            'key':k,
            'value':c.get(k)
        }
        pickle.dump(sobj,backup)
