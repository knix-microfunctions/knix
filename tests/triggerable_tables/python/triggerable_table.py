#!/usr/bin/python
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
import json

def handle(event, context):
    if type(event) == type([]):
        print("Test function start with list")
        print(str(event))
        print(str(type(event)))
        workflowname = event[0]
        tablename = event[1]
        keyname = event[2]
        print(str(context.addTriggerableTable(tableName=tablename)))
        time.sleep(2)
        print(str(context.addStorageTriggerForWorkflow(workflowname, tableName=tablename)))
        time.sleep(2)
        value = {'workflowname': workflowname, 'tablename': tablename}
        context.put(keyname, json.dumps(value), tableName=tablename)
        pass
    else:
        print("Test function start WITHOUT list")
        print(str(event))
        print(str(type(event)))
    return event
