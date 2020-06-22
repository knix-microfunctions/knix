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

import ast
import copy
from datetime import datetime
import json
import socket
import time
import threading

import anytree

from thriftpy2.transport import TFramedTransportFactory, TServerSocket
from thriftpy2.protocol import TCompactProtocolFactory
from thriftpy2.server import TSimpleServer
from thriftpy2.thrift import TProcessor
from ujsonpath import parse, tokenize

import py3utils

from DataLayerClient import DataLayerClient

class StateUtils:

    defaultStateType = 'Task_SAND'
    taskStateType = 'Task'
    choiceStateType = 'Choice'
    passStateType = 'Pass'
    succeedStateType = 'Succeed'
    failStateType = 'Fail'
    waitStateType = 'Wait'
    parallelStateType = 'Parallel'
    mapStateType = 'Map'
    _instcnt = 0  # instance counter
    mapFunctionOutput =  {}

    def __init__(self, functionstatetype=defaultStateType, functionstatename='', functionstateinfo='{}', functionruntime="", logger=None, workflowid=None, sandboxid=None, functiontopic=None, datalayer=None, storage_userid=None, internal_endpoint=None):
        self.operators = ['And', 'BooleanEquals', 'Not', 'NumericEquals', 'NumericGreaterThan', 'NumericGreaterThanEquals',\
             'NumericLessThan', 'NumericLessThanEquals', 'Or', 'StringEquals', 'StringGreaterThan',\
             'StringGreaterThanEquals', 'StringLessThan', 'StringLessThanEquals', 'TimestampEquals', 'TimestampGreaterThan',\
         'TimestampGreaterThanEquals', 'TimestampLessThan', 'TimestampLessThanEquals']

        self.operators_python = ['and', '==', 'not', '==', '>', '>=', '<', '<=', 'or', '==', '>', '>=', '<', '<=', '==', '>', '>=', '<', '<=']

        self.operators_set = set(self.operators)
        self.asl_errors = ("States.ALL", "States.Timeout", "States.TaskFailed", "States.Permissions", "States.ResultPathMatchFailure", "States.BranchFailed", "States.NoChoiceMatched")

        self.nodelist = []
        self.parsed_trees = []

        self.default_next_choice = []

        self.input_path_dict = {}
        self.items_path_dict = {}
        self.result_path_dict = {}
        self.output_path_dict = {}
        self.parameters_dict = {}
        self.functionstatetype = functionstatetype
        self.functionstatename = functionstatename
        self.functionstateinfo = functionstateinfo
        self.functiontopic = functiontopic
        self._datalayer = datalayer
        self._storage_userid = storage_userid
        self._internal_endpoint = internal_endpoint
        self._function_runtime = functionruntime
        if self._function_runtime == "java":
            # if java, this is the address we'll send requests to be handled
            self._java_handler_address = "/tmp/java_handler_" + self.functionstatename + ".uds"

        self.parsedfunctionstateinfo = {}
        self.workflowid = workflowid
        self.sandboxid = sandboxid
        self.choiceNext = ''

        self.mapStateCounter = 0
        #self._mapStateInfo = {}
        #self.batchAlreadyLaunched = []
        #self.currentMapInputMetadata = {} # initialise with empty dicts
        self.evaluateCounter = 0

        self.catcher_list = []
        self.retry_list = []

        self._logger = logger
        self.parse_function_state_info()
        self.function_output_batch_list = []
        self.tobeProcessedlater = []
        self.outputMapStatebatch = []
        self.mapPartialResult = {}

    def call_counter(func):
        def helper(*args, **kwargs):
            helper.calls += 1
            return func(*args, **kwargs)
        helper.calls = 0
        helper.__name__= func.__name__
        return helper

    # find target next for error in catcher list
    def find_cat_data(self, err, cat_list):
        cat_result = "$" # default
        cat_next = [] # default
        for cat in cat_list:
            if "ErrorEquals" in cat and (str(err) in cat["ErrorEquals"] or err.__class__.__name__ in cat["ErrorEquals"]):
                cat_next = cat['Next']
                if "ResultPath" in cat:
                    cat_result = cat['ResultPath']
        return cat_next, cat_result

    def find_ret_data(self, err, ret_list):
        ret_max_attempts = 1 # default
        ret_interval_seconds = 1 # default
        ret_backoff_rate = 1.0 #  default
        for ret in ret_list:
            if err in ret['ErrorEquals'] or err.__class__.__name__ in ret['ErrorEquals']:
                if "MaxAttempts" in list(ret.keys()):
                    ret_max_attempts = ret['MaxAttempts']
                if "IntervalSeconds" in list(ret.keys()):
                    ret_interval_seconds = ret['IntervalSeconds']
                if "BackoffRate" in list(ret.keys()):
                    ret_backoff_rate = ret['BackoffRate']
        return ret_max_attempts, ret_interval_seconds, ret_backoff_rate

    def isMapState(self):
        return self.functionstatetype == StateUtils.mapStateType

    def isTaskState(self):
        return self.functionstatetype == StateUtils.taskStateType or self.functionstatetype == StateUtils.defaultStateType
    def applyParameters(self, raw_state_input):
        #2c. Apply Parameters, if available and applicable (The Parameters field is used in Map to select values in the input)
        #       in = raw_state_input
        #       if Parameters:
        #           in = raw_state_input[ItemsPath]
        #
        try:
            function_input = raw_state_input
            self._logger.debug("inside applyParameters: " + str(self.parameters_dict) + ", raw_state_input: " + str(raw_state_input))
            if self.parameters_dict:
                function_input = self.process_parameters(self.parameters_dict, function_input)
            return function_input
        except Exception:
            raise Exception("Parameters processing exception")

    def applyItemsPath(self, raw_state_input):
        #2a. Apply ItemsPath, if available and applicable (The ItemsPath field is used in Map to select an array in the input)
        #       in = raw_state_input
        #       if ItemsPath:
        #           in = raw_state_input[ItemsPath]
        #
        try:
            function_input = raw_state_input
            if self.items_path_dict and 'ItemsPath' in self.items_path_dict:
                function_input = self.process_items_path(self.items_path_dict, function_input)
            return function_input
        except Exception:
            raise Exception("Items path processing exception")


    def applyInputPath(self, raw_state_input):
        #2. Apply InputPath, if available (Extract function_input from raw_state_input)
        #       in = raw_state_input
        #       if InputPath:
        #           in = raw_state_input[InputPath]
        #
        try:
            #self._logger.debug("Current Function Type: " + self.functionstatetype)
            #self._logger.debug("StateUtils: Input Path Dict: " + json.dumps(self.input_path_dict))

            function_input = raw_state_input
            if self.input_path_dict and 'InputPath' in self.input_path_dict:
                #t_start = time.time()
                function_input = self.process_input_path(self.input_path_dict, function_input)
                #t_end = time.time()
                #timestr = "%.15f" % ((t_end-t_start)*1.0E9)
                #self._logger.debug("Input Path Processing Time (ns): " + timestr)
            #self._logger.debug("StateUtils: Processed Value: " + json.dumps(function_input))
            return function_input
        except Exception:
            #self._logger.exception("Input path processing exception")
            #sys.stdout.flush()
            #os._exit(1)
            raise Exception("Input path processing exception")

    # send a request to the java worker and get the result
    def _send_java_request(self, java_input, java_output, api_server, server_socket):
        # get a connection to the java worker
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # send the request
        max_num_tries = 10
        num_tries = 0
        trying = True
        has_error = False
        while trying:
            try:
                sock.connect(self._java_handler_address)
                trying = False
            except socket.error as msg:
                num_tries += 1
                if num_tries > max_num_tries:
                    self._logger.debug("cannot open connection to java worker: %s", msg)
                    trying = False
                    has_error = True
                else:
                    self._logger.debug("will retry connection to java worker...")
                    time.sleep(0.05*num_tries)

        if not has_error:
            try:
                sock.sendall(java_input.encode())
                sock.shutdown(socket.SHUT_WR)

                # receive the response
                chunks = []
                while True:
                    data = sock.recv(4096)
                    if not data:
                        sock.close()
                        break
                    chunks.append(data.decode())

                output_data = "".join(chunks)

                self._logger.debug("received output_data: " + output_data)

                output_data = json.loads(output_data)

                if not output_data["hasError"]:
                    java_output["functionResult"] = output_data["functionResult"]
                    java_output["hasError"] = False
                    java_output["errorType"] = ""
                    java_output["errorTrace"] = ""
                else:
                    java_output["hasError"] = output_data["hasError"]
                    java_output["errorType"] = output_data["errorType"]
                    java_output["errorTrace"] = output_data["errorTrace"]

                # close the api server in the main thread, so that we can continue with publishing the output
                api_server.close()
                server_socket.close()
            except socket.error as msg:
                self._logger.debug("cannot send request to java worker: %s", msg)
                #os._exit(1)

    def _exec_function(self, runtime, exec_arguments, sapi):
        if runtime == "python 3.6":
            func = exec_arguments["function"]
            args = exec_arguments["function_input"]
            function_output = func(args, sapi)

        elif runtime == "java":
            # open the API server for this request
            api_uds = exec_arguments["api_uds"]
            thriftAPIService = exec_arguments["thriftAPIService"]
            java_input = exec_arguments["function_input"]

            processor = TProcessor(thriftAPIService, sapi)
            server_socket = TServerSocket(unix_socket=api_uds)
            # no need for any other type of server; there will only be a single client: the java function instance
            api_server = TSimpleServer(processor, server_socket,
                                       iprot_factory=TCompactProtocolFactory(),
                                       itrans_factory=TFramedTransportFactory())

            self._logger.debug("API server at: " + api_uds)
            self._logger.debug("starting with java_input: " + java_input)

            # access to the output for the thread via an object
            java_output = {}
            # send it to the java worker in a thread
            # (thread has access to api_server object and server_socket to stop it)
            # (thread has also access to the output to set it in the main thread of execution)
            try:
                t = threading.Thread(target=self._send_java_request, args=(java_input, java_output, api_server, server_socket,))
                t.start()
            except Exception as exc:
                pass

            # meanwhile, the main thread listens and serves API requests
            # when the execution is finished, the api server will be stopped
            try:
                self._logger.debug("API server serving...")
                api_server.serve()
            except Exception as exc:
                #raise exc
                pass

            # when the java worker function returns, it stops the API server and sets the output that was produced
            # get the output
            has_error = java_output["hasError"]
            error_type = java_output["errorType"]
            error_trace = java_output["errorTrace"]
            if not has_error:
                function_output = java_output["functionResult"]
            else:
                raise Exception(error_type)

        return function_output

    #@retry(ZeroDivisionError, tries=10, delay=1) # ToDo: parse parameters of of retryers and catchers
    #@retry([x[0] for x in self.asl_errors], tries=3, delay=2) # ToDo: parse parameters of of retryers and catchers
    #@retry("States.ALL", tries=3, delay=2)
    def exec_function_catch_retry(self, runtime, exec_arguments, sapi):
        retryer = self.retry_list
        catcher = self.catcher_list
        ret_error_list = []
        ret_interval_seconds = 0
        ret_backoff_rate = 0
        ret_max_attempts = 0
        cat_next = ""
        ret_value = []

        for ret in retryer:
            ret_error_list = ret['ErrorEquals']

            self._logger.debug("[StateUtils] found a ASL workflow retryer, retry for: " + str(ret_error_list))
            try:
                ret_value = self._exec_function(runtime, exec_arguments, sapi)
                return ret_value
            except Exception as exc:
                self._logger.debug("[StateUtils] retryer just caught an error: " + ", " + str(exc) + ", " + str(exc.__class__.__name__) + ", " + str(retryer))
                ret_max_attempts, ret_interval_seconds, ret_backoff_rate = self.find_ret_data(exc, retryer) # get the retry data for this error
                delay = int(ret_interval_seconds)
                max_attempts = int(ret_max_attempts)
                backoff_rate = float(ret_backoff_rate)

                # start retrying on this error
                while max_attempts:
                    try:
                        ret_value = self._exec_function(runtime, exec_arguments, sapi)
                        return ret_value
                    except Exception as e_retry:
                        if (any(str(e_retry) in s0 for s0 in ret_error_list) or any(e_retry.__class__.__name__ in s1 for s1 in ret_error_list)):
                            self._logger.debug("[StateUtils] MFn ASL retryer just caught an error:" + str(e_retry) + str(retryer))
                            self._logger.debug("[StateUtils] retrying for Error: " + str(e_retry) + ", remaining attempts: " + str(max_attempts))
                    max_attempts -= 1
                if not max_attempts:
                    ret_value = {"Error": str(exc), "Cause": "Error not caught by MFn ASL Workflow retryer"}
                    self._logger.error("[StateUtils] Error not caught by MFn ASL Workflow retryer!")
                    return ret_value
                    #raise # max retries have been reached

            self._logger.warning('%s, retrying in %s seconds... ' % (e_retry, str(delay)))
            time.sleep(delay)
            delay *= backoff_rate

        if catcher:
            self._logger.debug("[StateUtils] found a ASL workflow catcher")
            # there was no retry information provided for this function, proceed with catch
            ret_value = {"Error": "Catcher", "Cause": "error caught by MFn ASL Workflow catcher"}
            try:
                ret_value = self._exec_function(runtime, exec_arguments, sapi)
                return ret_value
            except Exception as exc:
                exc_msg = str(exc)
                self._logger.error("[StateUtils] catcher just caught an error: " + exc_msg + " " + str(catcher))
                cat_next, cat_result = self.find_cat_data(exc, catcher)
                if cat_next != []:
                    self._logger.error("[StateUtils] matching catch list entry target and result for this error: " + str(cat_next) + " " + str(cat_result))
                    self.result_path_dict['ResultPath'] = cat_result
                    ret_value = {"Error": exc_msg, "Cause": "this error caught by MFn ASL Workflow catcher!"}
                    if runtime == "java":
                        # do an extra serialization, because we were expecting a java output,
                        # but got a python object
                        val = {}
                        val["value"] = exc_msg
                        exc_msg = json.dumps(val)
                    sapi.add_dynamic_next(cat_next, exc_msg)
                    return ret_value
                else: # no catcher could be found for this error
                    self._logger.error("[StateUtils] Error not caught by MFn ASL Workflow catcher!")
                    raise exc

        else: # neither catcher nor retryers are set
            ret_value = self._exec_function(runtime, exec_arguments, sapi)
            return ret_value

    def getChoiceResults(self, value_output):
        choice_next_list = []
        #self._logger.debug("[StateUtils] getChoiceResults Inputs: " + str(self.choiceNext) + str(self.functionstatetype))
        if self.functionstatetype == self.choiceStateType and self.choiceNext != '':
            choice_next_list.append({"next": self.choiceNext, "value": value_output})
        return choice_next_list

    def evaluateChoiceConditions(self, function_input):
        self.choiceNext = ''
        self.choiceNext = self.evaluateNextState(function_input)
        self._logger.debug("[StateUtils] Evaluated Choice condition: " + str(self.choiceNext))


    def evaluateMapState(self, function_input, key, metadata, sapi):
        name_prefix = self.functiontopic + "_" + key

        if "MaxConcurrency" in self.parsedfunctionstateinfo:
            maxConcurrency = self.parsedfunctionstateinfo["MaxConcurrency"]
        else:
            maxConcurrency = 0
            self.parsedfunctionstateinfo["MaxConcurrency"] = maxConcurrency

        if "Parameters" in self.parsedfunctionstateinfo:
            mapParamters = self.parsedfunctionstateinfo["Parameters"]
        else:
            mapParameters = {}

        self._logger.debug("[StateUtils] evaluateMapState, maxConcurrency: " + str(maxConcurrency))

        self._logger.debug("[StateUtils] evaluateMapState metadata: " + str(metadata))

        counter_name_topic = self.sandboxid + "-" + self.workflowid + "-" + self.functionstatename

        total_branch_count = len(function_input) # all branches executed concurrently

        klist = [total_branch_count]

        self.parsedfunctionstateinfo["BranchCount"] = int(total_branch_count) # overwrite parsed BranchCount with new value
        self._logger.debug("[StateUtils] evaluateMapState, total_branch_count: " + str(total_branch_count))

        # translated from Parallel
        counter_metadata = {}
        counter_metadata["__state_action"] = "post_map_processing"
        counter_metadata["__async_execution"] = metadata["__async_execution"]
        workflow_instance_metadata_storage_key = name_prefix + "_workflow_metadata"
        counter_metadata["WorkflowInstanceMetadataStorageKey"] = workflow_instance_metadata_storage_key
        counter_metadata["CounterValue"] = 0 # this should be updated by riak hook
        counter_metadata["Klist"] = klist
        counter_metadata["TotalBranches"] = total_branch_count
        counter_metadata["ExecutionId"] = key
        counter_metadata["FunctionTopic"] = self.functiontopic
        counter_metadata["Endpoint"] = self._internal_endpoint

        iterator = self.parsedfunctionstateinfo["Iterator"]

        #assert total_branch_count == len(self.parsedfunctionstateinfo["Branches"])

        k_list = [total_branch_count]

        counter_name_trigger_metadata = {"k-list": k_list, "total-branches": total_branch_count}

        # dynamic values used for generation of branches
        counter_name_key = key
        branch_out_keys = []
        for i in range(total_branch_count):
            branch_out_key = key + "-branch-" + str(i+1)
            branch_out_keys.append(branch_out_key)

        counter_name_value_metadata = copy.deepcopy(metadata)
        counter_name_value_metadata["WorkflowInstanceMetadataStorageKey"] = workflow_instance_metadata_storage_key
        counter_name_value_metadata["CounterValue"] = 0 # this should be updated by riak hook
        counter_name_value_metadata["__state_action"] = "post_map_processing"
        counter_name_value_metadata["state_counter"] = metadata["state_counter"]
        self._logger.debug("[StateUtils] evaluateMapState, metadata[state_counter]: " + str(metadata["state_counter"]))
        self.mapStateCounter = int(metadata["state_counter"])

        counter_name_value = {"__mfnmetadata": counter_name_value_metadata, "__mfnuserdata": '{}'}

        CounterName = json.dumps([str(counter_name_topic), str(counter_name_key), counter_name_trigger_metadata, counter_name_value])

        workflow_instance_outputkeys_set_key = key +"_"+ self.functionstatename + "_outputkeys_set"
        mapInfo = {}
        mapInfo["CounterTopicName"] = counter_name_topic
        mapInfo["CounterNameKey"] = counter_name_key
        mapInfo["TriggerMetadata"] = counter_name_trigger_metadata
        mapInfo["CounterNameValueMetadata"] = counter_name_value_metadata
        mapInfo["BranchOutputKeys"] = branch_out_keys
        mapInfo["CounterName"] = CounterName
        mapInfo["MaxConcurrency"] = maxConcurrency
        mapInfo["BranchOutputKeysSetKey"] = workflow_instance_outputkeys_set_key
        mapInfo["k_list"] = k_list

        mapInfo_key = self.functionstatename + "_" + key  + "_map_info"

        metadata[mapInfo_key] = mapInfo

        self._logger.debug("[StateUtils] evaluateMapState: ")
        self._logger.debug("\t CounterName:" + CounterName)
        self._logger.debug("\t counter_name_topic:" + counter_name_topic)
        self._logger.debug("\t counter_name_key: " + counter_name_key)
        self._logger.debug("\t counter_name_trigger_metadata:" + json.dumps(counter_name_trigger_metadata))
        self._logger.debug("\t counter_name_value_metadata:" + json.dumps(counter_name_value_metadata))
        self._logger.debug("\t counter_name_value_encoded: " + json.dumps(counter_name_value))
        self._logger.debug("\t mapInfo_key:" + mapInfo_key)
        #self._logger.debug("\t mapInfo:" + json.dumps(mapInfo))
        self._logger.debug("\t workflow_instance_metadata_storage_key: " + workflow_instance_metadata_storage_key)
        #self._logger.debug("\t metadata " + json.dumps(metadata))
        self._logger.debug("\t total_branch_count:" + str(total_branch_count))
        self._logger.debug("\t branch_out_keys:" + ",".join(branch_out_keys))

        # create counter for Map equivalent Parallel state
        assert py3utils.is_string(CounterName)
        counterName = str(mapInfo["CounterName"])
        counter_metadata_key_name = counterName + "_metadata"

        try:
            dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

            # create a triggerable counter to start the post-parallel when parallel state finishes
            dlc.createCounter(CounterName, 0, tableName=dlc.countertriggerstable)

            dlc.put(counter_metadata_key_name, json.dumps(counter_metadata), tableName=dlc.countertriggersinfotable)

        except Exception as exc:
            self._logger.error("Exception in creating counter: " + str(exc))
            self._logger.error(exc)
            raise
        finally:
            dlc.shutdown()


        assert py3utils.is_string(workflow_instance_metadata_storage_key)
        self._logger.debug("[StateUtils] full_metadata_encoded put key: " + str(workflow_instance_metadata_storage_key))

        sapi.put(workflow_instance_metadata_storage_key, json.dumps(metadata))

        #assert py3utils.is_string(workflow_instance_outputkeys_set_key)
        # sapi.createSet(workflow_instance_outputkeys_set_key) # obsolete statement


        # Now provide each branch with its own input

        #branches = self.parsedfunctionstateinfo["Branches"]
        branch = self.parsedfunctionstateinfo["Iterator"] # this is just onee set
        #for branch in branches:
        # lauch a branch for each input element
        startat = str(branch["StartAt"])


        for i in range(len(function_input)):
            sapi.add_dynamic_next(startat, function_input[i]) # Alias for add_workflow_next(self, next, value)

            sapi.put(name_prefix + "_" + "mapStateInputValue", str(function_input[i]))
            sapi.put(name_prefix + "_" + "mapStateInputIndex", str(i))

            #self._mapStateInfo["mapStateInputValue"] = str(function_input[i])
            #self._mapStateInfo["mapStateInputIndex"] = str(i)

            self._logger.debug("\t Map State StartAt:" + startat)
            self._logger.debug("\t Map State input:" + str(function_input[i]))

        return function_input, metadata

    def evaluatePostMap(self, function_input, key, metadata, sapi):

        name_prefix = self.functiontopic + "_" + key

        # function is triggered by post-commit hook with metadata containing information abaout state results in buckets.
        # It collects these results and returns metadata and post_map_output_results

        #self._logger.debug("[StateUtils] evaluatePostMap: ")
        #self._logger.debug("\t key:" + key)
        #self._logger.debug("\t metadata:" + json.dumps(metadata))
        #self._logger.debug("\t function_input: " + str(function_input))

        action = metadata["__state_action"]
        assert action == "post_map_processing"
        #counterValue = metadata["CounterValue"]
        counterValue = function_input["CounterValue"]

        state_counter = 0
        if "state_counter" in metadata:
            state_counter = metadata["state_counter"]

        #self._logger.debug("[StateUtils] evaluatePostMap, metadata[state_counter]: " + str(metadata["state_counter"]))

        self._logger.debug("\t metadata:" + json.dumps(metadata))

        workflow_instance_metadata_storage_key = str(function_input["WorkflowInstanceMetadataStorageKey"])
        assert py3utils.is_string(workflow_instance_metadata_storage_key)
        full_metadata_encoded = sapi.get(workflow_instance_metadata_storage_key)
        self._logger.debug("[StateUtils] full_metadata_encoded get: " + str(full_metadata_encoded))

        full_metadata = json.loads(full_metadata_encoded)
        full_metadata["state_counter"] = state_counter

        #mapInfoKey = key + "_" + self.functionstatename + "_map_info"
        mapInfoKey = self.functionstatename + "_" + key  + "_map_info"
        mapInfo = full_metadata[mapInfoKey]

        branchOutputKeysSetKey = str(mapInfo["BranchOutputKeysSetKey"])
        branchOutputKeysSet = sapi.retrieveSet(branchOutputKeysSetKey)
        self._logger.debug("\t branchOutputKeysSet: " + str(branchOutputKeysSet))

        if not branchOutputKeysSet:
            self._logger.error("[StateUtils] branchOutputKeysSet is empty")
            raise Exception("[StateUtils] branchOutputKeysSet is empty")

        k_list = mapInfo["k_list"]

        self._logger.debug("\t action: " + action)
        self._logger.debug("\t counterValue:" + str(counterValue))
        #self._logger.debug("\t WorkflowInstanceMetadataStorageKey:" + metadata["WorkflowInstanceMetadataStorageKey"])
        #self._logger.debug("\t full_metadata:" + full_metadata_encoded)
        self._logger.debug("\t mapInfoKey: " + mapInfoKey)
        #self._logger.debug("\t mapInfo:" + json.dumps(mapInfo))
        self._logger.debug("\t branchOutputKeysSetKey:" + branchOutputKeysSetKey)
        self._logger.debug("\t branchOutputKeysSet:" + str(branchOutputKeysSet))
        self._logger.debug("\t k_list:" + str(k_list))

        NumBranchesFinished = abs(counterValue)
        self._logger.debug("\t NumBranchesFinished:" + str(NumBranchesFinished))

        do_cleanup = False

        if k_list[-1] == NumBranchesFinished:
            do_cleanup = True

        self._logger.debug("\t do_cleanup:" + str(do_cleanup))

        counterName = str(mapInfo["CounterName"])
        counter_metadata_key_name = counterName + "_metadata"
        assert py3utils.is_string(counterName)

        if do_cleanup:
            assert py3utils.is_string(counterName)
            try:
                dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

                # done with the triggerable counter
                dlc.deleteCounter(counterName, tableName=dlc.countertriggerstable)

                dlc.delete(counter_metadata_key_name, tableName=dlc.countertriggersinfotable)

            except Exception as exc:
                self._logger.error("Exception deleting counter: " + str(exc))
                self._logger.error(exc)
                raise
            finally:
                dlc.shutdown()

        post_map_output_values = []

        self._logger.debug("\t mapInfo_BranchOutputKeys:" + str(mapInfo["BranchOutputKeys"]))

        self._logger.debug("\t mapInfo_BranchOutputKeys length: " + str(len(mapInfo["BranchOutputKeys"])))

        for outputkey in mapInfo["BranchOutputKeys"]:
            outputkey = str(outputkey)
            if outputkey in branchOutputKeysSet: # mapInfo["BranchOutputKeys"]:
                self._logger.debug("\t BranchOutputKey:" + outputkey)
                while sapi.get(outputkey) == "":
                    time.sleep(0.1) # wait until value is available

                branchOutput = sapi.get(outputkey)
                branchOutput_decoded = json.loads(branchOutput)
                self._logger.debug("\t branchOutput(type):" + str(type(branchOutput)))
                self._logger.debug("\t branchOutput:" + branchOutput)
                self._logger.debug("\t branchOutput_decoded(type):" + str(type(branchOutput_decoded)))
                self._logger.debug("\t branchOutput_decoded:" + str(branchOutput_decoded))
                post_map_output_values = post_map_output_values + [branchOutput_decoded]
                if do_cleanup:
                    sapi.delete(outputkey) # cleanup the key from data layer
                    self._logger.debug("\t cleaned output key:" + outputkey)
            else:
                post_map_output_values = post_map_output_values + [None]
                self._logger.debug("\t this_BranchOutputKeys is not contained: " + str(outputkey))

        self._logger.debug("\t post_map_output_values:" + str(post_map_output_values))
        while (sapi.get(name_prefix + "_" + "mapStatePartialResult")) == "":
            time.sleep(0.1) # wait until value is available

        mapStatePartialResult = ast.literal_eval(sapi.get(name_prefix + "_" + "mapStatePartialResult"))
        #mapStatePartialResult = ast.literal_eval(self._mapStateInfo["mapStatePartialResult"])

        mapStatePartialResult += post_map_output_values
        sapi.put(name_prefix + "_" + "mapStatePartialResult", str(mapStatePartialResult))
        #self._mapStateInfo["mapStatePartialResult"] = str(mapStatePartialResult)

        # now apply ResultPath and OutputPath
        if do_cleanup:

            sapi.deleteSet(branchOutputKeysSetKey)

        if ast.literal_eval(sapi.get(name_prefix + "_" + "mapInputCount")) == len(mapStatePartialResult):
        # if ast.literal_eval(self._mapStateInfo["mapInputCount"]) == len(mapStatePartialResult):

            # we are ready to publish  but need to honour ResultPath and OutputPath
            res_raw = ast.literal_eval(sapi.get(name_prefix + "_" +"mapStatePartialResult"))
            #res_raw = ast.literal_eval(self._mapStateInfo["mapStatePartialResult"])

            # remove unwanted keys from input before publishing
            function_input = {}

            function_input_post_result = self.applyResultPath(function_input, res_raw)
            function_input_post_output = self.applyResultPath(function_input_post_result, function_input_post_result)
            if "Next" in self.parsedfunctionstateinfo:
                if self.parsedfunctionstateinfo["Next"]:
                    sapi.add_dynamic_next(self.parsedfunctionstateinfo["Next"], function_input_post_output )

            if "End" in self.parsedfunctionstateinfo:
                if self.parsedfunctionstateinfo["End"]:
                    sapi.add_dynamic_next("end", function_input_post_output)
            sapi.delete(name_prefix + "_" + "mapInputCount")
            sapi.delete(name_prefix + "_" + "mapStateInputIndex")
            sapi.delete(name_prefix + "_" + "mapStateInputValue")
            sapi.delete(name_prefix + "_" + "mapStatePartialResult")
            sapi.delete(name_prefix + "_" + "tobeProcessedlater")
            post_map_output_values = function_input_post_output
        return post_map_output_values, full_metadata

    def evaluateParallelState(self, function_input, key, metadata, sapi):
        name_prefix = self.functiontopic + "_" + key
        total_branch_count = self.parsedfunctionstateinfo["BranchCount"]
        assert total_branch_count == len(self.parsedfunctionstateinfo["Branches"])

        klist = [total_branch_count]

        # dynamic values
        branch_out_keys = []
        for i in range(total_branch_count):
            branch_out_key = name_prefix + "_branch_" + str(i+1)
            branch_out_keys.append(branch_out_key)

        counter_metadata = {}
        counter_metadata["__state_action"] = "post_parallel_processing"
        counter_metadata["__async_execution"] = metadata["__async_execution"]
        workflow_instance_metadata_storage_key = name_prefix + "_workflow_metadata"
        counter_metadata["WorkflowInstanceMetadataStorageKey"] = workflow_instance_metadata_storage_key
        counter_metadata["CounterValue"] = 0 # this should be updated by riak hook
        counter_metadata["Klist"] = klist
        counter_metadata["TotalBranches"] = total_branch_count
        counter_metadata["ExecutionId"] = key
        counter_metadata["FunctionTopic"] = self.functiontopic
        counter_metadata["Endpoint"] = self._internal_endpoint

        CounterName = name_prefix + "_counter"
        counter_metadata_key_name = CounterName + "_metadata"
        workflow_instance_outputkeys_set_key = name_prefix + "_outputkeys_set"

        parallelInfo = {}
        parallelInfo["CounterName"] = CounterName
        parallelInfo["BranchOutputKeys"] = branch_out_keys
        parallelInfo["BranchOutputKeysSetKey"] = workflow_instance_outputkeys_set_key
        parallelInfo["Klist"] = klist
        parallelInfo["TotalBranches"] = total_branch_count
        parallelInfo["ExecutionId"] = key
        parallelInfo["FunctionTopic"] = self.functiontopic
        parallelInfo["Endpoint"] = self._internal_endpoint

        parallelInfo_key = self.functionstatename + "_" + key + "_parallel_info"
        metadata[parallelInfo_key] = parallelInfo

        #self._logger.debug("[StateUtils] evaluateParallelState: ")
        #self._logger.debug("\t CounterName:" + CounterName)
        #self._logger.debug("\t CounterMetadata: " + json.dumps(counter_metadata))
        #self._logger.debug("\t parallelInfo_key:" + parallelInfo_key)
        #self._logger.debug("\t parallelInfo:" + json.dumps(parallelInfo))
        #self._logger.debug("\t total_branch_count:" + str(total_branch_count))
        #self._logger.debug("\t branch_out_keys:" + ",".join(branch_out_keys))

        assert py3utils.is_string(CounterName)
        try:
            dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

            # create a triggerable counter to start the post-parallel when parallel state finishes
            dlc.createCounter(CounterName, 0, tableName=dlc.countertriggerstable)

            dlc.put(counter_metadata_key_name, json.dumps(counter_metadata), tableName=dlc.countertriggersinfotable)

        except Exception as exc:
            self._logger.error("Exception in creating counter: " + str(exc))
            self._logger.error(exc)
            raise
        finally:
            dlc.shutdown()

        assert py3utils.is_string(workflow_instance_metadata_storage_key)
        sapi.put(workflow_instance_metadata_storage_key, json.dumps(metadata))

        assert py3utils.is_string(workflow_instance_outputkeys_set_key)
        sapi.createSet(workflow_instance_outputkeys_set_key)

        branches = self.parsedfunctionstateinfo["Branches"]
        for branch in branches:
            startat = str(branch["StartAt"])
            sapi.add_dynamic_next(startat, function_input)
            #self._logger.debug("\t Branch StartAt:" + startat)
            #self._logger.debug("\t Branch input:" + str(function_input))

        return function_input, metadata


    def processBranchTerminalState(self, key, value_output, metadata, sapi):
        if 'End' not in self.parsedfunctionstateinfo:
            return
        if self.parsedfunctionstateinfo["End"] and "ParentParallelInfo" in self.parsedfunctionstateinfo:
            parentParallelInfo = self.parsedfunctionstateinfo["ParentParallelInfo"]
            parallelName = parentParallelInfo["Name"]
            branchCounter = parentParallelInfo["BranchCounter"]

            #self._logger.debug("[StateUtils] processBranchTerminalState: ")
            #self._logger.debug("\t ParentParallelInfo:" + json.dumps(parentParallelInfo))
            #self._logger.debug("\t parallelName:" + parallelName)
            #self._logger.debug("\t branchCounter: " + str(branchCounter))
            #self._logger.debug("\t key:" + key)
            #self._logger.debug("\t metadata:" + json.dumps(metadata))
            #self._logger.debug("\t value_output(type):" + str(type(value_output)))
            #self._logger.debug("\t value_output:" + value_output)

            parallelInfoKey = parallelName + "_" + key + "_parallel_info"
            #self._logger.debug("\t parallelInfoKey:" + parallelInfoKey)
            if parallelInfoKey in metadata:
                parallelInfo = metadata[parallelInfoKey]

                counterName = str(parallelInfo["CounterName"])
                branchOutputKeys = parallelInfo["BranchOutputKeys"]
                branchOutputKey = str(branchOutputKeys[branchCounter-1])

                branchOutputKeysSetKey = str(parallelInfo["BranchOutputKeysSetKey"])

                #self._logger.debug("\t branchOutputKey:" + branchOutputKey)
                #self._logger.debug("\t branchOutputKeysSetKey:" + branchOutputKeysSetKey)

                assert py3utils.is_string(branchOutputKey)
                sapi.put(branchOutputKey, value_output)

                assert py3utils.is_string(branchOutputKeysSetKey)
                sapi.addSetEntry(branchOutputKeysSetKey, branchOutputKey)

                assert py3utils.is_string(counterName)
                try:
                    dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

                    # increment the triggerable counter
                    dlc.incrementCounter(counterName, 1, tableName=dlc.countertriggerstable)
                except Exception as exc:
                    self._logger.error("Exception incrementing counter: " + str(exc))
                    self._logger.error(exc)
                    raise
                finally:
                    dlc.shutdown()

            else:
                self._logger.error("[StateUtils] processBranchTerminalState Unable to find ParallelInfo")
                raise Exception("processBranchTerminalState Unable to find ParallelInfo")

        if self.parsedfunctionstateinfo["End"] and "ParentMapInfo" in self.parsedfunctionstateinfo:

            parentMapInfo = self.parsedfunctionstateinfo["ParentMapInfo"]

            #self._logger.debug("[StateUtils] processBranchTerminalState:parentMapInfo: " + str(parentMapInfo))
            mapName = parentMapInfo["Name"]
            #self._logger.debug("[StateUtils] processBranchTerminalState:mapName: " + str(mapName))
            mapInfoKey = mapName + "_" + key + "_map_info"
            #self._logger.debug("[StateUtils] processBranchTerminalState:mapInfoKey: " + str(mapInfoKey))

            branchCounter = parentMapInfo["BranchCounter"]

            #self._logger.debug("[StateUtils] processBranchTerminalState: ")
            #self._logger.debug("\t ParentMapInfo:" + json.dumps(parentMapInfo))
            #self._logger.debug("\t mapName:" + mapName)
            #self._logger.debug("\t branchCounter: " + str(branchCounter))
            #self._logger.debug("\t key:" + key)
            #self._logger.debug("\t metadata:" + json.dumps(metadata))
            #self._logger.debug("\t value_output(type):" + str(type(value_output)))
            #self._logger.debug("\t value_output:" + value_output)

            if mapInfoKey in metadata:
                mapInfo = metadata[mapInfoKey]

                rest = metadata["__function_execution_id"].split("_")[1:]
                for codes in rest: # find marker for map state and use it to calculate curent index
                    if "-M" in codes:
                        index = rest.index(codes)
                        current_index = int(rest[index].split("-M")[0])

                self._logger.debug("[StateUtils] current_index: " + str(current_index))
                if mapInfo["MaxConcurrency"] != 0:
                    current_index = current_index % int(mapInfo["MaxConcurrency"])

                counterName = str(mapInfo["CounterName"])
                branchOutputKeys = mapInfo["BranchOutputKeys"]
                #branchOutputKey = str(branchOutputKeys[branchCounter-1])
                branchOutputKey = str(branchOutputKeys[current_index])

                branchOutputKeysSetKey = str(mapInfo["BranchOutputKeysSetKey"])

                self._logger.debug("\t branchOutputKey:" + branchOutputKey)
                self._logger.debug("\t branchOutputKeysSetKey:" + branchOutputKeysSetKey)

                assert py3utils.is_string(branchOutputKey)
                sapi.put(branchOutputKey, value_output)

                assert py3utils.is_string(branchOutputKeysSetKey)
                sapi.addSetEntry(branchOutputKeysSetKey, branchOutputKey)

                assert py3utils.is_string(counterName)
                try:
                    dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

                    # increment the triggerable counter
                    dlc.incrementCounter(counterName, 1, tableName=dlc.countertriggerstable)
                except Exception as exc:
                    self._logger.error("Exception incrementing counter: " + str(exc))
                    self._logger.error(exc)
                    raise
                finally:
                    dlc.shutdown()

            else:
                self._logger.error("[StateUtils] processBranchTerminalState Unable to find MapInfo")
                raise Exception("processBranchTerminalState Unable to find MapInfo")

    def evaluatePostParallel(self, function_input, key, metadata, sapi):
        #self._logger.debug("[StateUtils] evaluatePostParallel: ")
        #self._logger.debug("\t key:" + key)
        #self._logger.debug("\t metadata:" + json.dumps(metadata))
        #self._logger.debug("\t function_input: " + str(function_input))

        action = metadata["__state_action"]
        assert action == "post_parallel_processing"
        counterValue = function_input["CounterValue"]

        workflow_instance_metadata_storage_key = str(function_input["WorkflowInstanceMetadataStorageKey"])
        assert py3utils.is_string(workflow_instance_metadata_storage_key)
        full_metadata_encoded = sapi.get(workflow_instance_metadata_storage_key)
        # self._logger.debug("[StateUtils] full_metadata_encoded: " + str(full_metadata_encoded))

        full_metadata = json.loads(full_metadata_encoded)

        parallelInfoKey = self.functionstatename + "_" + key +  "_parallel_info"
        parallelInfo = full_metadata[parallelInfoKey]

        branchOutputKeysSetKey = str(parallelInfo["BranchOutputKeysSetKey"])
        branchOutputKeysSet = sapi.retrieveSet(branchOutputKeysSetKey)
        if not branchOutputKeysSet:
            self._logger.error("[StateUtils] branchOutputKeysSet is empty")
            raise Exception("[StateUtils] branchOutputKeysSet is empty")

        k_list = parallelInfo["Klist"]

        #self._logger.debug("\t action: " + action)
        #self._logger.debug("\t counterValue:" + str(counterValue))
        #self._logger.debug("\t WorkflowInstanceMetadataStorageKey:" + metadata["WorkflowInstanceMetadataStorageKey"])
        #self._logger.debug("\t full_metadata:" + full_metadata_encoded)
        #self._logger.debug("\t parallelInfoKey:" + parallelInfoKey)
        #self._logger.debug("\t parallelInfo:" + json.dumps(parallelInfo))
        #self._logger.debug("\t branchOutputKeysSetKey:" + branchOutputKeysSetKey)
        #self._logger.debug("\t branchOutputKeysSet:" + str(branchOutputKeysSet))
        #self._logger.debug("\t k_list:" + str(k_list))

        NumBranchesFinished = abs(counterValue)
        #self._logger.debug("\t NumBranchesFinished:" + str(NumBranchesFinished))
        do_cleanup = False
        if k_list[-1] == NumBranchesFinished:
            do_cleanup = True

        #self._logger.debug("\t do_cleanup:" + str(do_cleanup))

        counterName = str(parallelInfo["CounterName"])
        assert py3utils.is_string(counterName)
        counter_metadata_key_name = counterName + "_metadata"

        if do_cleanup:
            assert py3utils.is_string(counterName)
            try:
                dlc = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)

                # done with the triggerable counter
                dlc.deleteCounter(counterName, tableName=dlc.countertriggerstable)

                dlc.delete(counter_metadata_key_name, tableName=dlc.countertriggersinfotable)
            except Exception as exc:
                self._logger.error("Exception deleting counter: " + str(exc))
                self._logger.error(exc)
                raise
            finally:
                dlc.shutdown()

            #self._logger.debug("\t deleted Counter: " + counterName)
            sapi.delete(workflow_instance_metadata_storage_key)

        post_parallel_output_values = []
        #self._logger.debug("\t parallelInfo_BranchOutputKeys:" + str(parallelInfo["BranchOutputKeys"]))
        for outputkey in parallelInfo["BranchOutputKeys"]:
            outputkey = str(outputkey)
            if outputkey in branchOutputKeysSet:
                #self._logger.debug("\t BranchOutputKey:" + outputkey)
                while sapi.get(outputkey) == "":
                    time.sleep(0.1) # wait until value is available

                branchOutput = sapi.get(outputkey)
                branchOutput_decoded = json.loads(branchOutput)
                #self._logger.debug("\t branchOutput(type):" + str(type(branchOutput)))
                #self._logger.debug("\t branchOutput:" + branchOutput)
                #self._logger.debug("\t branchOutput_decoded(type):" + str(type(branchOutput_decoded)))
                #self._logger.debug("\t branchOutput_decoded:" + str(branchOutput_decoded))
                post_parallel_output_values = post_parallel_output_values + [branchOutput_decoded]
                if do_cleanup:
                    sapi.delete(outputkey) # cleanup the key from data layer
                    #self._logger.debug("\t cleaned output key:" + outputkey)
            else:
                post_parallel_output_values = post_parallel_output_values + [None]

        #self._logger.debug("\t post_parallel_output_values:" + str(post_parallel_output_values))
        if do_cleanup:
            sapi.deleteSet(branchOutputKeysSetKey)

        if "Next" in self.parsedfunctionstateinfo:
            #self._logger.debug("\t add_dynamic_next:" + self.parsedfunctionstateinfo["Next"])
            sapi.add_dynamic_next(self.parsedfunctionstateinfo["Next"], post_parallel_output_values)

        #ToDo: need to check if Parallel state itself is terminal state

        if "End" in self.parsedfunctionstateinfo:
            if self.parsedfunctionstateinfo["End"]:
            #self._logger.debug("\t add_dynamic_next:" + self.parsedfunctionstateinfo["Next"])
                sapi.add_dynamic_next("end", post_parallel_output_values)

        return function_input, full_metadata


    def evaluateNonTaskState(self, function_input, key, metadata, sapi):
        # 3. Evaluate Non Task states
        #self._logger.debug("[StateUtils] NonTask state type: " + str(self.functionstatetype))
        #self._logger.debug("[StateUtils] Welcome to evaluateNonTaskState! Current key:" + str(key))
        function_output = None
        if self.functionstatetype == StateUtils.choiceStateType:
            #self._logger.debug("[StateUtils] Choice state info:" + str(self.functionstateinfo))
            self.evaluateChoiceConditions(function_input) # this sets chosen Next state
            #self._logger.debug("[StateUtils] Choice state Next:" + str(self.choiceNext))
            function_output = function_input # output of the Choice state

        elif self.functionstatetype == StateUtils.waitStateType:
            #self._logger.debug("[StateUtils] Wait state info:" + str(self.functionstateinfo))
            function_output = function_input
            if "Seconds" in list(json.loads(self.functionstateinfo).keys()):
                wait_state_seconds = json.loads(self.functionstateinfo)['Seconds']
                #self._logger.debug("[StateUtils] Wait state seconds:" + str(wait_state_seconds))
                time.sleep(float(wait_state_seconds))

            elif "SecondsPath" in list(json.loads(self.functionstateinfo).keys()):
                wait_state_secondspath = json.loads(self.functionstateinfo)['SecondsPath']
                #self._logger.debug("[StateUtils] Wait state secondspath:" + str(wait_state_secondspath))
                wait_state_secondspath_data = [match.value for match in parse(wait_state_secondspath).find(function_input)]
                if wait_state_secondspath_data == []:
                    #self._logger.exception("[StateUtils] Wait state timestamppath does not match: " + str(wait_state_secondspath))
                    raise Exception("Wait state timestamppath does not match")

                #self._logger.debug("[StateUtils] Wait state timestamppath data parsed:" + str(wait_state_secondspath_data[0]))
                time.sleep(float(wait_state_secondspath_data[0]))

            elif "Timestamp" in list(json.loads(self.functionstateinfo).keys()):
                wait_state_timestamp = json.loads(self.functionstateinfo)['Timestamp']
                #self._logger.debug("[StateUtils] Wait state timestamp:" + str(wait_state_timestamp))

                target_time = datetime.strptime(str(wait_state_timestamp), "%Y-%m-%dT%H:%M:%SZ")
                current_time = datetime.utcnow()

                #self._logger.debug("[StateUtils] Wait state timestamp difference" + str(current_time) + str(target_time))
                remaining = (target_time - current_time).total_seconds()
                #self._logger.debug("[StateUtils] Wait state timestamp remaining total_seconds:" + str(remaining))
                remaining_time = float(remaining)
                if remaining_time > 0:
                    time.sleep(remaining_time)
                else:
                    self._logger.error("[StateUtils] Wait state timestamp target lies in the past!" + str(wait_state_timestamp))


            elif "TimestampPath" in list(json.loads(self.functionstateinfo).keys()):
                wait_state_timestamppath = json.loads(self.functionstateinfo)['TimestampPath']
                self._logger.debug("[StateUtils] Wait state timestamppath:" + str(wait_state_timestamppath))
                # need to communicate with datalayer for definition of trigger for hibernating/resuming task
                wait_state_timestamppath_data = [match.value for match in parse(wait_state_timestamppath).find(function_input)]
                if wait_state_timestamppath_data == []:
                    #self._logger.exception("[StateUtils] Wait state timestamp_path does not match: " + str(wait_state_timestamppath))
                    raise Exception("Wait state timestamp_path does not match")

                self._logger.debug("[StateUtils] Wait state timestamppath data parsed:" + str(wait_state_timestamppath_data[0]))

                target_time = datetime.strptime(str(wait_state_timestamppath_data[0]), "%Y-%m-%dT%H:%M:%SZ")
                self._logger.debug("[StateUtils] Wait state timestamp data" + str(target_time))
                current_time = datetime.utcnow()

                self._logger.debug("[StateUtils] Wait state timestamp difference" + str(current_time) + str(target_time))
                remaining = (target_time - current_time).total_seconds()
                self._logger.debug("[StateUtils] Wait state timestamp remaining total_seconds:" + str(remaining))
                remaining_time = float(remaining)
                self._logger.debug("[StateUtils] Wait state timestamp remaining total_seconds:" + str(remaining_time))
                if remaining_time > 0:
                    time.sleep(remaining_time)
                else:
                    self._logger.error("[StateUtils] Wait state timestamp target lies in the past!" + str(wait_state_timestamppath_data[0]))
                    raise Exception("Wait state timestamp target lies in the past!" + str(wait_state_timestamppath_data[0]))

            else:
                #self._logger.exception("[StateUtils] Wait state: Missing required field")
                raise Exception("Wait state: Missing required field")


        elif self.functionstatetype == StateUtils.passStateType:
            self._logger.debug("[StateUtils] Pass state handling, received value:" + str(function_input))
            function_output = function_input

            if "Result" in self.functionstateinfo:
                pass_state_result = json.loads(self.functionstateinfo)['Result']
                self._logger.debug("[StateUtils] Pass state result:" + str(pass_state_result))#  self.functionstateinfo['Result']))
                function_output = pass_state_result

        elif self.functionstatetype == StateUtils.succeedStateType:
            function_output = function_input

        elif self.functionstatetype == StateUtils.failStateType:
            self._logger.debug("[StateUtils] Fail state handling, received value:" + str(function_input))
            self._logger.debug("[StateUtils] Fail state handling, received metadata:" + str(metadata))

            if "Cause" in self.functionstateinfo:
                fail_state_cause = json.loads(self.functionstateinfo)['Cause']
                self._logger.debug("[StateUtils] Fail state cause info:" + str(fail_state_cause))

            if "Error" in self.functionstateinfo:
                error_state_error = json.loads(self.functionstateinfo)['Error']
                self._logger.debug("[StateUtils] Fail state error info:" + str(error_state_error))
            function_output = function_input


        elif self.functionstatetype == StateUtils.parallelStateType:
            self._logger.debug("[StateUtils] Parallel state handling function_input: " + str(function_input))
            self._logger.debug("[StateUtils] Parallel state handling metadata: " + str(metadata))
            self._logger.debug("[StateUtils] Parallel state handling")

            if "__state_action" not in metadata or metadata["__state_action"] != "post_parallel_processing":
                function_output, metadata = self.evaluateParallelState(function_input, key, metadata, sapi)
            else:
                if metadata["__state_action"] == "post_parallel_processing":
                    function_output, metadata = self.evaluatePostParallel(function_input, key, metadata, sapi)

        elif self.functionstatetype == StateUtils.mapStateType:
            name_prefix = self.functiontopic + "_" + key

            self._logger.debug("[StateUtils] Map state handling function_input: " + str(function_input))
            self._logger.debug("[StateUtils] Map state handling metadata: " + str(metadata))

            if "MaxConcurrency" in self.parsedfunctionstateinfo.keys():
                maxConcurrency = int(self.parsedfunctionstateinfo["MaxConcurrency"])
            else:
                maxConcurrency = 0

            self._logger.debug("[StateUtils] Map state maxConcurrency: " + str(maxConcurrency))
            self._logger.debug("[StateUtils] Map state handling")

            if "__state_action" not in metadata or metadata["__state_action"] != "post_map_processing":
                # here we start the iteration process on a first batch
                if maxConcurrency != 0:
                    tobeProcessednow = function_input[:maxConcurrency] # take the first maxConcurrency elements
                    tobeProcessedlater = function_input[maxConcurrency:] # keep the remaining  elements for later
                else:
                    tobeProcessednow = function_input
                    tobeProcessedlater = []
                self._logger.debug("[StateUtils] Map state function_input split:" + str(tobeProcessednow) + " " + str(tobeProcessedlater))
                sapi.put(name_prefix + "_" + "tobeProcessedlater", str(tobeProcessedlater)) # store elements to be processed on DL
                sapi.put(name_prefix + "_" + "mapStatePartialResult", "[]") # initialise the collector variable
                sapi.put(name_prefix + "_" + "mapInputCount", str(len(function_input)))

                """
                metadata["tobeProcessedlater"] = str(tobeProcessedlater) # store elements to be processed on DL
                metadata["mapStatePartialResult"] = "[]" # initialise the collector variable
                metadata["mapInputCount"] =  str(len(function_input))

                """

                function_output, metadata = self.evaluateMapState(tobeProcessednow, key, metadata, sapi)

            elif metadata["__state_action"] == "post_map_processing":
                        tobeProcessedlater = ast.literal_eval(sapi.get(name_prefix + "_" + "tobeProcessedlater")) # get all elements that have not yet been processed
                        #tobeProcessedlater = ast.literal_eval(self._mapStateInfo["tobeProcessedlater"]) # get all elements that have not yet been processed
                        self._logger.debug("[StateUtils] Map state post_map processing input:" + str(tobeProcessedlater))
                        # we need to decide at this point if there is a need for more batches. if so:

                        if len(tobeProcessedlater) > 0: # we need to start another batch
                            function_output, metadata2 = self.evaluatePostMap(function_input, key, metadata, sapi) # take care not to overwrite metadata
                            function_output, metadata = self.evaluateMapState(tobeProcessedlater[:maxConcurrency], key, metadata, sapi) # start a new batch
                            sapi.put(name_prefix + "_" + "tobeProcessedlater", str(tobeProcessedlater[maxConcurrency:])) # store remaining elements to be processed on DL
                            #self._mapStateInfo["tobeProcessedlater"] = str(tobeProcessedlater[maxConcurrency:]) # store remaining elements to be processed on DL
                        else: # no more batches required. we are at the iteration end, publish the final result
                            self._logger.debug("[StateUtils] Map state input final stage: " + str(function_input))
                            function_output, metadata = self.evaluatePostMap(function_input, key, metadata, sapi)

            else:
                raise Exception("Unknow action type in map state")

        else:
            raise Exception("Unknown state type")

        return function_output, metadata


    def applyResultPath(self, raw_state_input, function_output):
        #4. Apply ResultPath, if available and if not 'Parallel' state
        #       if ResultPath:
        #           if ResultPath == '$' (this is the default value)
        #                raw_state_input_midway = function_output
        #           if ResultPath == 'null'
        #               raw_state_input_midway = raw_state_input
        #           if ResultPath == some variable name
        #               raw_state_input[some variable name] = function_output
        #               raw_state_input_midway = raw_state_input
        #       else:
        #           raw_state_input_midway = function_output
        #
        raw_state_input_midway = raw_state_input
        #self._logger.debug("Reached applyResultPath: " + str(self.result_path_dict))
        try:
            if self.result_path_dict and 'ResultPath' in self.result_path_dict:
                raw_state_input_midway = self.process_result_path(self.result_path_dict, raw_state_input, function_output)
            else:
                raw_state_input_midway = function_output
            return raw_state_input_midway
        except Exception as exc:
            raise Exception("Result path processing exception: " + str(exc))
            #self._logger.exception("Result path processing exception")
            #sys.stdout.flush()
            #self._logger.exception(exc)
            #raise

    def applyOutputPath(self, raw_state_input_midway):
        #5. Apply OutputPath, if available
        #       if OutputPath:
        #           if OutputPath == '$' (this is the default value)
        #               raw_state_output = raw_state_input_midway
        #           if OutputPath = 'null'
        #               raw_state_output = {}
        #           if OutputPath == some existing variable in 'raw_state_input_midway'
        #               raw_state_output = raw_state_input_midway[some existing variable]
        #           if OutputPath == some non-existing variable
        #               throw exception
        #       else:
        #           raw_state_output = raw_state_input_midway
        raw_state_output = raw_state_input_midway
        try:
            if self.output_path_dict and 'OutputPath' in self.output_path_dict:
                raw_state_output = self.process_output_path(self.output_path_dict, raw_state_input_midway)
            else:
                raw_state_output = raw_state_input_midway
            return raw_state_output
        except Exception as exc:
            raise Exception("Output path processing exception: " + str(exc))
            #self._logger.exception("Output path processing exception")
            #sys.stdout.flush()
            #self._logger.exception(exc)
            #raise

    def parse_function_state_info(self):
        if self.functionstatetype == StateUtils.defaultStateType:
            #self._logger.debug("Task_SAND state parsing. Not parsing further")
            return
        else:
            self.parsedfunctionstateinfo = json.loads(self.functionstateinfo)
            statedef = self.parsedfunctionstateinfo
            statetype = self.functionstatetype
            assert statetype == statedef['Type']

        if statetype == StateUtils.waitStateType:
            self._logger.debug("Wait state parsing")

        if statetype == StateUtils.failStateType:
            self._logger.debug("Fail state parsing")

        if statetype == StateUtils.succeedStateType:
            self._logger.debug("Succeed state parsing")

        if statetype == StateUtils.taskStateType:
            #self._logger.debug("Task state parsing")

            if "InputPath" in statedef: # read the I/O Path dicts
                self.input_path_dict['InputPath'] = statedef['InputPath']
                #self._logger.debug("found InputPath: " + json.dumps(self.input_path_dict['InputPath']))

            if "OutputPath" in statedef:
                self.output_path_dict['OutputPath'] = statedef['OutputPath']
                #self._logger.debug("found OutputPath: " + json.dumps(self.output_path_dict['OutputPath']))

            if "ResultPath" in statedef:
                self.result_path_dict['ResultPath'] = statedef['ResultPath']

            if "Parameters" in statedef:
                self.parameters_dict['Parameters'] = statedef['Parameters']
                self._logger.debug("found Parameters: " + json.dumps(self.parameters_dict['Parameters']))

            if "Catch" in statedef:
                self.catcher_list = statedef['Catch']
                # parse it once and store it
                self.catcher_list = ast.literal_eval(str(self.catcher_list))
                #self._logger.debug("found Catchers: " + str(self.catcher_list))

            if "Retry" in statedef:
                self.retry_list = statedef['Retry']
                # parse it once and store it
                self.retry_list = ast.literal_eval(str(self.retry_list))
                #self._logger.debug("found Retry: " + str(self.retry_list))

        if statetype == StateUtils.choiceStateType:
            #self._logger.debug("Choice state parsing")

            if "InputPath" in statedef:
                self.input_path_dict['InputPath'] = statedef['InputPath']
                self._logger.debug("found InputPath: " + json.dumps(statedef['InputPath']))

            if "OutputPath" in statedef:
                self.output_path_dict['OutputPath'] = statedef['OutputPath']
                self._logger.debug("found OutputPath: " + json.dumps(statedef['OutputPath']))

            if "ResultPath" in statedef:
                self.result_path_dict['ResultPath'] = statedef['ResultPath']
                self._logger.debug("found ResultPath: " + json.dumps(self.result_path_dict['ResultPath']))

            self._logger.debug("Choice state rules: " + json.dumps(statedef))
            if "Default" in statedef:
                self.default_next_choice.append(statedef["Default"])
                self._logger.debug("DefaultTarget: " + str(self.default_next_choice))
            #choice_state_default = statedef['Default']

            choices_list = statedef['Choices'] # get the choice rule list for this state
            self._logger.debug("Choice state rules list: " + str(choices_list))

            key_dict = {} # parse the choice rule list into an expression tree
            for choices in choices_list:
                self._logger.debug("Choice state rule element processed: " + json.dumps(list(choices.keys())))
                #self._logger.debug("converted_function_output: " + str(converted_function_output))
                operator_counter = 0
                if ("Not" in list(choices.keys())) or ("And" in list(choices.keys())) or ("Or" in list(choices.keys())):
                    operator_counter += 1
                if operator_counter == 0: # No operators, so no recursive evaluation required
                    self.traverse(choices['Next'], choices)
                    hostname = self.nodelist[-1].split("/")[0]
                    childname = self.nodelist[-1].split("/")[1]
                    previousnode = anytree.Node(choices['Next'])
                    root = previousnode
                    key_dict[hostname] = previousnode
                    previousnode = anytree.Node(childname, parent=previousnode) # key_dict[hostname])
                    #evalname = ast.literal_eval(str(previousnode.name))

                else: # operator detected, we need to traverse the choice rule tree
                    self.traverse(choices['Next'], choices)
                    nodename = self.nodelist[-1].split("/")[0]
                    previousnode = anytree.Node(nodename)
                    root = previousnode
                    key_dict[self.nodelist[-1].split("/{")[0]] = previousnode
                    no_childs = 1 # we already have attached the root

                    for i in range(len(self.nodelist)): # count the nodes in the choice rule tree which do not have childs
                        children = self.nodelist[-(i+1)].split("/")[-1]
                        if children.strip("") == "{}":
                            no_childs += 1

                    for i in range(no_childs):
                        nodename = self.nodelist[-(i+2)].split("/")[i+1]
                        previousnode = anytree.Node(nodename, parent=previousnode)
                        key_dict[self.nodelist[-(i+2)].split("/{")[0]] = previousnode

                    # from now on we have to attach the children expressions

                    for i in range(len(self.nodelist)-no_childs):
                        childname = self.nodelist[-(i+no_childs+1)].split("/")[-1]
                        hostname = self.nodelist[-(i+no_childs+1)].split("/{")[0]
                        previousnode = anytree.Node(childname, key_dict[hostname])

                #test = EvaluateNode(root.children[0])
                #self._logger.debug("Evaluate: " + str(test) + ", Next: " + choices['Next']) # + str(json.dumps(value))
                #input_json={}
                #self._logger.debug("value type: " + value)
                #for key in value.keys():
                    #if key in test:
                        #self._logger.debug("Modified Evaluate: " + key)
                        #test.replace(key, test[key])
                        #self._logger.debug("Modified Evaluate: " + test)
                ##self._logger.debug("Resulting Rendered Tree: " + str(anytree.RenderTree(root)))
                self.parsed_trees.append(root)

            #if statedef[substates]['Type'] == "Task":
            #    self._logger.debug("Task state: " + json.dumps(statedef[substates]))

        if statetype == StateUtils.passStateType:
            self._logger.debug("[StateUtils] Pass state parsing")

            if "InputPath" in statedef:
                self.input_path_dict['InputPath'] = statedef['InputPath']
                self._logger.debug("found InputPath: " + json.dumps(self.input_path_dict['InputPath']))

            if "OutputPath" in statedef:
                self.output_path_dict['OutputPath'] = statedef['OutputPath']
                self._logger.debug("found OutputPath: " + json.dumps(self.output_path_dict['OutputPath']))

            if "ResultPath" in statedef:
                self.result_path_dict['ResultPath'] = statedef['ResultPath']
                self._logger.debug("found ResultPath: " + json.dumps(self.result_path_dict['ResultPath']))

            if "Parameters" in statedef:
                self.parameters_dict['Parameters'] = statedef['Parameters']
                self._logger.debug("found Parameters: " + json.dumps(self.parameters_dict['Parameters']))

            #self._logger.debug("found Next:  " + json.dumps(statedef['Next']))
            #self._logger.debug("found Result:  " + json.dumps(statedef['Result']))

        if statetype == StateUtils.parallelStateType:
            #self._logger.debug("[StateUtils] Parallel state parsing")

            if "InputPath" in statedef:
                self.input_path_dict['InputPath'] = statedef['InputPath']
                self._logger.debug("found InputPath: " + json.dumps(self.input_path_dict['InputPath']))

            if "OutputPath" in statedef:
                self.output_path_dict['OutputPath'] = statedef['OutputPath']
                self._logger.debug("found OutputPath: " + json.dumps(self.output_path_dict['OutputPath']))

            if "ResultPath" in statedef:
                self.result_path_dict['ResultPath'] = statedef['ResultPath']
                self._logger.debug("found ResultPath: " + json.dumps(self.result_path_dict['ResultPath']))

            if "Parameters" in statedef:
                self.parameters_dict['Parameters'] = statedef['Parameters']
                self._logger.debug("found Parameters: " + json.dumps(self.parameters_dict['Parameters']))

        if statetype == StateUtils.mapStateType:
            #self._logger.debug("[StateUtils] Parallel state parsing")

            if "InputPath" in statedef:
                self.input_path_dict['InputPath'] = statedef['InputPath']
                self._logger.debug("found InputPath: " + json.dumps(self.input_path_dict['InputPath']))

            if "ItemsPath" in statedef:
                self.items_path_dict['ItemsPath'] = statedef['ItemsPath']
                self._logger.debug("found ItemsPath: " + json.dumps(self.items_path_dict['ItemsPath']))

            if "ResultPath" in statedef:
                self.result_path_dict['ResultPath'] = statedef['ResultPath']
                self._logger.debug("found ResultPath: " + json.dumps(self.result_path_dict['ResultPath']))

            if "OutputPath" in statedef:
                self.output_path_dict['OutputPath'] = statedef['OutputPath']
                self._logger.debug("found OutputPath: " + json.dumps(self.output_path_dict['OutputPath']))

            if "Parameters" in statedef:
                self.parameters_dict['Parameters'] = statedef['Parameters']
                self._logger.debug("found Parameters: " + json.dumps(self.parameters_dict['Parameters']))


    def EvaluateNode(self, node):
        """
        Recursively parse the expression tree starting from given node into a python statement
        """

        if not node.children: # this is a leaf node
            evalname = json.dumps(ast.literal_eval(str(node.name)))
            #type(evalname) == int or type(evalname) == float:
            ev_expr = "(" + self.evaluate(evalname) + ")"
            return ev_expr

        else:  #node is an operator
            if node.name == "Not": # there can be only one child
                child = node.children[0]
                evalname = json.dumps(ast.literal_eval(str(child.name)))
                ev_expr = self.evaluate(evalname)
                return "not (%s)" % ev_expr

            if node.name == "And": # collect all children recursively
                child_and_array = []
                for child in node.children:
                    child_and_array.append(self.EvaluateNode(child))

                returnstr = "(" +  " and ".join(child_and_array) + ")"
                return returnstr

            if node.name == "Or": # collect all children recursively
                child_or_array = []
                for child in node.children:
                    child_or_array.append(self.EvaluateNode(child))
                returnstr = "(" + " or ".join(child_or_array) +  ")"
                return returnstr
            else:  #unknown operator found here. Thow some error!
                raise Exception("Parse Error: unknown operator found: ", node.name)

    def evaluate(self, expression):
        """
        evaluate a AWS Choice rule expression with the data contained in values
        """
        expr = []
        ex = json.loads(expression)
        self._logger.debug(expression)
        vals = {}
        if "Variable" in ex.keys():
            k = ex["Variable"].split("$.")[1]
            vals[k] = ""
            expr.append(k)

        for op in self.operators:
            if op in ex.keys():
                expr.append(self.operators_python[self.operators.index(op)])
                expr.append(ex[op])
                break

        if isinstance(expr[2], (int, float)):
            result = "%s %s %s" % (expr[0], expr[1], expr[2])
        else:
            result = "%s %s '%s'" % (expr[0], expr[1], expr[2]) # we want to compare strings with strings
        return result

    def process_parameters(self, parameters, state_data):
        """
        evaluate JSON path Paramaters in conjunction with state_data
        """
        parameters = parameters['Parameters']
        ret_value = None
        ret_item_value = None

        if parameters == "$": # return unfiltered input data
            ret_value = state_data
        elif parameters is None: #return empty json
            ret_value =  {}
        else: # contains a parameter filter, get it and return selected kv pairs
            ret_value = {}
            ret_index = {}

        for key in parameters.keys(): # process parameters keys
                if key.casefold() == "comment".casefold(): # ignore
                    ret_value[key] = parameters[key]
                elif parameters[key] == "$$.Map.Item.Value": # get Items key
                       value_key = key.split(".$")[0]
                       ret_value = value_key
                       ret_item_value = value_key
                elif parameters[key] == "$$.Map.Item.Index": # get Index key
                       index_key = key.split(".$")[0]
                       ret_index = index_key
                else: # processing more complex Parameters values
                     if isinstance(parameters[key], dict): # parameters key refers to dict value
                        ret_value[key] = {}
                        for k in parameters[key]: # get nested keys
                           if not k.split(".")[-1] == "$": # parse static value
                               print (parameters[key][k])
                               ret_value[key][k] = parameters[key][k]
                           else:
                               new_key = k.split(".$")[0] # use the json paths in paramters to match
                               ret_value[key][new_key] = [match.value for match in parse(parameters[key][k]).find(state_data)][0]
                        return ret_value

                     if isinstance(parameters[key], str): # parameters key refers to string value
                        ret_value = {}
                        new_key = key.split(".$")[0] # get the parameters key
                        query_key = parameters[key].split("$.")[1] # correct the correspondig value
                        new_value = state_data[query_key] # save the actual value before replacing the key
                        for kk in state_data.keys():
                         if isinstance(state_data[kk], dict): # value encapsulates dict
                            ret_value[new_key] = new_value
                            if ret_item_value != None:
                                 ret_value[ret_item_value] = state_data[kk]
                            else:
                                 raise Exception("Error: item value is not set!")
                            ret_value_dict = {}
                            ret_value_dict[kk] = ret_value
                            return ret_value_dict

                         if isinstance(state_data[kk], list):  # value encapsulates list
                            ret_value_list = []
                            for data in state_data[kk]:
                                ret_value_list.append({new_key: new_value, ret_item_value: data})
                            ret_value_dict = {}
                            ret_value_dict[kk] = ret_value_list
                            return ret_value_dict
                     else:
                        raise Exception("Error: invaldid Parmeters format: " + str(parameters[key]))

        # calculate transformed state output provided to Iterator
        ret_total = []
        ret_total_dict = {}

        if isinstance(state_data, dict):
            for kk in state_data.keys():
                for key  in state_data[kk]:
                    if ret_value != {} and ret_index == {}:
                        ret_total.append({ret_value: key})
                    elif ret_value == {} and ret_index != {}:
                        ret_total.append({ret_index: state_data[kk].index(key) })
                    elif ret_value != {} and ret_index != {}:
                        ret_total.append({ret_value: key, ret_index: state_data[kk].index(key) })
                    else:
                        raise Exception("Map State Parameters parse error on dict input: " + str(state_data))
                ret_total_dict[kk] = ret_total
            ret_value = ret_total_dict

        elif isinstance(state_data, list):
            for key in state_data:
                if ret_value != {} and ret_index == {}:
                    ret_total.append({ret_value: key})
                elif ret_value == {} and ret_index != {}:
                    ret_total.append({ret_index: state_data.index(key) })
                elif ret_value != {} and ret_index != {}:
                    ret_total.append({ret_value: key, ret_index: state_data.index(key) })
                else:
                    raise Exception("Map State Parameters parse error on list input: " + str(list))
            ret_value = ret_total
        else:
            raise Exception("Map state parse error: invalid state input")

        return ret_value

    def process_items_path(self, path_fields, state_data):
        ret_value = None
        if 'ItemsPath' not in list(path_fields.keys()):
            path_fields['ItemsPath'] = "$"

        input_path = path_fields['ItemsPath']

        if input_path == "$": # return unfiltered input data
            ret_value = state_data
        elif input_path is None: #return empty  list
            ret_value = []
        else: # it contains a filter, get it and return selected list in input
            self._logger.debug("seeing items_path filter: " + str(input_path) + " " + str(state_data))
            filtered_state_data = [match.value for match in parse(input_path).find(state_data)]
            if not filtered_state_data:
                raise Exception("Items Path processing exception: no match with map state item, invalid path!")
            else:
                filtered_state_data = [match.value for match in parse(input_path).find(state_data)][0]
                ret_value = filtered_state_data
        return ret_value

    def process_input_path(self, path_fields, state_data):
        ret_value = None
        if 'InputPath' not in list(path_fields.keys()):
            path_fields['InputPath'] = "$"
            #return state_data

        input_path = path_fields['InputPath']

        if input_path == "$": # return unfiltered input data
            ret_value = state_data
        elif input_path is None: #return empty dict
            ret_value = {}
        else: # input_path contains a filter, get and apply it
            self._logger.debug("seeing input_path filter: " + str(input_path) + " " + str(state_data))
            filtered_state_data = [match.value for match in parse(input_path).find(state_data)]
            self._logger.debug("after seeing input_path filter: " + str(filtered_state_data))
            if not filtered_state_data:
                raise Exception("Input Path processing exception: no match with state input item, invalid path!")
            else:
                filtered_state_data = [match.value for match in parse(input_path).find(state_data)][0]
                ret_value = filtered_state_data

        return ret_value

    def nested_dict(self, keys, value):
        if len(keys) == 1:
            return {keys[0]: value}
        return {keys[0]: self.nested_dict(keys[1:], value)}

    def process_result_path(self, path_fields, state_data, task_output):
        ret_value = None
        # path_fields: result path dict
        # state_data: input dict
        # task_output: output of the state/task
        if 'ResultPath' not in list(path_fields.keys()):
            path_fields['ResultPath'] = "$"

        result_path = path_fields['ResultPath']

        if result_path == "$":
            ret_value = state_data
        elif result_path is None:
            ret_value = {}
        else: # result_path is not empty so is there a match?
            self._logger.debug("inside ResultPath processing: " + str(result_path) + " " + str(task_output) )
            keys = list(tokenize(result_path)) # get all keys
            filtered_state_data = self.nested_dict(keys[1:], task_output)
            if isinstance(state_data, dict):
                ret_value = dict(list(filtered_state_data.items()) + list(state_data.items())) # adding key and values to new dict
            else:
                ret_value = filtered_state_data

        return ret_value

    def process_output_path(self, path_fields, raw_state_input_midway):
        ret_value = None
        if 'OutputPath' not in list(path_fields.keys()):
            path_fields['OutputPath'] = "$"

        output_path = path_fields['OutputPath']

        if output_path == "$":
            ret_value = raw_state_input_midway
        elif output_path is None:
            ret_value = {}
        else: # output_path is not empty so is there a match?
            filtered_state_data = [match.value for match in parse(output_path).find(raw_state_input_midway)]
            if not filtered_state_data:
                raise Exception("Exception: no match with state input item, invalid path!")
            else:
                key = str(parse(output_path).nodes[-1].value[0])
                filtered_state_data = raw_state_input_midway[key]
                ret_value = filtered_state_data

        return ret_value


    def traverse(self, path, obj):
        """
        Traverse the object recursively and print every path / value pairs.
        """
        cnt = -1
        if isinstance(obj, dict):
            d = obj
            d_sum = {}
            for k, v in list(d.items()):
                if isinstance(v, dict):
                    self.traverse(path + "/" + k, v)
                elif isinstance(v, list):
                    self.traverse(path + "/" + k, v)
                else:
                    d_sum[k] = v

            self.nodelist.append(path + "/" + str(d_sum))

        if isinstance(obj, list):
            li = obj
            for e in li:
                cnt += 1
                if isinstance(e, dict):
                    self.traverse("{path}".format(path=path), e)
                elif isinstance(e, list):
                    self.traverse("{path}".format(path=path), e)

    def evaluateNextState(self, function_input):
        # this should be called for Choice state only
        # for the rest the next values are statically defined and are parsed by hostagent

        if len(self.default_next_choice) > 0:
            nextfunc = self.default_next_choice[-1]

        self._logger.debug("[StateUtils] choice_function_input: " + str(function_input))

        for tree in self.parsed_trees:
            ##self._logger.debug("Resulting Rendered Tree: " + str(anytree.RenderTree(tree.root)))
            ##self._logger.debug("Resulting Rendered Tree Root: " + str(tree.root))
            test = self.EvaluateNode(tree.children[0])

            self._logger.debug("[StateUtils] choice test: " + str(test))
            self._logger.debug("Resulting Parsed Expression: " + str(test))
            self._logger.debug("Current Value String: " + json.dumps(function_input))

            # Sample value input to choice {"Comment": "Test my Iterator function", "iterator": {"count": 10, "index": 5, "step": 1}}
            for key in list(function_input.keys()):
                new_test = "False"
                key = str(key)

                if key == "Comment":
                    continue

                #if "iterator.continue" == str(key):
                self._logger.debug("[StateUtils] choice value key under test: " + key)
                #keys = "continue"
                if key in str(test):
                    val = function_input[key]
                    self._logger.debug("[StateUtils] choice val: " + str(val))
                    if isinstance(val, (int, float)): # calculate new_test value, no additional processing of values

                        self._logger.debug("[StateUtils] choice key/val: " + key + "/" + str(val))
                        new_test = test.replace(key, str(val))
                        self._logger.debug("[StateUtils] choice eval new_test: " + str(eval(str(new_test))))

                    elif "." in test: # need to process the json path of this variable name

                        test2 = "$." + test.lstrip('(').rstrip(')').split("==")[0] # rebuild the json path for the variable
                        jsonpath_expr = parse(test2)

                        choice_state_path_data = [match.value for match in jsonpath_expr.find(function_input)]
                        new_test = str(choice_state_path_data[0])

                    else:
                        new_test = test.replace(key, "'" + str(val)+"'") # need to add high colons to key to mark as string inside the expression

                if eval(str(new_test)):
                    nextfunc = tree.root.name.strip("/")
                    self._logger.debug("now calling: " + str(nextfunc))
                    return nextfunc # {"next":nextfunc, "value": post_processed_value}

        # if no choice rule applied, return the last one (assigned at the beginning)
        self._logger.debug("now calling: " + str(nextfunc))
        return nextfunc
