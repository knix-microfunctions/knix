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

# ["wf_triggers_storage", "triggerable_bucket", "triggerable_key"]


def handle(event, context):
    if type(event) == type([]):
        nonce = event[3]
        print(f"_!_EXPLICIT_START_{nonce}")
        workflowname = event[0]
        bucketname = event[1] + "__" + nonce
        keyname = event[2] + "__" + nonce
        workflow_other = workflowname + "__" + nonce

        try:
            # creating a bucket
            addTriggerableBucket(bucketname, context)

            # associating main wf with bucket
            addStorageTriggerForWorkflow(workflowname, bucketname, context)

            # check if bucket is added in workflows metadata
            response = checkWorkflowDetailsForAssociatedBucketnames(
                workflowname, [bucketname], context)
            workflow_id = response['data']["id"]

            # check if workflow is added in bucket metadata
            reponse = checkBucketDetailsForAssociatedWorkflows(
                bucketname, [workflowname], context)

            # add the other workflow
            workflow_other_id = addWorkflow(workflow_other, context)

            # upload the workflow description for the other workflow
            uploadWorkflowJSON(workflow_other, workflow_other_id,
                               workflow_other_json, context)

            # associating other wf with bucket. This association will be queued up, since the workflow has not been deployed.
            addStorageTriggerForWorkflow(workflow_other, bucketname, context)

            # check if bucket is added to other workflow's metadata
            checkWorkflowDetailsForAssociatedBucketnames(
                workflow_other, [bucketname], context)

            # the other workflow should not yet have been added to the bucket metadata, since the workflow is not deployed
            checkBucketDetailsForAssociatedWorkflows(
                bucketname, [workflowname], context)

            # deploy the other workflow, any queued up associations between the workflow and associated buckets will now be made
            deployWorkflow(workflow_other, workflow_other_id, context)
            time.sleep(5)

            # both workflows now should have been added to the bucket metadata
            checkBucketDetailsForAssociatedWorkflows(
                bucketname, [workflowname, workflow_other], context)

            # this should trigger both the workflows
            count = 1
            keyname_to_use = f"{keyname}_1"
            value = {'workflowname': workflowname, 'bucketname': bucketname,
                     'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(
                f"Writing to triggerable bucket: {bucketname}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(
                value), bucketName=bucketname)
            time.sleep(3)

            # remove the association between other workflow and the bucket
            deleteStorageTriggerForWorkflow(
                workflow_other, bucketname, context)

            # this should trigger just the main workflow
            count = 2
            keyname_to_use = f"{keyname}_2"
            value = {'workflowname': workflowname, 'bucketname': bucketname,
                     'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(
                f"Writing to triggerable bucket: {bucketname}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(
                value), bucketName=bucketname)
            time.sleep(3)

            # associating other wf with bucket again. This association will be immediately added since the workflow is deployed
            addStorageTriggerForWorkflow(workflow_other, bucketname, context)

            # this should trigger both the workflows
            count = 3
            keyname_to_use = f"{keyname}_1"
            value = {'workflowname': workflowname, 'bucketname': bucketname,
                     'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(
                f"Writing to triggerable bucket: {bucketname}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(
                value), bucketName=bucketname)
            time.sleep(3)

            undeployWorkflow(workflow_other, workflow_other_id, context)

            # check if bucket is added to other workflow's metadata
            checkWorkflowDetailsForAssociatedBucketnames(
                workflow_other, [bucketname], context)

            # check if bucket is added to main workflow's metadata
            checkWorkflowDetailsForAssociatedBucketnames(
                workflowname, [bucketname], context)

            # check how many workflows are associated with bucket
            checkBucketDetailsForAssociatedWorkflows(
                bucketname, [workflowname], context)

            # this should trigger just the main workflow
            count = 4
            keyname_to_use = f"{keyname}_2"
            value = {'workflowname': workflowname, 'bucketname': bucketname,
                     'workflow_other': workflow_other, 'nonce': nonce, 'count': str(count)}
            print(
                f"Writing to triggerable bucket: {bucketname}, key: {keyname_to_use}")
            context.put(keyname_to_use, json.dumps(
                value), bucketName=bucketname)
            time.sleep(3)

            # remove the association between other workflow and the bucket
            deleteStorageTriggerForWorkflow(
                workflow_other, bucketname, context)

            # check if there are no associated buckets for other workflow
            checkWorkflowDetailsForAssociatedBucketnames(
                workflow_other, [], context)

            # remove the association between main workflow and the bucket
            deleteStorageTriggerForWorkflow(workflowname, bucketname, context)

            # check if there are no associated buckets
            checkWorkflowDetailsForAssociatedBucketnames(
                workflowname, [], context)

            # check if there are no workflows associated with the bucket
            checkBucketDetailsForAssociatedWorkflows(bucketname, [], context)

            # delete the bucket
            deleteTriggerableBucket(bucketname, context)

            trigger_start_other_wf = 0
            explicit_start_other_wf = 0
            trigger_start_main_wf = 0
            explicit_start_main_wf = 0
            other_trigger_logs = []
            main_trigger_logs = []

            # get workflow logs for the other workflow
            other_workflow_log_lines = retrieveAllWorkflowLogs(
                workflow_other, workflow_other_id, context)
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
            workflow_log_lines = retrieveAllWorkflowLogs(
                workflowname, workflow_id, context)
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
                    "bucketname": bucketname,
                    "keyname": keyname,
                    "main_trigger_logs": main_trigger_logs,
                    "other_trigger_logs": other_trigger_logs
                }

            print("MAIN_WORKFLOW,TRIGGERS," + str(trigger_start_main_wf) +
                  ",EXPLICIT,"+str(explicit_start_main_wf))
            print("OTHER_WORKFLOW,TRIGGERS," + str(trigger_start_other_wf) +
                  ",EXPLICIT,"+str(explicit_start_other_wf))
            return response

        except Exception as e:
            try:
                if workflow_other_id != None and workflow_other_id != "":
                    undeployWorkflow(
                        workflow_other, workflow_other_id, context)
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
                deleteTriggerableBucket(bucketname, context)
            except Exception as g:
                pass
            raise e

    else:
        if type(event) == type({}) and 'key' in event and 'value' in event and 'source' in event:
            value = json.loads(event["value"])
            if 'nonce' in value and 'count' in value:
                print("_!_TRIGGER_START_" +
                      value['nonce'] + ";" + value['count'])
        else:
            assert(0)
        return event


