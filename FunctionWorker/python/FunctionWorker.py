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

from signal import signal, SIGCHLD, SIG_IGN, SIG_DFL
import os
import sys
#import argparse
import time
import imp
import json
import logging
import socket
import subprocess
import shlex
#import hashlib
from threading import Timer

import thriftpy2

#from retry import retry

from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage
#from DataLayerClient import DataLayerClient
from MicroFunctionsLogWriter import MicroFunctionsLogWriter
from MicroFunctionsAPI import MicroFunctionsAPI
from StateUtils import StateUtils
from SessionUtils import SessionUtils
from PublicationUtils import PublicationUtils

import py3utils

LOGGER_HOSTNAME = 'hostname-unset'
LOGGER_CONTAINERNAME = 'containername-unset'
LOGGER_UUID = '0l'
LOGGER_USERID = 'userid-unset'
LOGGER_WORKFLOWNAME = 'workflow-name-unset'
LOGGER_WORKFLOWID = 'workflow-id-unset'

class LoggingFilter(logging.Filter):
    def filter(self, record):
        global LOGGER_HOSTNAME
        global LOGGER_CONTAINERNAME
        global LOGGER_UUID
        global LOGGER_USERID
        global LOGGER_WORKFLOWNAME
        global LOGGER_WORKFLOWID
        record.timestamp = time.time()*1000000
        record.hostname = LOGGER_HOSTNAME
        record.containername = LOGGER_CONTAINERNAME
        record.uuid = LOGGER_UUID
        record.userid = LOGGER_USERID
        record.workflowname = LOGGER_WORKFLOWNAME
        record.workflowid = LOGGER_WORKFLOWID
        return True

