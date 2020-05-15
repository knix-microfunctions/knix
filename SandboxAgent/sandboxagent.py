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

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time

import requests

from deployment import Deployment
import logging_helpers
import process_utils

sys.path.insert(1, os.path.join(sys.path[0], '../FunctionWorker/python'))

import py3utils
from DataLayerClient import DataLayerClient
from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage

LOG_FILENAME = '/opt/mfn/logs/sandboxagent.log'
FLUENTBIT_FOLDER = '/opt/mfn/LoggingService/fluent-bit' # this a symbolic link to the actual fluent-bit folder location inside the sandbox container
ELASTICSEARCH_INDEX_WF = 'mfnwf'
ELASTICSEARCH_INDEX_FE = 'mfnfe'

POLL_TIMEOUT = py3utils.ensure_long(60000)
#ELASTICSEARCH_INDEX = 'wf' # index name will be: 'wf' + [the first character of the workflow name (in lower case)]

class SandboxAgent:
    def __init__(self, hostname, queue, datalayer, sandboxid, userid, workflowid, elasticsearch, workflowname, endpoint_key):

        self._start = time.time()

        self._python_version = sys.version_info

        self._hostname = hostname
        self._queue = queue
        self._datalayer = datalayer
        self._elasticsearch = elasticsearch
        self._userid = userid
        self._sandboxid = sandboxid
        self._workflowid = workflowid
        self._workflowname = workflowname
        # _XXX_: we'll use the endpoint_key to look up our endpoint
        self._endpoint_key = endpoint_key
        self._deployment_info_key = "deployment_info_workflow_" + self._workflowid

        self._logger = logging_helpers.setup_logger(self._sandboxid, LOG_FILENAME)
        self._fluentbit_process, self._command_args_map_fluentbit = logging_helpers.setup_fluentbit_and_elasticsearch_index(self._logger, FLUENTBIT_FOLDER, self._elasticsearch, ELASTICSEARCH_INDEX_WF, ELASTICSEARCH_INDEX_FE)

        self._logger.info("hostname (and container name): %s", self._hostname)
        self._logger.info("elasticsearch nodes: %s", self._elasticsearch)
        self._logger.info("queueservice: %s", self._queue)
        self._logger.info("datalayer: %s", self._datalayer)
        self._logger.info("user id: %s", self._userid)
        self._logger.info("sandbox id: %s", self._sandboxid)
        self._logger.info("workflow id: %s", self._workflowid)
        self._logger.info("workflow name: %s", self._workflowname)
        self._logger.info("endpoint_key: %s", self._endpoint_key)

        self._instructions_topic = "instructions_" + self._sandboxid

        self._management_data_layer_client = DataLayerClient(locality=1, sid="Management", wid="Management", is_wf_private=True, connect=self._datalayer)
        self._logger.info("Management data layer client connected after %s s", str(time.time()-self._start))

        # to be declared later
        self._local_queue_client = None
        self._deployment = None
        self._queue_service_process = None
        self._frontend_process = None
        # visible to the outside world: either kubernetes assigned URL or bare-metal host address + exposed port
        self._external_endpoint = None
        # visible internally: kubernetes node address or same as bare-metal external endpoint
        self._internal_endpoint = None

        self._is_running = False
        self._shutting_down = False

    def _handle_instruction(self, instruction):
        error = None

        action = instruction["action"]
        if "parameters" in instruction:
            parameters = instruction["parameters"]

        if action == "stop-function-worker":
            self._deployment.stop_function_worker(parameters["functionTopic"])
        elif action == "shutdown":
            self.shutdown()
        else:
            error = "Unsupported 'action' in instruction: " + action

        return error

    def _get_and_handle_message(self):
        error = None

        lqm = self._local_queue_client.getMessage(self._instructions_topic, POLL_TIMEOUT)
        if lqm is not None:
            lqcm = LocalQueueClientMessage(lqm)
            key = lqcm.get_key()
            value = lqcm.get_value()
            self._logger.info(key + " " + value)
            try:
                instruction = json.loads(value)
                error = self._handle_instruction(instruction)
            except Exception as exc:
                error = "Couldn't decode instruction: " + str(exc)
                self._logger.error(error)

            if error is None:
                self._logger.info("Handled instruction successfully at t+ %s s", str(time.time()-self._start))

    def _process_deployment_info(self):
        has_error = False
        errmsg = ""

        deployment_info = self._management_data_layer_client.get(self._deployment_info_key)
        num_trials = 0
        sleep_time = 1.0
        while num_trials < 5 and (deployment_info is None or deployment_info == ""):
            time.sleep(sleep_time)
            deployment_info = self._management_data_layer_client.get(self._deployment_info_key)
            num_trials = num_trials + 1
            sleep_time = sleep_time * 2

        if num_trials == 5:
            has_error = True
            errmsg = "Could not retrieve deployment info: " + self._deployment_info_key

        if not has_error:
            # if we're running on kubernetes, the endpoint will correspond to the assigned url
            # if we're running on bare-metal, the endpoint will correspond to the hostip + docker-mapped port
            self._external_endpoint = self._management_data_layer_client.getMapEntry(self._workflowid + "_workflow_endpoint_map", endpoint_key)
            num_trials = 0
            sleep_time = 1.0
            while num_trials < 5 and (self._external_endpoint is None or self._external_endpoint == ""):
                time.sleep(sleep_time)
                self._external_endpoint = self._management_data_layer_client.getMapEntry(self._workflowid + "_workflow_endpoint_map", endpoint_key)
                num_trials = num_trials + 1
                sleep_time = sleep_time * 2

            if num_trials == 5:
                has_error = True
                errmsg = "Could not retrieve endpoint: " + self._endpoint_key

        # in Kubernetes, endpoint is the externally visible URL
        # in bare-metal, endpoint is the current host's address

        # for session support, in FunctionWorker, we need current host address (bare-metal)
        # or current node address (kubernetes)

        # for parallel state support, in FunctionWorker, either would be fine

        # As such, let the FunctionWorker know both and let it decide what to do
        if 'KUBERNETES_SERVICE_HOST' in os.environ:
            # get current node's internal address
            self._internal_endpoint = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + str(os.getenv("PORT", "8080"))
        else:
            # bare-metal mode: the current host's address and external address are the same
            self._internal_endpoint = self._external_endpoint

        if not has_error:
            self._logger.info("External endpoint: %s", self._external_endpoint)
            self._logger.info("Internal endpoint: %s", self._internal_endpoint)
            self._deployment = Deployment(deployment_info,\
                self._hostname, self._userid, self._sandboxid, self._workflowid,\
                self._workflowname, self._queue, self._datalayer, \
                self._logger, self._external_endpoint, self._internal_endpoint)
            self._deployment.set_child_process("fb", self._fluentbit_process, self._command_args_map_fluentbit)
            has_error, errmsg = self._deployment.process_deployment_info()

        return has_error, errmsg

    # SIGTERM kills Thrift before we can handle stuff
    def sigterm(self, signum, _):
        self._logger.info("SIGTERM received...")
        # we will call shutdown() when we catch the exception
        # raise interrupt to kill main sequence when shutdown was not received through the queue
        raise KeyboardInterrupt

    def sigchld(self, signum, _):
        if not self._shutting_down:
            should_shutdown, pid, failed_process_name = self._deployment.check_child_process()

            if should_shutdown:
                self._update_deployment_status(True, "A sandbox process stopped unexpectedly: " + failed_process_name)

                if pid == self._queue_service_process.pid:
                    self._queue_service_process = None
                elif pid == self._frontend_process.pid:
                    self._frontend_process = None

                self.shutdown(reason="Process " + failed_process_name + " with pid: " + str(pid) + " stopped unexpectedly.")

    def shutdown(self, reason=None):
        self._shutting_down = True
        errmsg = ""
        if reason is not None:
            errmsg = "Shutting down sandboxagent due to reason: " + reason + "..."
            self._logger.info(errmsg)
        else:
            self._logger.info("Gracefully shutting down sandboxagent...")

        if self._frontend_process is not None:
            self._logger.info("Shutting down the frontend...")
            self._frontend_process.terminate()
        else:
            self._logger.info("No frontend; most probably it was the reason of the shutdown.")

        # shutting down function workers depends on the queue service
        if self._queue_service_process is not None:
            self._logger.info("Shutting down the function worker(s)...")
            self._deployment.shutdown()

            # shut down the local queue client, so that we can also shut down the queue service
            self._local_queue_client.removeTopic(self._instructions_topic)
            self._local_queue_client.shutdown()

            self._logger.info("Shutting down the queue service...")
            process_utils.terminate_and_wait_child(self._queue_service_process, "queue service", 5, self._logger)
        else:
            self._logger.info("No queue service; most probably it was the reason of the shutdown.")
            self._logger.info("Force shutting down the function worker(s)...")
            self._deployment.force_shutdown()

        # we can't do this here, because there may be other sandboxes running the same workflow
        #self._management_data_layer_client.put("workflow_status_" + self._workflowid, "undeployed")
        self._management_data_layer_client.shutdown()

        self._logger.info("Shutting down fluent-bit...")
        time.sleep(2) # flush interval of fluent-bit
        process_utils.terminate_and_wait_child(self._fluentbit_process, "fluent-bit", 5, self._logger)

        self._is_running = False

        if self._frontend_process is not None:
            try:
                self._frontend_process.wait(30)
            except subprocess.TimeoutExpired as exc:
                self._frontend_process.kill()
                _, _ = self._frontend_process.communicate()

        self._logger.info("Shutdown complete.")
        if reason is not None:
            self._update_deployment_status(True, errmsg)
            self._management_data_layer_client.shutdown()
            os._exit(1)
        else:
            self._update_deployment_status(False, errmsg)
            self._management_data_layer_client.shutdown()
            os._exit(0)

    def _stop_deployment(self, reason, errmsg):
        self._logger.error("Stopping deployment due to error in launching %s...", reason)
        self._logger.info(errmsg)
        self._update_deployment_status(True, errmsg)
        self._management_data_layer_client.shutdown()
        os._exit(1)

    def _update_deployment_status(self, has_error, errmsg):
        sbstatus = {}
        sbstatus["errmsg"] = errmsg
        if has_error:
            sbstatus["status"] = "failed"
        else:
            if self._shutting_down:
                sbstatus["status"] = "undeployed"
            else:
                sbstatus["status"] = "deployed"

        # set our own status in the map
        self._management_data_layer_client.putMapEntry(self._workflowid + "_sandbox_status_map", self._endpoint_key, json.dumps(sbstatus))

    def run(self):
        has_error = False
        errmsg = ""

        ts_qs_launch = time.time()
        # 1. launch the QueueService here
        self._logger.info("Launching QueueService...")
        cmdqs = "java -jar /opt/mfn/queueservice.jar"
        command_args_map_qs = {}
        command_args_map_qs["command"] = cmdqs
        command_args_map_qs["wait_until"] = "Starting local queue..."
        error, self._queue_service_process = process_utils.run_command(cmdqs, self._logger, wait_until="Starting local queue...")
        if error is not None:
            has_error = True
            errmsg = "Could not start the sandbox queue service: " + str(error)

        if has_error:
            self._stop_deployment("queue service", errmsg)

        ts_fw_launch = time.time()
        # 2. process the deployment info and start function workers
        self._logger.info("Going to parse the deployment info and get the endpoint...")
        has_error, errmsg = self._process_deployment_info()

        if has_error:
            self._stop_deployment("workflow", errmsg)

        ts_fe_launch = time.time()
        # 3. launch the frontend
        self._logger.info("Launching frontend...")

        cmdweb = "/opt/mfn/frontend"
        fenv = dict(os.environ)
        workflow = self._deployment.get_workflow()
        fenv["MFN_ENTRYTOPIC"] = workflow.getWorkflowEntryTopic()
        fenv["MFN_RESULTTOPIC"] = workflow.getWorkflowExitTopic()
        fenv["MFN_QUEUE"] = self._queue
        # MFN_DATALAYER already set

        command_args_map_fe = {}
        command_args_map_fe["command"] = cmdweb
        command_args_map_fe["custom_env"] = fenv
        command_args_map_fe["wait_until"] = "Frontend is ready to handle requests"
        error, self._frontend_process = process_utils.run_command(cmdweb, self._logger, custom_env=fenv, wait_until="Frontend is ready to handle requests")
        if error is not None:
            has_error = True
            errmsg = "Could not start the frontend: " + str(error)

        if has_error:
            self._stop_deployment("frontend", errmsg)

        self._logger.info("frontend started")

        t_fe = (time.time() - ts_fe_launch) * 1000.0
        t_fw = (ts_fe_launch - ts_fw_launch) * 1000.0
        t_qs = (ts_fw_launch - ts_qs_launch) * 1000.0

        self._logger.info("QS launch time: %s (ms), FWs download + launch time: %s (ms), FE launch time: %s (ms)", str(t_qs), str(t_fw), str(t_fe))

        self._deployment.set_child_process("qs", self._queue_service_process, command_args_map_qs)
        self._deployment.set_child_process("fe", self._frontend_process, command_args_map_fe)

        signal.signal(signal.SIGTERM, self.sigterm)

        children_pids = self._deployment.get_all_children_pids()
        children_pids.sort()
        self._logger.info("All children pids: " + str(children_pids))

        signal.signal(signal.SIGCHLD, self.sigchld)

        # update our own sandbox status
        self._update_deployment_status(False, errmsg)

        #self._management_data_layer_client.put("workflow_status_" + self._workflowid, "deployed")
        #self._management_data_layer_client.delete("workflow_status_error_" + self._workflowid)

        # 4. start listening for additional instructions if any
        self._local_queue_client = LocalQueueClient(connect=self._queue)
        self._local_queue_client.addTopic(self._instructions_topic)

        self._is_running = True

        self._logger.info("Successfully deployed.")

        while self._is_running:
            try:
                self._get_and_handle_message()
            except KeyboardInterrupt as interrupt:
                self._logger.info("Interrupted...")
                self.shutdown()
            except Exception as exc:
                self._logger.error("%s", str(exc))
                # allow shutdown() some time to clean up
                if self._shutting_down:
                    time.sleep(5)
                else:
                    time.sleep(2)

