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

import copy
import json
import time

import requests

from DataLayerClient import DataLayerClient
from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage
from MicroFunctionsExceptions import MicroFunctionsException

import py3utils

class PublicationUtils():
    def __init__(self, sandboxid, workflowid, functopic, funcruntime, wfnext, wfpotnext, wflocal, wflist, wfexit, cpon, stateutils, logger, queue, datalayer):
        self._logger = logger

        self._function_topic = functopic
        self._sandboxid = sandboxid
        self._workflowid = workflowid

        self._function_runtime = funcruntime

        self._prefix = self._sandboxid + "-" + self._workflowid + "-"

        self._wf_next = wfnext
        self._wf_pot_next = wfpotnext
        self._wf_local = wflocal
        self._wf_function_list = wflist
        self._wf_exit = wfexit

        # whether we should store backups of triggers before publishing the output
        self._should_checkpoint = cpon

        # the topic to send out messages to remote functions
        # TODO: pub_topic_global becomes a new request to another sandbox?
        # via header?
        self._pub_topic_global = "pub_global"

        self._recovery_manager_topic = "RecoveryManager"

        self._state_utils = stateutils
        self._metadata = None

        self._queue = queue
        self._local_queue_client = None
        self._datalayer = datalayer

        self._sapi = None

        self._output_counter_map = {}

        self._dynamic_workflow = []

        self._backup_data_layer_client = None
        self._execution_info_map_name = None
        self._next_backup_list = []

        #self._logger.debug("[PublicationUtils] init done.")

    # only to be called from the function worker
    def set_sapi(self, sapi):
        self._sapi = sapi

    def set_metadata(self, metadata):
        self._metadata = metadata
        self._execution_info_map_name = "execution_info_map_" + self._metadata["__execution_id"]

    def update_metadata(self, metadata_name, metadata_value, is_privileged=False):
        if is_privileged:
            self._metadata[metadata_name] = metadata_value
        else:
            if "__mfnusermetadata" not in self._metadata:
                self._metadata["__mfnusermetadata"] = {}
            self._metadata["__mfnusermetadata"][metadata_name] = metadata_value

    def _get_local_queue_client(self):
        if self._local_queue_client is None:
            self._local_queue_client = LocalQueueClient(connect=self._queue)
        return self._local_queue_client

    def _shutdown_local_queue_client(self):
        if self._local_queue_client is not None:
            self._local_queue_client.shutdown()

    def get_backup_data_layer_client(self):
        if self._backup_data_layer_client is None:
            # locality = -1 means that the writes happen to the local data layer first and then asynchronously to the global data layer
            self._backup_data_layer_client = DataLayerClient(locality=-1, for_mfn=True, sid=self._sandboxid, connect=self._datalayer)
        return self._backup_data_layer_client

    def shutdown_backup_data_layer_client(self):
        if self._backup_data_layer_client is not None:
            self._backup_data_layer_client.shutdown()

    def convert_api_message_to_python_object(self, message):
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        val = message
        if self._function_runtime == "java":
            val = json.loads(message)
            val = val["value"]

        return val

    def is_valid_value(self, value):
        if not (py3utils.is_string(value) \
            or isinstance(value, (dict, list, int, float)) \
            or value is None):
            return False

        return True

    def _is_valid_trigger_destination(self, destination):
        if not (py3utils.is_string(destination) and destination != ""):
            return False

        return True

    def _is_allowed_or_privileged(self, destination, send_now):
        # Management service is privileged, so allow
        # 1) asynchronous execution
        # 2) Recovery manager topic
        # @ returns a tuple with (is_allowed, is_privileged)
        if self._sandboxid == "Management" and self._workflowid == "Management":
            if destination[0:6] == "async_" or\
                destination == self._recovery_manager_topic:
                # next[0:6] == "async_"
                # next == self._recovery_manager_topic:
                return (True, True)
            return (True, False)

        if send_now:
            if destination not in self._wf_function_list:
                return (False, False)
        elif destination not in self._wf_pot_next:
            return (False, False)

        return (True, False)

    def is_valid_trigger_message(self, next, value, send_now):
        is_valid = True
        errmsg = ""

        if not self._is_valid_trigger_destination(next):
            is_valid = False
            errmsg = "Malformed dynamic trigger definition; 'next' must be a string."

        is_allowed, is_privileged = self._is_allowed_or_privileged(next, send_now)
        if not is_allowed:
            is_valid = False
            if send_now:
                errmsg = errmsg + "\n" + "Destination is not in workflow: " + next
                errmsg = errmsg + "\n" + "Can only send an immediate trigger message to an existing function or the workflow end."
            else:
                errmsg = errmsg + "\n" + "Workflow does not match generated 'next': " + next

        if not self.is_valid_value(value):
            is_valid = False
            errmsg = errmsg + "\n" + "Malformed dynamic trigger definition; 'value' must be a python data type (dict, list, str, int, float, or None)."

        return is_valid, is_privileged, errmsg

    def decode_input(self, encoded_input):
        if encoded_input == '':
            encoded_input = '{}'
        #if isinstance(encoded_input,dict):
        #    encoded_input = json.dumps(encoded_input)
        # if encoded_input aready is a dict, convert to JSON Text
        #if encoded_input.startswith("null"):
        #    encoded_input = encoded_input.replace("null","")
        #Decode input. Input (value) must be a valid JSON Text.
        #however, post-commit hook published value has the format key; value
        #print ("Encoded State Input: " + str(encoded_input).replace("null",""))
        #print ("Encoded State Input: " + str(encoded_input) + str(type(encoded_input)))
        #self._logger.debug("received user input in decode_input: " + str(encoded_input))
        try:
           #if isinstance(encoded_input,str):
            raw_state_input = json.loads(encoded_input)
            #if isinstance(encoded_input,dict):
            #    raw_state_input = encoded_input
            return raw_state_input

        except Exception as exc:
            #self._logger.exception("User Input is not a valid JSON Text")
            #self._logger.exception(exc)
            raise Exception("User Input is not a valid JSON Text: " + str(exc))

    def encode_output(self, raw_state_output):
        #Produce output JSON Text from raw_state_output
        try:
            value_output = json.dumps(raw_state_output)
            return value_output
        except Exception as exc:
            #self._logger.exception("Error while encoding state output")
            #self._logger.exception(exc)
            raise Exception("Error while encoding state output: " + str(exc))

    def decapsulate_input(self, encoded_encapsulated_input):
        # The actual user input is encapsulated in a dict of the form:
        # { "__mfnuserdata": actual_user_input,
        # "__mfnmetadata": system_specific_metadata }
        # This encapsulation is invisible to the user and is added,
        # maintained, and removed by the frontend and function worker.

        if encoded_encapsulated_input == '':
            #self._logger.exception("Invalid encapsulation of user input")
            raise MicroFunctionsException("Invalid encapsulation of user input.")
        else:
            try:
                encapsulated_input = json.loads(encoded_encapsulated_input)
                userdata = encapsulated_input['__mfnuserdata']
                metadata = encapsulated_input['__mfnmetadata']
                return userdata, metadata
            except Exception as exc:
                #self._logger.exception("Unable to decode encapsulated user input")
                #self._logger.exception(e)
                raise MicroFunctionsException("Unable to decode encapsulated user input: " + str(exc))

    def encapsulate_output(self, encoded_state_output, metadata):
        try:
            value = {"__mfnuserdata": encoded_state_output, "__mfnmetadata":  metadata}
            value_output = json.dumps(value)
            return value_output
        except Exception as exc:
            #self._logger.exception("Error while encoding state output")
            #self._logger.exception(e)
            raise MicroFunctionsException("Error while encoding state output: " + str(exc))

    def get_dynamic_workflow(self):
        '''
        Return the dynamically generated workflow information,
        so that this function instance can trigger other functions when it finishes.
        '''
        return self._dynamic_workflow

    def send_message_to_running_function(self, trigger):
        self.send_to_function_now("-1l", trigger, lqcpub=None)

    def append_trigger(self, trigger):
        trigger["value"] = self.encode_output(trigger["value"])
        self._dynamic_workflow.append(trigger)

    def _convert_function_output_static_workflow(self, function_output):
        converted_function_output = []
        for wfnext in self._wf_next:
            converted_function_output.append({"next": wfnext, "value": function_output})
        return converted_function_output

    def _store_output_data(self):
        data_out = self._sapi.get_transient_data_output()
        to_be_deleted = self._sapi.get_data_to_be_deleted()

        if data_out or to_be_deleted:
            dlc = self._sapi._get_data_layer_client()

            for k in data_out:
                dlc.put(k, data_out.get(k))

            for k in to_be_deleted:
                dlc.delete(k)

        data_out_private = self._sapi.get_transient_data_output(is_private=True)
        to_be_deleted_private = self._sapi.get_data_to_be_deleted(is_private=True)

        if data_out_private or to_be_deleted_private:
            dlc_private = self._sapi._get_data_layer_client(is_private=True)

            for k in data_out_private:
                dlc_private.put(k, data_out_private.get(k))

            for k in to_be_deleted_private:
                dlc_private.delete(k)

        self._sapi._shutdown_data_layer_client()

    def _send_local_queue_message(self, lqcpub, lqtopic, key, value):
        # construct a LocalQueueClientMessage(key, value)
        # and send it to the local queue topic via the local queue client
        lqcm = LocalQueueClientMessage(key=key, value=value)

        #lqcpub.addMessage(lqtopic, lqcm, False)
        ack = lqcpub.addMessage(lqtopic, lqcm, True)
        while not ack:
            ack = lqcpub.addMessage(lqtopic, lqcm, True)

    def _send_remote_message(self, remote_address, message_type, lqtopic, key, value):
        # form a http request to send to remote host
        # need to set async=true in request URL, so that the frontend does not have a sync object waiting
        if message_type == "session_update":
            # if a session update message, set headers appropriately
            action_data = {}
            action_data["topic"] = lqtopic
            action_data["key"] = key
            action_data["value"] = value

            resp = requests.post(remote_address,
                                params={"async": 1},
                                json={},
                                headers={"X-MFN-Action": "Session-Update",
                                        "X-MFN-Action-Data": json.dumps(action_data)})

        elif message_type == "global_pub":
            # TODO: if global publishing, set headers appropriately (e.g., for load balancing)
            pass

        return

    def _publish_privileged_output(self, function_output, lqcpub):
        next = function_output["next"]

        output = {}

        # init metadata for the workflow (similar to the frontend)
        metadata = {}
        metadata["__result_topic"] = self._metadata["__result_topic"]
        metadata["__execution_id"] = self._metadata["__execution_id"]
        metadata["__function_execution_id"] = self._metadata["__execution_id"]

        if next[:6] == "async_":
            # backup of the 'input' and 'next' has been done by executeWorkflowAsync in management service
            metadata["__async_execution"] = True
            output["topicNext"] = next[6:]
        elif next == self._recovery_manager_topic:
            metadata["__async_execution"] = self._metadata["__async_execution"]
            output["topicNext"] = next

        output["value"] = self.encapsulate_output(function_output["value"], metadata)

        outkey = self._metadata["__execution_id"]
        # publish to pub manager's separate queue for global next
        outputstr = json.dumps(output)
        self._send_local_queue_message(lqcpub, self._pub_topic_global, outkey, outputstr)

        return (None, None)

    def _generate_trigger_metadata(self, topic_next):
        # keep track of the output instances of the next topic
        # e.g., funcA -> funcB with input1 (instance 0) and funcB with input2 (instance 1)
        if topic_next not in self._output_counter_map:
            self._output_counter_map[topic_next] = 0

        output_instance_id = self._output_counter_map[topic_next]
        next_function_execution_id = self._metadata["__function_execution_id"] + "_" + str(output_instance_id)

        # get current state type. if map state add marker to execution Id
        state_type = self._state_utils.functionstatetype
        self._logger.debug("self._state_utils.functionstatetype: " + str(state_type))

        if state_type == 'Map':
            next_function_execution_id = self._metadata["__function_execution_id"] + "_" + str(output_instance_id)+"-M"
        self._output_counter_map[topic_next] += 1

        trigger_metadata = copy.deepcopy(self._metadata)
        trigger_metadata["__function_execution_id"] = next_function_execution_id

        #self._logger.debug("trigger metadata: " + str(trigger_metadata))

        return (next_function_execution_id, trigger_metadata)

    def _publish_output(self, key, trigger, lqcpub, timestamp_map=None):
        if timestamp_map is not None:
            timestamp_map['t_pub_output'] = time.time() * 1000.0
        next = trigger["next"]

        if "to_running_function" in trigger and trigger["to_running_function"]:
            # SessionUtils API calls have already determined the locality
            # this is for a running function instance on a remote host
            if "is_local" in trigger and trigger["is_local"]:
                trigger["value"] = self.encapsulate_output(trigger["value"], self._metadata)
                # this is for a running function on the local host
                # SessionUtils has already created the appropriate next
                if timestamp_map is not None:
                    timestamp_map['t_pub_localqueue'] = time.time() * 1000.0
                self._send_local_queue_message(lqcpub, next, key, trigger["value"])
            else:
                # send it to the remote host with a special header
                self._send_remote_message(trigger["remote_address"], "session_update", next, key, trigger["value"])
            return (None, None)
        elif "is_privileged" in trigger and trigger["is_privileged"]:
            # next[0:6] == "async_"
            # next == self._recovery_manager_topic:
            return self._publish_privileged_output(trigger, lqcpub)
        else:
            topic_next = self._prefix + next

            output = {}
            output["topicNext"] = topic_next

            next_function_execution_id, trigger_metadata = self._generate_trigger_metadata(topic_next)

            output["value"] = self.encapsulate_output(trigger["value"], trigger_metadata)

            # check whether next is local or not
            if topic_next in self._wf_local:
                # event message directly to the next function's local queue topic
                if timestamp_map is not None:
                    timestamp_map['t_pub_localqueue'] = time.time() * 1000.0
                self._send_local_queue_message(lqcpub, topic_next, key, output["value"])
            else:
                # check if 'next' is exit topic and modify output["topicNext"] accordingly
                isExitTopic = False
                if next == self._wf_exit:
                    isExitTopic = True

                    if self._metadata["__execution_id"] != key:
                        key = self._metadata["__execution_id"]

                    dlc = self.get_backup_data_layer_client()

                    # store the workflow's final result
                    dlc.put("result_" + key, output["value"])
                    #self._logger.debug("[__mfn_backup] [exitresult] [%s] %s", "result_" + key, output["value"])

                    # _XXX_: this is not handled properly by the frontend
                    # this was an async execution
                    # just send an empty message to the frontend to signal end of execution
                    #if "__async_execution" in self._metadata and self._metadata["__async_execution"]:
                    #    output["value"] = ""

                if isExitTopic and timestamp_map is not None:
                    timestamp_map['t_pub_exittopic'] = time.time() * 1000.0
                    timestamp_map['exitsize'] = len(output["value"])
                self._send_local_queue_message(lqcpub, topic_next, key, output["value"])

            return (next_function_execution_id, output)

    def _store_trigger_backups(self, dlc, input_backup_map, current_function_instance_id, store_next_backup_list=False):
        # keep track of the execution instances with their updated keys
        # i.e., keys that contains the output instance ids
        # use this set to describe the execution details

        if self._execution_info_map_name is not None:
            # dump the backups into the data layer
            for input_backup_key in input_backup_map:
                dlc.putMapEntry(self._execution_info_map_name, input_backup_key, input_backup_map[input_backup_key])

            # if there is any new next, store them
            # if a next was generated by sending a message immediately,
            # this next will have been appended to our list in memory
            # and the backup will be overwritten
            # if one or more nexts were generated when publishing
            # at the end of execution, they will have been appended to our list
            # in memory and we will store the backup once for the entire list
            if store_next_backup_list:
                dlc.putMapEntry(self._execution_info_map_name, "next_" + current_function_instance_id, json.dumps(self._next_backup_list))

    def _send_message_to_recovery_manager(self, key, message_type, topic, func_exec_id, has_error, error_type, lqcpub):
        return
        message_rec = {}
        message_rec["messageType"] = message_type
        message_rec["currentTopic"] = topic
        message_rec["currentFunctionExecutionId"] = func_exec_id
        message_rec["hasError"] = has_error
        message_rec["errorType"] = error_type

        output = {}
        output["topicNext"] = self._recovery_manager_topic
        output["value"] = json.dumps(message_rec)
        outputstr = json.dumps(output)
        # message via global publisher to pub manager's queue for backups
        self._send_local_queue_message(lqcpub, self._pub_topic_global, key, outputstr)

    # need to store backups of inputs and send message to recovery manager
    def send_to_function_now(self, key, trigger, lqcpub=None, dlc=None):
        trigger["value"] = self.encode_output(trigger["value"])

        # get a local queue client
        if lqcpub is None:
            lqcpub = self._get_local_queue_client()

        current_function_instance_id = self._metadata["__function_execution_id"] + "_" + self._function_topic

        # if next_function_execution_id and output are None only if:
        # 1) message was sent to a running function (i.e., session function update message)
        # 2) message was a privileged message
        any_next = False
        next_function_execution_id, output = self._publish_output(key, trigger, lqcpub)
        if self._should_checkpoint:
            input_backup_map = {}
            starting_next = {}

            if dlc is None:
                dlc = self.get_backup_data_layer_client()

            if next_function_execution_id is not None and output is not None:
                # here, output MUST contain "topicNext" and "value"; otherwise,
                # we wouldn't have been able to publish it in publish_output()
                # use the updated topicNext for globally published messages
                starting_next[next_function_execution_id] = output["topicNext"]
                next_function_instance_id = next_function_execution_id + "_" + output["topicNext"]
                input_backup_map["input_" + next_function_instance_id] = output["value"]
                self._next_backup_list.append(next_function_instance_id)
                any_next = True

            self._store_trigger_backups(dlc, input_backup_map, current_function_instance_id, store_next_backup_list=any_next)

            for next_func_exec_id in starting_next:
                next_func_topic = starting_next[next_func_exec_id]
                self._send_message_to_recovery_manager(key, "start", next_func_topic, next_func_exec_id, False, "", lqcpub)

            self._send_message_to_recovery_manager(key, "running", self._function_topic, self._metadata["__function_execution_id"], False, "", lqcpub)

    # utilize the workflow to publish directly to the next function's topic
    # publish directly to the next function's topic, accumulate backups
    # publish backups at the end with a 'fin' flag, which also indicates that all have been published
    # also, handle global queue events
    def publish_output_direct(self, key, value_output, has_error, error_type, timestamp_map):
        timestamp_map["t_pub_start"] = timestamp_map["t_start_pub"] = time.time() * 1000.0

        # if we already have a local queue client (because of immediately sent messages) and backup data layer client,
        # re-use them
        # if not, then the call to get them will initialize them
        lqcpub = self._get_local_queue_client()

        # _XXX_: 'function instance id' is uniquely identified via:
        # 1) (workflow) execution id (i.e., uuid set by frontend)
        # 2) output instance id (depends on the number of 'next' using the same function)
        # 3) function topic
        # 1) and 2) => '__function_execution_id' in metadata;
        # set by the previous function (or frontend if we're the first function) in the metadata
        current_function_instance_id = self._metadata["__function_execution_id"] + "_" + self._function_topic

        if has_error:
            timestamp_map["t_start_dlcbackup"] = time.time() * 1000.0
            dlc = self.get_backup_data_layer_client()

            # set data layer flag to stop further execution of function instances
            # that may have been triggered concurrently via a new message
            dlc.put("workflow_execution_stop_" + key, "1")

            # dump the result into the data layer
            result = {}
            result["has_error"] = has_error
            result["error_type"] = error_type

            encoded_result = self.encode_output(result)

            encapsulated_result = self.encapsulate_output(encoded_result, self._metadata)

            #dlc.put("result_" + current_function_instance_id, encapsulated_result)
            dlc.putMapEntry(self._execution_info_map_name, "result_" + current_function_instance_id, encapsulated_result)

            # publish a message to the 'exit' topic
            trigger = {}
            trigger["next"] = self._wf_exit
            trigger["value"] = encoded_result

            # don't need next_function_execution_id, because we'll stop execution anyway
            # similarly, we don't need to do any backups
            next_function_execution_id, output = self._publish_output(key, trigger, lqcpub, timestamp_map)

            # store the workflow's final result
            # which has been encapsulated
            dlc.put("result_" + key, output["value"])
            timestamp_map["hasError"] = True

        else:
            # dump the result into the data layer
            timestamp_map["t_start_encapsulate"] = time.time() * 1000.0
            encapsulated_value_output = self.encapsulate_output(value_output, self._metadata)

            if self._should_checkpoint:
                timestamp_map["t_start_dlcbackup"] = time.time() * 1000.0
                dlc = self.get_backup_data_layer_client()

                #dlc.put("result_" + current_function_instance_id, encapsulated_value_output)
                timestamp_map["t_start_resultmap"] = time.time() * 1000.0
                dlc.putMapEntry(self._execution_info_map_name, "result_" + current_function_instance_id, encapsulated_value_output)
                #self._logger.debug("[__mfn_backup] [%s] [%s] %s", self._execution_info_map_name, "result_" + current_function_instance_id, encapsulated_value_output)

            timestamp_map["t_start_storeoutput"] = time.time() * 1000.0
            # store self._sapi.transient_output into the data layer
            self._store_output_data()

            # get the combined (next, value) tuple list for the output
            # use here the original output:
            # we'll update the metadata separately for each trigger and encapsulate the output with it
            timestamp_map["t_start_generatenextlist"] = time.time() * 1000.0
            converted_function_output = self._convert_function_output_static_workflow(value_output)
            choice_next_list = self._state_utils.getChoiceResults(value_output)
            converted_function_output = converted_function_output + self._dynamic_workflow + choice_next_list

            check_error_flag = True
            continue_publish_flag = True
            # if we are sending the result ONLY to the workflow exit, then there is no point in checking the error flag
            if len(converted_function_output) == 1 and converted_function_output[0]["next"] == self._wf_exit:
                check_error_flag = False

            if check_error_flag:
                timestamp_map["t_start_dlcbackup_err"] = time.time() * 1000.0
                dlc = self.get_backup_data_layer_client()
                # check the workflow stop flag
                # if some other function execution had an error and we had been
                # simultaneously triggered, we can finish but don't need to publish
                # to the next function in the workflow, so we can stop execution of the workflow
                timestamp_map["t_start_dlcbackup_err_flag"] = time.time() * 1000.0
                workflow_exec_stop = dlc.get("workflow_execution_stop_" + key, locality=0)
                if workflow_exec_stop is not None and workflow_exec_stop != "":
                    self._logger.info("Not continuing because workflow execution has been stopped... %s", key)
                    continue_publish_flag = False

            # if we didn't have to check the error, or we checked it, but there was not one, then continue publishing the output
            # to the next functions
            # if we checked the error and there was one, then don't publish to the next functions
            if continue_publish_flag:
                # converted_function_output can only contain next values from static (_wf_next) and dynamic next (_wf_pot_next)
                # static next values would have been already defined and checked before deploying workflow
                # dynamic next values are checked when creating the trigger in MicroFunctionsAPI.add_workflow_next()
                # so there is no need for another check

                if self._should_checkpoint:
                    # we are going to accummulate any input backups in this map
                    input_backup_map = {}
                    # we are going to accummulate any new starting functions in this map
                    starting_next = {}

                timestamp_map["t_start_pubnextlist"] = time.time() * 1000.0
                any_next = False
                # parse the converted_function_output to determine the next and publish directly
                for function_output in converted_function_output:
                    next_function_execution_id, output = self._publish_output(key, function_output, lqcpub, timestamp_map)
                    if self._should_checkpoint:
                        if next_function_execution_id is not None and output is not None:
                            # here, output MUST contain "topicNext" and "value"; otherwise,
                            # we wouldn't have been able to publish it in publish_output()
                            # use the updated topicNext for globally published messages
                            starting_next[next_function_execution_id] = output["topicNext"]
                            next_function_instance_id = next_function_execution_id + "_" + output["topicNext"]
                            input_backup_map["input_" + next_function_instance_id] = output["value"]
                            self._next_backup_list.append(next_function_instance_id)
                            any_next = True

                if self._should_checkpoint:
                    timestamp_map["t_start_backtrigger"] = time.time() * 1000.0
                    # backups for next of successfully completed function execution instances
                    self._store_trigger_backups(dlc, input_backup_map, current_function_instance_id, store_next_backup_list=any_next)

                    for next_func_exec_id in starting_next:
                        next_func_topic = starting_next[next_func_exec_id]
                        self._send_message_to_recovery_manager(key, "start", next_func_topic, next_func_exec_id, False, "", lqcpub)

        if self._should_checkpoint:
            # regardless whether this function execution had an error or not, we are finished and need to let the recovery manager know
            self._send_message_to_recovery_manager(key, "finish", self._function_topic, self._metadata["__function_execution_id"], has_error, error_type, lqcpub)

        # log the timestamps
        timestamp_map["t_pub_end"] = timestamp_map["t_end_pub"] = timestamp_map["t_end_fork"] = time.time() * 1000.0
        timestamp_map["function_instance_id"] = current_function_instance_id
        timestamp_map_str = json.dumps(timestamp_map)
        self._logger.info("[__mfn_progress] %s %s", timestamp_map["function_instance_id"], timestamp_map_str)
        size = 0
        if 'exitsize' in timestamp_map and 't_pub_exittopic' in timestamp_map:
            size = timestamp_map['exitsize']
        self._logger.info("[__mfn_tracing] [ExecutionId] [%s] [Size] [%s] [TimestampMap] [%s] [%s]", key, str(size), timestamp_map_str, timestamp_map["function_instance_id"])
        # also put them to the data layer
        # (can skip, but need to update "getExecutionDescription.py" in ManagementService)
        #dlc.put("timestamps_" + current_function_instance_id, json.dumps(timestamp_map))

        # shut down the local queue client
        self._shutdown_local_queue_client()
        self.shutdown_backup_data_layer_client()

