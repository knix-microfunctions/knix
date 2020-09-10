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


workflow_other_json = '''{
	"Comment": "other Workflow",
	"StartAt": "test",
	"States": {
		"test": {
			"Type": "Task",
			"Resource": "triggers_storage",
			"End": true
		}
	}
}'''

# ["wf_triggers_storage", "triggerable_table", "triggerable_key"]
def handle(event, context):
    if type(event) == type([]):
        nonce = event[3]
        print(f"_!_EXPLICIT_START_{nonce}")
        workflowname = event[0]
        tablename = event[1] + "__" + nonce
        keyname = event[2] + "__" + nonce
        workflow_other = workflowname + "__" + nonce

        try:
            # creating a table
            addTriggerableTable(tablename, context)

            # associating main wf with table
            addStorageTriggerForWorkflow(workflowname, tablename, context)

            # check if table is added in workflows metadata
            response = checkWorkflowDetailsForAssociatedTablenames(workflowname, [tablename], context)
            workflow_id = response['data']["id"]

            # check if workflow is added in table metadata
            reponse = checkTableDetailsForAssociatedWorkflows(tablename, [workflowname], context)

            # add the other workflow
            workflow_other_id = addWorkflow(workflow_other, context)

            # upload the workflow description for the other workflow
            uploadWorkflowJSON(workflow_other, workflow_other_id, workflow_other_json, context)

            # associating other wf with table. This association will be queued up, since the workflow has not been deployed.
            addStorageTriggerForWorkflow(workflow_other, tablename, context)

            # check if table is added to other workflow's metadata
            checkWorkflowDetailsForAssociatedTablenames(workflow_other, [tablename], context)

            # the other workflow should not yet have been added to the table metadata, since the workflow is not deployed
            checkTableDetailsForAssociatedWorkflows(tablename, [workflowname], context)

            # deploy the other workflow, any queued up associations between the workflow and associated tables will now be made
            deployWorkflow(workflow_other, workflow_other_id, context)
            time.sleep(5)

            # both workflows now should have been added to the table metadata
            checkTableDetailsForAssociatedWorkflows(tablename, [workflowname, workflow_other], context)

            # this should trigger both the workflows
            count = 1
            keyname_to_use = f"{keyname}_1"
            value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(f"Writing to triggerable table: {tablename}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(value), tableName=tablename)
            time.sleep(3)


            # remove the association between other workflow and the table
            deleteStorageTriggerForWorkflow(workflow_other, tablename, context)

            # this should trigger just the main workflow
            count = 2
            keyname_to_use = f"{keyname}_2"
            value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(f"Writing to triggerable table: {tablename}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(value), tableName=tablename)
            time.sleep(3)


            # associating other wf with table again. This association will be immediately added since the workflow is deployed
            addStorageTriggerForWorkflow(workflow_other, tablename, context)


            # this should trigger both the workflows
            count = 3
            keyname_to_use = f"{keyname}_1"
            value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(f"Writing to triggerable table: {tablename}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(value), tableName=tablename)
            time.sleep(3)


            undeployWorkflow(workflow_other, workflow_other_id, context)

            # check if table is added to other workflow's metadata
            checkWorkflowDetailsForAssociatedTablenames(workflow_other, [tablename], context)

            # check if table is added to main workflow's metadata
            checkWorkflowDetailsForAssociatedTablenames(workflowname, [tablename], context)

            # check how many workflows are associated with table
            checkTableDetailsForAssociatedWorkflows(tablename, [workflowname], context)


            # this should trigger just the main workflow
            count = 4
            keyname_to_use = f"{keyname}_2"
            value = {'workflowname': workflowname, 'tablename': tablename, 'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(f"Writing to triggerable table: {tablename}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(value), tableName=tablename)
            time.sleep(3)

            # remove the association between other workflow and the table
            deleteStorageTriggerForWorkflow(workflow_other, tablename, context)

            # check if there are no associated tables for other workflow
            checkWorkflowDetailsForAssociatedTablenames(workflow_other, [], context)

            # remove the association between main workflow and the table
            deleteStorageTriggerForWorkflow(workflowname, tablename, context)

            # check if there are no associated tables
            checkWorkflowDetailsForAssociatedTablenames(workflowname, [], context)

            # check if there are no workflows associated with the table
            checkTableDetailsForAssociatedWorkflows(tablename, [], context)

            # delete the table
            deleteTriggerableTable(tablename, context)

            trigger_start_other_wf = 0
            explicit_start_other_wf = 0
            trigger_start_main_wf = 0
            explicit_start_main_wf = 0
            other_trigger_logs = []
            main_trigger_logs = []

            # get workflow logs for the other workflow
            other_workflow_log_lines = retrieveAllWorkflowLogs(workflow_other, workflow_other_id, context)
            for line in other_workflow_log_lines:
                if "_!_TRIGGER_START_" + nonce in line.strip():
                    trigger_start_other_wf = trigger_start_other_wf + 1
                    other_trigger_logs.append(line)
                if "_!_EXPLICIT_START_" + nonce in line.strip():
                    explicit_start_other_wf = explicit_start_other_wf + 1
            time.sleep(1)

            # delete other workflow
            deleteWorkflow(workflow_other, workflow_other_id, context)

            # get workflow logs for the main workflow
            workflow_log_lines = retrieveAllWorkflowLogs(workflowname, workflow_id, context)
            for line in workflow_log_lines:
                if "_!_TRIGGER_START_" + nonce in line.strip():
                    trigger_start_main_wf = trigger_start_main_wf + 1
                    main_trigger_logs.append(line)
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
                "keyname": keyname,
                "main_trigger_logs": main_trigger_logs,
                "other_trigger_logs": other_trigger_logs
            }

            print("MAIN_WORKFLOW,TRIGGERS," + str(trigger_start_main_wf) + ",EXPLICIT,"+str(explicit_start_main_wf))
            print("OTHER_WORKFLOW,TRIGGERS," + str(trigger_start_other_wf) + ",EXPLICIT,"+str(explicit_start_other_wf))
            return response

        except Exception as e:
            try:
                if workflow_other_id != None and workflow_other_id != "":
                    undeployWorkflow(workflow_other, workflow_other_id, context)
                    time.sleep(1)
            except Exception as f:
                pass

            try:
                if workflow_other_id != None and workflow_other_id != "":
                    deleteWorkflow(workflow_other, workflow_other_id, context)
                    time.sleep(1)
            except Exception as f:
                pass

            try:
                deleteTriggerableTable(tablename, context)
            except Exception as g:
                pass
            raise e

    else:
        if type(event) == type({}) and 'nonce' in event and 'count' in event:
            print("_!_TRIGGER_START_" + event['nonce'] + ";" + event['count'])
        return event


def addTriggerableTable(tablename, context):
    message = f"addTriggerableTable Table: {tablename}"
    ret = context.addTriggerableTable(tableName=tablename)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def deleteTriggerableTable(tablename, context):
    message = f"deleteTriggerableTable Table: {tablename}"
    ret = context.deleteTriggerableTable(tableName=tablename)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def addStorageTriggerForWorkflow(workflowname, tablename, context):
    message = f"addStorageTriggerForWorkflow Table: {tablename}, workflowname: {workflowname}"
    ret = context.addStorageTriggerForWorkflow(workflowname, tableName=tablename)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def checkWorkflowDetailsForAssociatedTablenames(workflowname, expected_tablenames, context):
    message = f"checkWorkflowDetailsForAssociatedTablenames: workflow {workflowname}, expected_tablenames: {expected_tablenames}"
    response = context.getWorkflowDetails(workflowname)
    if response == None or response['status'] != 'success':
        message = f"{message}, Error: response: {response}"
        print(message)
        raise Exception(message)

    associatedTables = response['data']['associatedTriggerableTables']
    if len(associatedTables) != len(expected_tablenames):
        message = f"{message}, Error: Mismatch between the expected number of tables associated with workflow and the actual number. Response: {response}"
        print(message)
        raise Exception(message)

    for tablename in expected_tablenames:
        if tablename not in associatedTables:
            message = f"{message}, Error: could not find table {tablename} in list of associated tables. Reponse: {response}"
            print(message)
            raise Exception(message)

    message = f"{message}, Success"
    #message = f"{message}, Success, Reponse: {response}"
    print(message)
    return response


def checkTableDetailsForAssociatedWorkflows(tablename, expected_workflows, context):
    message = f"checkTableDetailsForAssociatedWorkflows: tablename {tablename}, expected_workflows: {expected_workflows}"
    response = context.getTriggerableTables()
    if response == None or response['status'] != 'success':
        message = f"{message}, Error: Response: {response}"
        print(message)
        raise Exception(message)

    triggerableTables = response['data']['tables']

    if tablename not in triggerableTables:
        message = f"{message}, Error: table not found in list of triggerable tables. Reponse: {response}"
        print(message)
        raise Exception(message)

    tableInfo = triggerableTables[tablename]
    if type(tableInfo) != type([]) or len(tableInfo) != len(expected_workflows):
        message = f"{message}, Error: Mismatch between the expected number of workflows associated with table and the actual number. Response: {response}"
        print(message)
        raise Exception(message)
    
    for workflowname in expected_workflows:
        if workflowname not in tableInfo:
            message = f"{message}, Error: could not find workflow {workflowname} in list of associated workflows. Reponse: {response}"
            print(message)
            raise Exception(message)

    message = f"{message}, Success"
    #message = f"{message}, Success, Reponse: {response}"
    print(message)
    return response


def addWorkflow(workflowname, context):
    message = f"addWorkflow: workflow: {workflowname}"
    request = \
    {
        "action": "addWorkflow",
        "data": {
            "workflow": {"name": workflowname}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    workflow_id = response['data']['workflow']['id']
    message = f"{message}, Success, workflow_id = {workflow_id}"
    print(message)
    return workflow_id


def deleteWorkflow(workflowname, workflow_id, context):
    message = f"deleteWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
    {
        "action": "deleteWorkflow",
        "data": {
            "workflow": {"id": workflow_id}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success"
    print(message)


def uploadWorkflowJSON(workflowname, workflow_id, workflow_json, context):
    message = f"uploadWorkflowJSON: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
    {
        "action": "uploadWorkflowJSON",
        "data": {
            "workflow": {"id": workflow_id, "json": base64.b64encode(workflow_json.encode()).decode()}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def deployWorkflow(workflowname, workflow_id, context):
    message = f"deployWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
    {
        "action": "deployWorkflow",
        "data": {
            "workflow": {"id": workflow_id}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def undeployWorkflow(workflowname, workflow_id, context):
    message = f"undeployWorkflow: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
    {
        "action": "undeployWorkflow",
        "data": {
            "workflow": {"id": workflow_id}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Status message: {status_message}, Error: Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def deleteStorageTriggerForWorkflow(workflowname, tablename, context):
    message = f"deleteStorageTriggerForWorkflow Table: {tablename}, workflowname: {workflowname}"
    ret = context.deleteStorageTriggerForWorkflow(workflowname, tableName=tablename)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def retrieveAllWorkflowLogs(workflowname, workflow_id, context):
    message = f"retrieveAllWorkflowLogs: workflow: {workflowname}, workflow_id: {workflow_id}"
    request = \
    {
        "action": "retrieveAllWorkflowLogs",
        "data": {
            "workflow": {"id": workflow_id}
        }
    }
    status, status_message, response = context.invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Error: Status message: {status_message}, Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)

    workflow_log = response["data"]["workflow"]["log"]
    workflow_log = base64.b64decode(workflow_log).decode()
    workflow_log_lines = workflow_log.split("\n")
    return workflow_log_lines
