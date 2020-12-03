import os
import time

def handle(event, context):
    # wait for workflow endpoint to become available. If workflowname is "", then it is taken from the 'WORKFLOWNAME' env variable available in all knix sandboxes
    endpoint_available = wait_for_workflow_endpoint_to_become_available(context, workflowname="", timeout_sec=20)
    if endpoint_available:
        print("Workflow endpoint is available")
        return True
    else:
        print("Workflow endpoint is not available")
        return False


def wait_for_workflow_endpoint_to_become_available(context, workflowname = "", timeout_sec = 20):
    if workflowname == "":
        if 'WORKFLOWNAME' in os.environ and type(os.environ['WORKFLOWNAME']) == type("") and len(os.environ['WORKFLOWNAME']) > 0:
            workflowname = os.environ['WORKFLOWNAME']
    
    if workflowname == "":
        print("[wait_for_workflow_endpoint_to_become_available] Error, WORKFLOWNAME env variable not found")
        return False

    message = f"[wait_for_workflow_endpoint_to_become_available] workflow: {workflowname}, timeout_sec: {timeout_sec}"
    c = 0
    while True:
        c = c + 1
        print(message + ", Fetching details, attempt " + str(c))
        response = context._getWorkflowDetails(workflowname)
        if response == None or response['status'] != 'success' or 'data' not in response:
            print(message + ", Error: response: " + str(response))
            return False

        wf_info = response['data']
        if wf_info is None or type(wf_info) is not type({}) or len(wf_info) == 0:
            print(message + ", Error: workflow info not available: " + str(wf_info))
            return False

        if 'status' not in wf_info or 'endpoints' not in wf_info:
            print(message + ", Error: status or endpoint fields not available: " + str(wf_info))
            return False
        
        endpoints = wf_info['endpoints']
        status = wf_info['status']
        
        if status == 'deployed' or status == 'deploying':
            if len(endpoints) > 0:
                return True
            else:
                pass
        else:
            print(message + ", Error: workflow status is: " + status + ", " + str(wf_info))
            return False

        if c < timeout_sec:
            time.sleep(1)
        else:
            print(message + ", Error: Timeout")
            return False