def get_k8s_nodename():
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as ftoken:
        token = ftoken.read()
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as fnamespace:
        namespace = fnamespace.read()

    k8sport = os.getenv('KUBERNETES_SERVICE_PORT_HTTPS')
    podname = socket.gethostname()
    try:
        resp = requests.get(
            'https://kubernetes.default:'+k8sport+'/api/v1/namespaces/'+namespace+'/pods/'+podname,
            headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
            verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
            proxies={"https":""})
        resp.raise_for_status()
        pod = resp.json()
        return pod["spec"]["nodeName"]
    except (requests.exceptions.HTTPError, KeyError) as httperr:
        logger.error("Unable to find my own pod spec %s", podname)
        logger.error(resp.text, httperr)
        sys.exit(1)
    return podname

def find_k8s_ep(fqdn):
    # On K8s, sandboxes are run with MFN_HOSTNAME = kubernetes node name
    # Find host-local queue and datalayer endpoints
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as ftoken:
        token = ftoken.read()
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as fnamespace:
        namespace = fnamespace.read()

    k8sport = os.getenv('KUBERNETES_SERVICE_PORT_HTTPS')
    nodename = os.getenv("MFN_HOSTNAME")
    svcname = fqdn.split('.', 1)[0]
    retry = True
    try:
        while retry:
            resp = requests.get(
                'https://kubernetes.default:'+k8sport+'/api/v1/namespaces/'+namespace+'/endpoints/'+svcname,
                headers={"Authorization": "Bearer "+token, "Accept": "application/json"},
                verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
                proxies={"https":""})
            resp.raise_for_status()
            dleps = resp.json()
            # we got the service, if we can't find anything
            retry = False
            for subs in dleps["subsets"]:
                for addr in subs.get("addresses", []):
                    if addr.get("nodeName", None) == nodename:
                        logger.info("Found collocated endpoint of svc "+svcname+" at "+addr["ip"])
                        return addr["hostname"] + "." + svcname + ":" + str(dleps["subsets"][0]["ports"][0]["port"])
                for addr in subs.get("notReadyAddresses", []):
                    if addr.get("nodeName", None) == nodename:
                        infomsg = "Found collocated endpoint that isn't ready yet. Waiting another 5s for svc "+svcname+" endpoint at "+addr["ip"]+" to become ready"
                        logger.info(infomsg)
                        retry = True
                        time.sleep(5)
                        break
    except (requests.exceptions.HTTPError, KeyError) as httperr:
        logger.error("Unable to find a collocated service endpoint address for svc %s, please delete pod to have it rescheduled on another node", svcname)
        logger.error(resp.text, httperr)
        sys.exit(1)
    return fqdn