class FunctionWorker:

    # TODO: scratch space for each function worker, possibly tmpfs path
    # each topic is defined as a function of (user, sandbox, workflow, function id). as a result, topic will identify the workflow.
    def __init__(self, args_dict):
        self._POLL_MAX_NUM_MESSAGES = 500
        self._POLL_TIMEOUT = py3utils.ensure_long(10000)

        self._set_args(args_dict)

        self._prefix = self._sandboxid + "-" + self._workflowid + "-"
        self._wf_local = {}

        self._setup_loggers()

        self._state_utils = StateUtils(self._function_state_type, self._function_state_name, self._function_state_info, self._function_runtime, self._logger, self._workflowid, self._sandboxid, self._function_topic, self._datalayer, self._storage_userid, self._internal_endpoint)

        # check the runtime
        if self._function_runtime == "java":
            self._api_thrift = thriftpy2.load("/opt/mfn/FunctionWorker/MicroFunctionsAPI.thrift", module_name="mfnapi_thrift")

        elif self._function_runtime == "python 3.6":
            # if it is python, load the user code
            sys.path.insert(1, self._function_folder)
            if self._state_utils.isTaskState():
                try:
                    prevdir = os.path.dirname(__file__)
                    #self._logger.debug("dir of functionworker before importing user code: " + prevdir)
                    os.chdir(self._function_folder)
                    # FIXME: need to fix this part for python3 compatibility
                    self.code = imp.load_source(self._function_name, self._function_path)
                    os.chdir(prevdir)
                    #curdir = os.path.dirname(__file__)
                    #self._logger.debug("dir of functionworker after importing user code: " + curdir)
                except Exception as exc:
                    self._logger.exception("Exception loading user code: %s", str(exc))
                    sys.stdout.flush()
                    os._exit(1)

        # for retrieving new messages
        self.local_queue_client = LocalQueueClient(connect=self._queue)

        # for storing (key, pid) tuples on the data layer
        # keyspace: hostname + "InstancePidMap"
        # tablename: topic with "_" as separator
        # entries := (key, pid)
        #self._map_name_key_pid = "KeyPidMap_" + self._hostname + "_" + self._function_topic.replace("-", "_").replace(".", "_")
        #self.local_data_layer_client = DataLayerClient(locality=0, sid=self._sandboxid, for_mfn=True, connect=self._datalayer)

        signal(SIGCHLD, SIG_IGN)

        self._is_running = False
        #self._print_self()

    def _set_args(self, args):
        self._userid = args["userid"]
        self._storage_userid = args["storageuserid"]
        self._sandboxid = args["sandboxid"]
        self._workflowid = args["workflowid"]
        self._workflowname = args["workflowname"]
        self._function_path = args["fpath"]
        self._function_name = args["fname"]
        self._function_folder = args["ffolder"]
        self._function_state_type = args["functionstatetype"]
        self._function_state_name = args["functionstatename"]
        self._function_state_info = args["functionstateinfo"]
        self._function_topic = args["ftopic"]
        self._hostname = args["hostname"]
        self._queue = args["queue"]
        self._datalayer = args["datalayer"]
        self._external_endpoint = args["externalendpoint"]
        self._internal_endpoint = args["internalendpoint"]
        self._wf_next = args["fnext"]
        self._wf_pot_next = args["fpotnext"]
        self._function_runtime = args["fruntime"]

        # _XXX_: also includes the workflow end point (even though it is not an actual function)
        self._wf_function_list = args["workflowfunctionlist"]
        self._wf_exit = args["workflowexit"]

        self._is_session_workflow = False
        if args["sessionworkflow"]:
            self._is_session_workflow = True

        self._is_session_function = False
        if args["sessionfunction"]:
            self._is_session_function = True
        self._session_function_parameters = args["sessionfunctionparameters"]
        self._usertoken = os.environ["USERTOKEN"]

        self._should_checkpoint = args["shouldcheckpoint"]

    def _setup_loggers(self):
        global LOGGER_HOSTNAME
        global LOGGER_CONTAINERNAME
        global LOGGER_USERID
        global LOGGER_WORKFLOWNAME
        global LOGGER_WORKFLOWID

        LOGGER_HOSTNAME = self._hostname
        LOGGER_CONTAINERNAME = socket.gethostname()
        LOGGER_USERID = self._userid
        LOGGER_WORKFLOWNAME = self._workflowname
        LOGGER_WORKFLOWID = self._workflowid

        self._logger = logging.getLogger(self._function_state_name)
        self._logger.setLevel(logging.INFO)
        self._logger.addFilter(LoggingFilter())

        formatter = logging.Formatter("[%(timestamp)d] [%(levelname)s] [%(hostname)s] [%(containername)s] [%(uuid)s] [%(userid)s] [%(workflowname)s] [%(workflowid)s] [%(name)s] [%(asctime)s.%(msecs)03d] %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
        logfile = '/opt/mfn/logs/function_'+ self._function_state_name + '.log'

        hdlr = logging.FileHandler(logfile)
        hdlr.setLevel(logging.INFO)
        hdlr.setFormatter(formatter)
        self._logger.addHandler(hdlr)

        global print
        print = self._logger.info
        sys.stdout = MicroFunctionsLogWriter(self._logger, logging.INFO)
        sys.stderr = MicroFunctionsLogWriter(self._logger, logging.ERROR)

    #FOR_DEBUGGING_ONLY
    def _print_self(self):
        self._logger.debug("[self state]:")
        self._logger.debug("\tself._userid: %s", self._userid)
        self._logger.debug("\tself._storage_userid: %s", self._storage_userid)
        self._logger.debug("\tself._sandboxid: %s", self._sandboxid)
        self._logger.debug("\tself._workflowid: %s", self._workflowid)
        self._logger.debug("\tself._prefix: %s", self._prefix)
        self._logger.debug("\tself._function_folder: %s", self._function_folder)
        self._logger.debug("\tself._function_path: %s", self._function_path)
        self._logger.debug("\tself._function_name: %s", self._function_name)
        self._logger.debug("\tself._function_runtime: %s", str(self._function_runtime))
        self._logger.debug("\tself._function_state_type: %s", self._function_state_type)
        self._logger.debug("\tself._function_state_name: %s", self._function_state_name)
        self._logger.debug("\tself._function_state_info: %s", self._function_state_info)
        self._logger.debug("\tself._function_topic: %s", self._function_topic)
        self._logger.debug("\tself._hostname: %s", self._hostname)
        self._logger.debug("\tself._queue: %s", self._queue)
        self._logger.debug("\tself._datalayer: %s", self._datalayer)
        self._logger.debug("\tself._external_endpoint: %s", str(self._external_endpoint))
        self._logger.debug("\tself._internal_endpoint: %s", str(self._internal_endpoint))
        self._logger.debug("\tself._wf_next: %s", ",".join(self._wf_next))
        self._logger.debug("\tself._wf_pot_next: %s", ",".join(self._wf_pot_next))
        self._logger.debug("\tself._wf_function_list: %s", ",".join(self._wf_function_list))
        self._logger.debug("\tself._wf_exit: %s", self._wf_exit)
        self._logger.debug("\tself._wf_local: %s", ",".join(self._wf_local))
        self._logger.debug("\tself._is_session_workflow: %s", str(self._is_session_workflow))
        self._logger.debug("\tself._is_session_function: %s", str(self._is_session_function))
        self._logger.debug("\tself._session_function_parameters: %s", str(self._session_function_parameters))
        self._logger.debug("\tself._should_checkpoint: %s", str(self._should_checkpoint))
        self._logger.debug("\tself._usertoken: %s", str(self._usertoken))
    ####

    def _fork_and_handle_message(self, key, encapsulated_value):
        #self._logger.debug("[FunctionWorker] fork_and_handle_message, Before fork")
        try:
            # replace individual timestamps with a map
            timestamp_map = {}
            timestamp_map["t_start_fork"] = time.time() * 1000.0

            instance_pid = os.fork()

            if instance_pid == 0:
                global LOGGER_UUID
                LOGGER_UUID = key

                #self._print_self()  #FOR_DEBUGGING_ONLY
                #self._logger.debug("[FunctionWorker] fork_and_handle_message, After fork" + str(encapsulated_value))

                has_error = False
                error_type = ""

                timestamp_map["t_start_pubutils"] = time.time() * 1000.0
                # 0. Setup publication utils
                if not has_error:
                    try:
                        publication_utils = PublicationUtils(self._sandboxid, self._workflowid, self._function_topic, self._function_runtime, self._wf_next, self._wf_pot_next, self._wf_local, self._wf_function_list, self._wf_exit, self._should_checkpoint, self._state_utils, self._logger, self._queue, self._datalayer)
                    except Exception as exc:
                        self._logger.exception("PublicationUtils exception: %s\n%s", str(instance_pid), str(exc))
                        publication_utils = None
                        error_type = "PublicationUtils exception"
                        has_error = True

                # _XXX_: move the following check at the end of execution
                # there we have to have the output backups, so the initialization of data layer client
                # happens anyway.
                # if there was an error, we'll simply not publish the output to the next function
                # and stop the workflow execution there
                '''
                # check the workflow stop flag
                # if some other function execution had an error and we had been
                # simultaneously triggered, we don't need to continue execution
                timestamp_map["t_start_backdatalayer"] = time.time() * 1000.0
                if not has_error:
                    try:
                        dlc_backup = publication_utils.get_backup_data_layer_client()
                        timestamp_map["t_start_backdatalayer_r"] = time.time() * 1000.0
                        workflow_exec_stop = dlc_backup.get("workflow_execution_stop_" + key)
                        if workflow_exec_stop is not None and workflow_exec_stop != "":
                            self._logger.info("Not continuing because workflow execution has been stopped... %s", key)
                            publication_utils.shutdown_backup_data_layer_client()
                            os._exit(0)
                    except Exception as exc:
                        self._logger.exception("PublicationUtils data layer client exception: %s\n%s", str(instance_pid), str(exc))
                        publication_utils = None
                        error_type = "PublicationUtils data layer client exception"
                        has_error = True
                '''
                # Start of pre-processing

                # 1. Decapsulate the input.
                # The actual user input is encapsulated in a dict of the form {"__mfnuserdata": actual_user_input, "__mfnmetadata": mfn_specific_metadata}
                # This encapsulation is invisible to the user and is added, maintained, and removed by the hostagent and functionworker.
                #self._logger.debug("[FunctionWorker] Received encapsulated input:" + str(type(encapsulated_value)) + ":" + encapsulated_value)
                timestamp_map["t_start_decapsulate"] = time.time() * 1000.0
                if not has_error:
                    try:
                        value, metadata = publication_utils.decapsulate_input(encapsulated_value)
                        if "state_counter" not in metadata:
                            metadata["state_counter"] = 1
                        else:
                            metadata["state_counter"] += 1
                        #self._logger.debug("[FunctionWorker] fork_and_handle_message, metadata[state_counter]: " + str(metadata["state_counter"]))

                        #self._logger.debug("[FunctionWorker] Received state input:" + str(type(value)) + ":" + value)
                        #self._logger.debug("[FunctionWorker] Enclosed metadata:" + str(type(metadata)) + ":" + str(metadata))

                        # pass the metadata to the publication_utils, so that we can use it for sending immediate triggers
                        publication_utils.set_metadata(metadata)
                    except Exception as exc:
                        self._logger.exception("User input decapsulation error: %s\n%s", str(instance_pid), str(exc))
                        error_type = "User Input Decapsulation Error"
                        has_error = True

                timestamp_map["t_start_chdir"] = time.time() * 1000.0
                signal(SIGCHLD, SIG_DFL)
                if self._state_utils.isTaskState():
                    os.chdir(self._function_folder)

                # 2. Decode input. Input (value) must be a valid JSON Text.
                # Note: JSON Text is not the same as JSON string. JSON string a one variable type that can be contained inside a JSON Text.
                # Double quote delimited strings are valid JSON Texts, representing JSON strings. Examples below:
                # (variable 'value' refers is the input to fork_and_handle_message)
                #
                # value='abcdefghi'  is a python string, NOT a valid JSON Text (this will throw an error)
                #
                # value='"abcdefghi"' is a valid JSON Text representation of the string python 'abcdefghi'
                #   user code will receive <type 'str'> or <type 'unicode'> as input
                #
                # value='{"x":1}'  is a JSON Text representation of <type 'dict'>.
                #   user code will receive a <type 'dict'> as input
                timestamp_map["t_start_decodeinput"] = time.time() * 1000.0
                if not has_error:
                    try:
                        raw_state_input = publication_utils.decode_input(value)
                        #self._logger.debug("[FunctionWorker] Decoded state input:" + str(type(raw_state_input)) + ":" + str(raw_state_input))
                    except Exception as exc:
                        self._logger.exception("State Input Decoding exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "State Input Decoding exception"
                        has_error = True

                # 3. Apply InputPath, if available
                timestamp_map["t_start_inputpath"] = time.time() * 1000.0
                #self._logger.debug("[FunctionWorker] Before Path/Parameters processing, input: " + str(type(raw_state_input)) + " : " + str(raw_state_input) + ", metadata: " + str(metadata) + " has_error: " + str(has_error))
                if not has_error:
                    try:
                        if "__state_action" not in metadata or (metadata["__state_action"] != "post_map_processing" and metadata["__state_action"] != "post_parallel_processing"):
                             #self._logger.debug("[FunctionWorker] User code input(Before InputPath processing):" + str(type(raw_state_input)) + ":" + str(raw_state_input))
                             function_input = self._state_utils.applyInputPath(raw_state_input)
                             #self._logger.debug("[FunctionWorker] User code input(Before applyParameter processing):" + str(type(function_input)) + ":" + str(function_input))
                             function_input = self._state_utils.applyParameters(function_input)
                             #self._logger.debug("[FunctionWorker] User code input(Before ItemsPath processing):" + str(type(function_input)) + ":" + str(function_input))
                             function_input = self._state_utils.applyItemsPath(function_input) # process map items path

                        #elif "Action" not in metadata or metadata["Action"] != "post_parallel_processing":
                        #     function_input = self._state_utils.applyInputPath(raw_state_input)

                        else:
                             function_input = raw_state_input
                    except Exception as exc:
                        self._logger.exception("InputPath processing exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "InputPath processing exception"
                        has_error = True

                # Start of function setup (i.e., session utils, MicroFunctionsAPI)

                timestamp_map["t_start_sessutils"] = time.time() * 1000.0
                # 4. Setup session related stuff here if necessary
                session_utils = None
                if not has_error:
                    # set up session related stuff here, if this is a session workflow/function
                    # do this after fork(), so that we don't bottleneck the parent
                    # 1. a session id
                    # 2. a session function instance id
                    # TODO: 3. other metadata (e.g., direct data pipe endpoints)
                    # 4. health check mechanism (e.g., a thread in session_utils?)
                    # 5. Telemetry can be handled by the function instance writing to the data layer, or sending out a message immediately
                    # (see MicroFunctionsAPI.send_to_running_function_in_session() with send_now = True)
                    if self._is_session_workflow:
                        # set a given session id if it is present in the incoming event
                        # for all messages coming to a session
                        session_id = None
                        if "sessionId" in function_input and function_input["sessionId"] != "" and function_input["sessionId"] is not None:
                            session_id = function_input["sessionId"]
                        elif "session_id" in function_input and function_input["session_id"] != "" and function_input["session_id"] is not None:
                            session_id = function_input["session_id"]

                        session_utils = SessionUtils(self._hostname, self._userid, self._sandboxid, self._workflowid, self._logger, self._function_state_name, self._function_topic, key, session_id, publication_utils, self._queue, self._datalayer, self._internal_endpoint)

                        if self._is_session_function:
                            try:
                                session_utils.setup_session_function(self._session_function_parameters)
                            except Exception as exc:
                                self._logger.exception("Session function instantiation exception: %s\n%s", str(instance_pid), str(exc))
                                error_type = "sessionFunctionId error"
                                has_error = True

                timestamp_map["t_start_sapi"] = time.time() * 1000.0
                # 5. Setup the MicroFunctionsAPI object
                if not has_error:
                    try:
                        # pass the SessionUtils object for API calls to send a message to other running functions?
                        # MicroFunctionsAPI object checks before sending a message (i.e., allow only if this is_session_workflow is True)
                        # Maybe allow only if the destination is a session function? Requires a list of session functions and passing them to the MicroFunctionsAPI and SessionUtils
                        # Nonetheless, currently, MicroFunctionsAPI and SessionUtils write warning messages to the workflow log to indicate such problems
                        # (e.g., when this is not a workflow session or session function, when the destination running function instance does not exist)
                        sapi = MicroFunctionsAPI(self._storage_userid, self._sandboxid, self._workflowid, self._function_state_name, key, publication_utils, self._is_session_workflow, self._is_session_function, session_utils, self._logger, self._datalayer, self._external_endpoint, self._internal_endpoint, self._userid, self._usertoken)
                        # need this to retrieve and publish the in-memory, transient data (i.e., stored/deleted via is_queued = True)
                        publication_utils.set_sapi(sapi)
                    except Exception as exc:
                        self._logger.exception("MicroFunctionsAPI exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "MicroFunctionsAPI exception"
                        has_error = True

                timestamp_map["t_start"] = time.time() * 1000.0
                # todo add catch retry
                #a = self._state_utils.get_retry_data()
                #b = self._state_utils.get_catcher_data()
                #self._logger.debug("CatchRetry Data: " + json.dumps(self._state_utils.get_retry_data()))
                #self._logger.debug("CatchRetry Data2: " + str(type((self._state_utils.get_retry_data()))))
                #retrydata = self._state_utils.get_retry_data()

                # 6. Execute function
                if not has_error:
                    #self._logger.debug("[FunctionWorker] Before isTaskState, query: " + str(self._state_utils.isTaskState()))
                    if self._function_runtime == "python 3.6":
                        if self._state_utils.isTaskState() and self.code:
                            function_output = None
                            try:
                                # TODO: acknowledgement for session function instance creation
                                # if this is a session function, we'll keep running until the end of that function instance (e.g., session end)
                                # need a way to 'acknowledge' that the session function instance is running, so that the host agent also knows
                                # that the triggering message has indeed created a new instance
                                # if we do not send such acknowledgement, the host agent will keep thinking it has not been handled (e.g., after a restart)
                                # and will try to recreate the session function instance again (and again).
                                exec_arguments = {}
                                exec_arguments["function"] = self.code.handle
                                exec_arguments["function_input"] = function_input
                                function_output = self._state_utils.exec_function_catch_retry(self._function_runtime, exec_arguments, sapi)
                            except Exception as exc:
                                self._logger.exception("User code exception: %s\n%s", str(instance_pid), str(exc))
                                sys.stdout.flush()
                                error_type = "User code exception: " + str(exc.__class__.__name__)
                                has_error = True

                        else:
                            # Processing for Non 'Task' states
                            try:
                                self._logger.debug("[FunctionWorker] Before evaluateNonTaskState, input: " + str(function_input) + str(metadata))
                                #TODO: catch-retry for non-task functions?
                                function_output, metadata_updated = self._state_utils.evaluateNonTaskState(function_input, key, metadata, sapi)
                                metadata = metadata_updated
                                # update metadata in the publication utils
                                publication_utils.set_metadata(metadata)

                                #self._logger.debug("[FunctionWorker] After evaluateNonTaskState, result: " + str(function_output) + str(function_input))
                            except Exception as exc:
                                self._logger.exception("NonTaskState evaluation exception: %s\n%s", str(instance_pid), str(exc))
                                error_type = "NonTaskState evaluation exception"
                                has_error = True
                    elif self._function_runtime == "java":
                        exec_arguments = {}

                        api_uds = "/tmp/" + self._function_state_name + "_" + key + ".uds"

                        exec_arguments["api_uds"] = api_uds
                        exec_arguments["thriftAPIService"] = self._api_thrift.MicroFunctionsAPIService

                        # serialize the input to the java worker
                        java_input = {}
                        java_input["key"] = key
                        java_input["event"] = function_input
                        java_input["APIServerSocketFilename"] = api_uds

                        java_input = json.dumps(java_input)

                        exec_arguments["function_input"] = java_input

                        function_output = self._state_utils.exec_function_catch_retry(self._function_runtime, exec_arguments, sapi)

                timestamp_map["t_end"] = timestamp_map["t_start_resultpath"] = time.time() * 1000.0

                #self._logger.debug("[FunctionWorker] User code output:" + str(type(function_output)) + ":" + str(function_output))
                # Start of post-processing

                # 7. Apply ResultPath, if available
                if not has_error:
                    try:
                        raw_state_input_midway = self._state_utils.applyResultPath(raw_state_input, function_output)
                        #self._logger.debug("[FunctionWorker] After ResultPath processing:" + str(type(raw_state_input_midway)) + ":" + str(raw_state_input_midway))
                    except Exception as exc:
                        self._logger.exception("ResultPath processing exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "ResultPath processing exception"
                        has_error = True

                # 8. Apply OutputPath, if available
                timestamp_map["t_start_outputpath"] = time.time() * 1000.0
                if not has_error:
                    try:
                        raw_state_output = self._state_utils.applyOutputPath(raw_state_input_midway)
                        #self._logger.debug("[FunctionWorker] After OutputPath processing:" + str(type(raw_state_output)) + ":" + str(raw_state_output))
                    except Exception as exc:
                        self._logger.exception("OutputPath processing exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "OutputPath processing exception"
                        has_error = True

                # 9. Produce output string (value_output) from raw_state_output
                #   (Data sent to publish output should also be a JSON Text.)
                timestamp_map["t_start_encodeoutput"] = time.time() * 1000.0
                value_output = 'null'
                if not has_error:
                    try:
                        value_output = publication_utils.encode_output(raw_state_output)
                        #self._logger.debug("[FunctionWorker] Encoded state output:" + str(type(value_output)) + ":" + value_output)
                    except Exception as exc:
                        self._logger.exception("State Output Encoding exception: %s\n%s", str(instance_pid), str(exc))
                        error_type = "State Output Encoding exception"
                        has_error = True

                # 10. If current state is a terminal state inside a parallel branch then store output and decrement counter
                timestamp_map["t_start_branchterminal"] = time.time() * 1000.0
                if not has_error:
                    try:
                        self._state_utils.processBranchTerminalState(key, value_output, metadata, sapi) # not supposed to have a return value
                    except Exception as exc:
                        self._logger.exception("ProcessBranchTerminalState: %s\n%s", str(instance_pid), str(exc))
                        error_type = "ProcessBranchTerminalState exception"
                        has_error = True

                #self._logger.exception("Before publish, has_error: " + str(has_error))

                # Start of output publishing
                try:
                    # _XXX_: a potential race condition here with the session_utils helper thread
                    # if the long-running function finishes and publishes the output,
                    # the local queue client there is shut down at the end of the publishing
                    # but the helper thread may not still have exited its polling loop for session update messages
                    # hence may try to send another heartbeat message with the publication_utils local queue client

                    # need a way to sync the cleanup of the local queue client?
                    # 1. shutdown the helper thread before publishing
                    # 2. ensure in the helper thread no other heartbeat is published when it just exits the polling loop
                    if session_utils is not None and self._is_session_function:
                        session_utils.shutdown_helper_thread()

                    if publication_utils is not None:
                        publication_utils.publish_output_direct(key, value_output, has_error, error_type, timestamp_map)

                    # remove session function metadata from the session metadata tables if this is a session function
                    if session_utils is not None and self._is_session_function:
                        session_utils.cleanup()

                    os._exit(0)

                except Exception as exc:
                    self._logger.exception("Publication exception: %s\n%s", str(instance_pid), str(exc))
                    sys.stdout.flush()
                    os._exit(1)

            else:
                # parent
                # ignore children's exit signal, which allows the init to reap them
                # TODO: store child process ids, so that we can keep track of running instances
                # remove child process ids in the host agent, when the 'fin' message is received
                # store (key, pid) mapping to the data layer to keep track of function instances
                # TODO: maybe store this information in a forked process,
                # so that we don't bottleneck/fail the parent functionworker
                # TODO: need some component to remove the finished (key, instance_pid) tuples
                #self._logger.debug("[FunctionWorker] key: " + key + " -> " + str(instance_pid))
                #self._logger.debug("State Output instance PID: " + str(instance_pid) + str(has_error))
                #self.local_data_layer_client.putMapEntry(self._map_name_key_pid, key, str(instance_pid))
                pass

        except Exception as exc:
            if instance_pid == 0:
                self._logger.exception("Child exception: %s", str(exc))
                os._exit(1)
            else:
                self._logger.exception("Fork exception: %s", str(instance_pid))
                self._logger.exception(str(exc))
                sys.stdout.flush()

    def _process_update(self, value):
        try:
            update = json.loads(value)
            action = update["action"]

            #self._logger.debug("New update: %s", update)

            if action == "stop":
                self.shutdown()
            elif action == "update-local-functions":
                self._wf_local = update["localFunctions"]
        except Exception as exc:
            self._logger.error("Could not parse update message: %s; ignored...", str(exc))

    def _handle_message(self, lqm):
        try:
            lqcm = LocalQueueClientMessage(lqm=lqm)
            key = lqcm.get_key()
            value = lqcm.get_value()
            if key == "0l":
                self._process_update(value)
            else:
                self._fork_and_handle_message(key, value)
        except Exception as exc:
            self._logger.exception("Exception in handling: %s", str(exc))
            sys.stdout.flush()
            os._exit(1)

    def _get_and_handle_message(self):
        lqm = self.local_queue_client.getMessage(self._function_topic, self._POLL_TIMEOUT)
        if lqm is not None:
            self._handle_message(lqm)

    def run(self):
        self._is_running = True

        self._logger.info("[FunctionWorker] Started:" \
            + self._function_state_name \
            + ", user: " + self._userid \
            + ", workflow: " + self._workflowid \
            + ", sandbox: " + self._sandboxid \
            + ", pid: " + str(os.getpid()))

        while self._is_running:
            self._get_and_handle_message()

        self._logger.debug("[FunctionWorker] Waiting for child processes to finish:" \
            + self._function_state_name \
            + ", user: " + self._userid \
            + ", workflow: " + self._workflowid \
            + ", sandbox: " + self._sandboxid \
            + ", pid: " + str(os.getpid()))

        t = Timer(5, self.childWaitTimeout)
        t.start()
        self.wait_for_child_processes()
        t.cancel()

        self._logger.info("[FunctionWorker] Exit:" \
            + self._function_state_name \
            + ", user: " + self._userid \
            + ", workflow: " + self._workflowid \
            + ", sandbox: " + self._sandboxid \
            + ", pid: " + str(os.getpid()))

        self.local_queue_client.shutdown()

        self._logger.info("[FunctionWorker] Done")
        time.sleep(0.5)
        # shut down also the data layer client used for (key, pid) tuples
        #self.local_data_layer_client.shutdown()

    def childWaitTimeout(self):
        self._logger.info("[FunctionWorker] Force Exit:" \
            + self._function_state_name \
            + ", user: " + self._userid \
            + ", workflow: " + self._workflowid \
            + ", sandbox: " + self._sandboxid \
            + ", pid: " + str(os.getpid()))
        self.local_queue_client.shutdown()
        self._logger.info("[FunctionWorker] Done")
        time.sleep(0.5)
        os._exit(0)

    def runCmd(self, cmd):
        """
        This method runs a command and returns a list
        with the contents of its stdout and stderr and
        the exit code of the command.
        """
        try:
            args = shlex.split(cmd)
            child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            childStdoutBytes, childStderrBytes = child.communicate()
            return childStdoutBytes.decode().strip(), childStderrBytes.decode().strip(), child.returncode
        except Exception as e:
            self._logger.error('[FunctionWorker] runCmd:' + str(e))
            return '', '', -1

    def wait_for_child_processes(self):
        pid = os.getpid()
        out, err, retcode = self.runCmd('pgrep -P ' + str(pid))
        if retcode != 0:
            self._logger.error("[FunctionWorker] wait_for_child_processes: Failed to get children process ids")
            return

        children_pids = set(out.split())
        self._logger.debug("[FunctionWorker] wait_for_child_processes: Parent pid: " + str(pid) + "  Children_pid: " + str(children_pids))

        if len(children_pids) == 0:
            self._logger.debug("[FunctionWorker] wait_for_child_processes: No remaining pids to wait for")
            return

        while True:
            try:
                cpid, status = os.waitpid(-1, 0)
                self._logger.debug("[FunctionWorker] wait_for_child_processes: Status change for pid: " + str(cpid) + " Status: " + str(status))
                if str(cpid) not in children_pids:
                    #print('wait_for_child_processes: ' + str(cpid) + "Not found in children_pids")
                    continue
                children_pids.remove(str(cpid))
                if len(children_pids) == 0:
                    self._logger.debug("[FunctionWorker] wait_for_child_processes: No remaining pids to wait for")
                    break
            except Exception as e:
                self._logger.error('[FunctionWorker] wait_for_child_processes: ' + str(e))
                break

    def shutdown(self):
        self._logger.debug("[FunctionWorker] Shutdown command received:" \
            + self._function_state_name \
            + ", user: " + self._userid \
            + ", workflow: " + self._workflowid \
            + ", sandbox: " + self._sandboxid \
            + ", pid: " + str(os.getpid()))

        self._is_running = False

def main():
    params_filename = sys.argv[1]
    with open(params_filename, "r") as paramsf:
        params = json.load(paramsf)

    # create a thread with local queue consumer and subscription
    try:
        gw = FunctionWorker(params)
        gw.run()
    except Exception as exc:
        raise

if __name__ == '__main__':
    main()

