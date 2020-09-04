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
import base64

# ["wftrigtest", "trigtable", "trigkey"]

workflow_other_json = '''{
	"Comment": "other Workflow",
	"StartAt": "test",
	"States": {
		"test": {
			"Type": "Task",
			"Resource": "triggerable_table",
			"End": true
		}
	}
}'''

def handle(event, context):
    if type(event) == type([]):
        nonce = event[3]
        print("_!_EXPLICIT_START_" + nonce)
        workflowname = event[0]
        tablename = event[1] + "__" + nonce
        keyname = event[2] + "__" + nonce
        workflow_other = workflowname + "__" + nonce

        print("addTriggerableTable: " + tablename)
        print("addTriggerableTable: " + str(context.addTriggerableTable(tableName=tablename)))
        time.sleep(1)
        
        print("addStorageTriggerForWorkflow: " + workflowname + ", tablename: " + tablename)
        print("addStorageTriggerForWorkflow: " + str(context.addStorageTriggerForWorkflow(workflowname, tableName=tablename)))
        time.sleep(1)


        print("getWorkflowDetails: " + workflowname)
        response = context.getWorkflowDetails(workflowname)
        assert(response != None)
        #print("getWorkflowDetails response: " + str(response))
        assert(response['status'] == 'success')
        associatedTables = response['data']['associatedTriggerableTables']
        assert(len(associatedTables) == 1)
        assert(tablename in associatedTables)
        workflow_id = response['data']["id"]
        time.sleep(1)


        print("getTriggerableTables")
        response = context.getTriggerableTables()
        assert(response != None)
        #print("getTriggerableTables response: " + str(response))
        assert(response['status'] == 'success')
        triggerableTables = response['data']['tables']
        assert(tablename in triggerableTables)
        tableInfo = triggerableTables[tablename]
        assert(type(tableInfo) == type([]))
        assert(len(tableInfo) == 1)
        assert(workflowname in tableInfo)


        print("addWorkflow: " + workflow_other)
        request = \
        {
            "action": "addWorkflow",
            "data": {
                "workflow": {"name": workflow_other}
            }
        }
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("addWorkflow response: " + str(response))
        assert(response['status'] == 'success')
        workflow_other_id = response['data']['workflow']['id']
        time.sleep(1)


        print("uploadWorkflowJSON: " + workflow_other)
        request = \
        {
            "action": "uploadWorkflowJSON",
            "data": {
                "workflow": {"id": workflow_other_id, "json": base64.b64encode(workflow_other_json.encode()).decode()}
            }
        }
        #print("uploadWorkflowJSON request: " + str(request))
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("uploadWorkflowJSON response: " + str(response))
        assert(response['status'] == 'success')
        time.sleep(1)


        print("addStorageTriggerForWorkflow: " + workflow_other + ", tablename: " + tablename)
        print("addStorageTriggerForWorkflow: " + str(context.addStorageTriggerForWorkflow(workflow_other, tableName=tablename)))
        time.sleep(1)


        print("getWorkflowDetails: " + workflow_other)
        response = context.getWorkflowDetails(workflow_other)
        assert(response != None)
        #print("getWorkflowDetails response: " + str(response))
        assert(response['status'] == 'success')
        associatedTables = response['data']['associatedTriggerableTables']
        assert(len(associatedTables) == 1)
        assert(tablename in associatedTables)
        time.sleep(1)


        print("getTriggerableTables")
        response = context.getTriggerableTables()
        assert(response != None)
        #print("getTriggerableTables response: " + str(response))
        assert(response['status'] == 'success')
        triggerableTables = response['data']['tables']
        assert(tablename in triggerableTables)
        tableInfo = triggerableTables[tablename]
        assert(type(tableInfo) == type([]))
        assert(len(tableInfo) == 1)
        assert(workflowname in tableInfo)
        time.sleep(1)


        print("deployWorkflow: " + workflow_other)
        request = \
        {
            "action": "deployWorkflow",
            "data": {
                "workflow": {"id": workflow_other_id}
            }
        }
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("deployWorkflow response: " + str(response))
        assert(response['status'] == 'success')
        time.sleep(5)


        print("getTriggerableTables")
        response = context.getTriggerableTables()
        assert(response != None)
        #print("getTriggerableTables response: " + str(response))
        assert(response['status'] == 'success')
        triggerableTables = response['data']['tables']
        assert(tablename in triggerableTables)
        tableInfo = triggerableTables[tablename]
        assert(type(tableInfo) == type([]))
        assert(len(tableInfo) == 2)
        assert(workflowname in tableInfo)
        assert(workflow_other in tableInfo)
        time.sleep(1)


        # this should trigger both the workflows
        keyname_to_use = keyname + "_1"
        print("Writing to triggerable table: " + tablename + ", key: " + keyname_to_use)
        value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce}
        context.put(keyname_to_use, json.dumps(value), tableName=tablename)
        time.sleep(3)

        print("deleteStorageTriggerForWorkflow: " + workflow_other + ", tablename: " + tablename)
        print("deleteStorageTriggerForWorkflow: " + str(context.deleteStorageTriggerForWorkflow(workflow_other, tableName=tablename)))
        time.sleep(1)


        # this should trigger just the main workflow
        keyname_to_use = keyname + "_2"
        print("Writing to triggerable table: " + tablename + ", key: " + keyname_to_use)
        value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce}
        context.put(keyname_to_use, json.dumps(value), tableName=tablename)
        time.sleep(3)


        print("addStorageTriggerForWorkflow: " + workflow_other + ", tablename: " + tablename)
        print("addStorageTriggerForWorkflow: " + str(context.addStorageTriggerForWorkflow(workflow_other, tableName=tablename)))
        time.sleep(1)


        # this should trigger both the workflows
        keyname_to_use = keyname + "_3"
        print("Writing to triggerable table: " + tablename + ", key: " + keyname_to_use)
        value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce}
        context.put(keyname_to_use, json.dumps(value), tableName=tablename)
        time.sleep(3)


        print("undeployWorkflow: " + workflow_other)
        request = \
        {
            "action": "undeployWorkflow",
            "data": {
                "workflow": {"id": workflow_other_id}
            }
        }
        #print(str(request))
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("undeployWorkflow response: " + str(response))
        assert(response['status'] == 'success')
        time.sleep(5)


        print("getWorkflowDetails: " + workflow_other)
        response = context.getWorkflowDetails(workflow_other)
        assert(response != None)
        #print("getWorkflowDetails response: " + str(response))
        assert(response['status'] == 'success')
        associatedTables = response['data']['associatedTriggerableTables']
        assert(len(associatedTables) == 1)
        assert(tablename in associatedTables)
        time.sleep(1)


        print("getTriggerableTables")
        response = context.getTriggerableTables()
        assert(response != None)
        #print("getTriggerableTables: " + str(response))
        assert(response['status'] == 'success')
        triggerableTables = response['data']['tables']
        assert(tablename in triggerableTables)
        tableInfo = triggerableTables[tablename]
        assert(type(tableInfo) == type([]))
        assert(len(tableInfo) == 1)
        assert(workflowname in tableInfo)
        time.sleep(1)

        # this should trigger the main workflow only
        keyname_to_use = keyname + "_4"
        print("Writing to triggerable table: " + tablename + ", key: " + keyname_to_use)
        value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce}
        context.put(keyname_to_use, json.dumps(value), tableName=tablename)
        time.sleep(5)


        print("deleteTriggerableTable: " + tablename)
        print("deleteTriggerableTable: " + str(context.deleteTriggerableTable(tableName=tablename)))
        time.sleep(1)


        trigger_start_other_wf = 0
        explicit_start_other_wf = 0
        trigger_start_main_wf = 0
        explicit_start_main_wf = 0

        print("retrieveAllWorkflowLogs: " + workflow_other)
        request = \
        {
            "action": "retrieveAllWorkflowLogs",
            "data": {
                "workflow": {"id": workflow_other_id}
            }
        }
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("retrieveAllWorkflowLogs response: " + str(response))
        assert(response['status'] == 'success')
        other_workflow_log = response["data"]["workflow"]["log"]
        other_workflow_log = base64.b64decode(other_workflow_log).decode()
        other_workflow_log_lines = other_workflow_log.split("\n")
        for line in other_workflow_log_lines:
            if "_!_TRIGGER_START_" + nonce in line.strip():
                trigger_start_other_wf = trigger_start_other_wf + 1
            if "_!_EXPLICIT_START_" + nonce in line.strip():
                explicit_start_other_wf = explicit_start_other_wf + 1
        time.sleep(5)


        print("deleteWorkflow: " + workflow_other)
        request = \
        {
            "action": "deleteWorkflow",
            "data": {
                "workflow": {"id": workflow_other_id}
            }
        }
        #print(str(request))
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("deleteWorkflow reponse: " + str(response))
        assert(response['status'] == 'success')
        time.sleep(1)


        print("retrieveAllWorkflowLogs: " + workflowname)
        request = \
        {
            "action": "retrieveAllWorkflowLogs",
            "data": {
                "workflow": {"id": workflow_id}
            }
        }
        status, message, response = context.invoke_management_api(request)
        assert(status == True)
        #print("retrieveAllWorkflowLogs response: " + str(response))
        assert(response['status'] == 'success')
        workflow_log = response["data"]["workflow"]["log"]
        workflow_log = base64.b64decode(workflow_log).decode()
        workflow_log_lines = workflow_log.split("\n")
        for line in other_workflow_log_lines:
            #print(line.strip())
            if "_!_TRIGGER_START_" + nonce in line.strip():
                trigger_start_main_wf = trigger_start_main_wf + 1
            if "_!_EXPLICIT_START_" + nonce in line.strip():
                explicit_start_main_wf = explicit_start_main_wf + 1
        time.sleep(1)
        
        response = \
        {
            "trigger_start_main_wf": trigger_start_main_wf, 
            "explicit_start_main_wf": explicit_start_main_wf, 
            "trigger_start_other_wf": trigger_start_other_wf, 
            "explicit_start_other_wf": explicit_start_other_wf, 
            "main_wf": workflowname, 
            "other_wf": workflow_other,
            "tablename": tablename,
            "keyname": keyname
        }

        print("MAIN_WORKFLOW,TRIGGERS," + str(trigger_start_main_wf) + ",EXPLICIT,"+str(explicit_start_main_wf))
        print("OTHER_WORKFLOW,TRIGGERS," + str(trigger_start_other_wf) + ",EXPLICIT,"+str(explicit_start_other_wf))
        return response
    else:
        if type(event) == type({}) and 'nonce' in event:
            print("_!_TRIGGER_START_" + event['nonce'])
        return event