if __name__ == "__main__":
    logger = logging.getLogger()

    # MFN_HOSTNAME aka hostname is used to:
    # - distinguish whether functions are running on the same physical host or not, mainly for session functions
    # - allow kubernetes sandboxes to find the queue and datalayer endpoint that is host-local
    if len(sys.argv) == 8:
        logger.info("Getting parameters from the command line...")
        hostname = sys.argv[1]
        userid = sys.argv[3]
        sandboxid = sys.argv[4]
        workflowid = sys.argv[5]
        queue = "127.0.0.1:4999"
        datalayer = hostname + ":4998"
        elasticsearch = sys.argv[6]
        endpoint_key = sys.argv[7]
        workflowname = workflowid
    else:
        logger.info("Getting parameters from environment variables...")
        hostname = os.getenv("MFN_HOSTNAME", os.getenv("HOSTNAME", socket.gethostname()))
        queue = os.getenv("MFN_QUEUE", "127.0.0.1:4999")
        datalayer = os.getenv("MFN_DATALAYER", hostname+":4998")
        userid = os.getenv("USERID")
        sandboxid = os.getenv("SANDBOXID")
        workflowid = os.getenv("WORKFLOWID")
        elasticsearch = os.getenv("MFN_ELASTICSEARCH", hostname+":9200")
        endpoint_key = os.getenv("MFN_ENDPOINT_KEY")
        workflowname = os.getenv("WORKFLOWNAME", workflowid)

    if os.path.exists('/var/run/secrets/kubernetes.io'):
        if "MFN_HOSTNAME" not in os.environ:
            os.environ["MFN_HOSTNAME"] = get_k8s_nodename()
            hostname = os.environ["MFN_HOSTNAME"]
        # Find endpoints for datalayer
        datalayer = find_k8s_ep(datalayer)
        #queue = find_k8s_ep(queue)

    sandbox_agent = SandboxAgent(hostname, queue, datalayer, sandboxid, userid, workflowid, elasticsearch, workflowname, endpoint_key)
    sandbox_agent.run()