def addTriggerableBucket(bucketname, context):
    message = f"addTriggerableBucket Bucket: {bucketname}"
    ret = context.addTriggerableBucket(bucketName=bucketname)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def deleteTriggerableBucket(bucketname, context):
    message = f"deleteTriggerableBucket bucket: {bucketname}"
    ret = context.deleteTriggerableBucket(bucketName=bucketname)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def addStorageTriggerForWorkflow(workflowname, bucketname, context):
    message = f"addStorageTriggerForWorkflow Bucket: {bucketname}, workflowname: {workflowname}"
    ret = context.addStorageTriggerForWorkflow(
        workflowname, bucketName=bucketname)
    if ret == None or ret == False:
        message = f"{message}, Error: response: {ret}"
        print(message)
        raise Exception(message)
    else:
        message = f"{message}, Success: response: {ret}"
        print(message)
    time.sleep(1)


def checkWorkflowDetailsForAssociatedBucketnames(workflowname, expected_bucketnames, context):
    message = f"checkWorkflowDetailsForAssociatedBucketnames: workflow {workflowname}, expected_bucketnames: {expected_bucketnames}"
    response = context._getWorkflowDetails(workflowname)
    if response == None or response['status'] != 'success':
        message = f"{message}, Error: response: {response}"
        print(message)
        raise Exception(message)

    associatedTables = response['data']['associatedTriggerableTables']
    if len(associatedTables) != len(expected_bucketnames):
        message = f"{message}, Error: Mismatch between the expected number of buckets associated with workflow and the actual number. Response: {response}"
        print(message)
        raise Exception(message)

    for tablename in expected_bucketnames:
        if tablename not in associatedTables:
            message = f"{message}, Error: could not find bucket {tablename} in list of associated buckets. Reponse: {response}"
            print(message)
            raise Exception(message)

    message = f"{message}, Success"
    print(message)
    return response


def checkBucketDetailsForAssociatedWorkflows(bucketname, expected_workflows, context):
    message = f"checkBucketDetailsForAssociatedWorkflows: bucketname {bucketname}, expected_workflows: {expected_workflows}"
    response = context._getTriggerableBuckets()
    if response == None or response['status'] != 'success':
        message = f"{message}, Error: Response: {response}"
        print(message)
        raise Exception(message)

    triggerableTables = response['data']['buckets']

    if bucketname not in triggerableTables:
        message = f"{message}, Error: bucket not found in list of triggerable buckets. Reponse: {response}"
        print(message)
        raise Exception(message)

    tableInfo = triggerableTables[bucketname]
    if type(tableInfo) != type([]) or len(tableInfo) != len(expected_workflows):
        message = f"{message}, Error: Mismatch between the expected number of workflows associated with bucket and the actual number. Response: {response}"
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
    status, status_message, response = context._invoke_management_api(request)
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
    status, status_message, response = context._invoke_management_api(request)
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
    status, status_message, response = context._invoke_management_api(request)
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
    status, status_message, response = context._invoke_management_api(request)
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
    status, status_message, response = context._invoke_management_api(request)
    if status != True or response['status'] != 'success':
        message = f"{message}, Status message: {status_message}, Error: Response: {response}"
        print(message)
        raise Exception(message)

    message = f"{message}, Success."
    print(message)


def deleteStorageTriggerForWorkflow(workflowname, bucketname, context):
    message = f"deleteStorageTriggerForWorkflow Bucket: {bucketname}, workflowname: {workflowname}"
    ret = context.deleteStorageTriggerForWorkflow(
        workflowname, bucketName=bucketname)
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
    status, status_message, response = context._invoke_management_api(request)
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
