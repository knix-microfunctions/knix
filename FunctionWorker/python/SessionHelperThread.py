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

import threading

import json
import time
import queue
from collections import deque

from DataLayerClient import DataLayerClient
from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage
from MicroFunctionsExceptions import MicroFunctionsSessionAPIException

import py3utils

class SessionHelperThread(threading.Thread):

    def __init__(self, helper_params, logger, pubutils, sessutils, queueservice, datalayer):

        self._logger = logger

        #self._logger.debug("[SessionHelperThread] " + str(helper_params))

        self._publication_utils = pubutils

        self._session_utils = sessutils

        self._queue_service = queueservice
        self._datalayer = datalayer

        self._sandboxid = helper_params["sandboxid"]
        self._workflowid = helper_params["workflowid"]
        self._session_function_id = helper_params["session_function_id"]
        self._session_id = helper_params["session_id"]

        # set up heartbeat parameters
        self._heartbeat_enabled = False
        self._heartbeat_method = None
        # our own local queue client to be used when sending a heartbeat
        # TODO: double check if we can just reuse the one we're polling
        # probably yes
        self._local_queue_client_heartbeat = None
        self._heartbeat_function = None
        self._heartbeat_data_layer_key = None
        self._data_layer_client_heartbeat = None

        self._init_heartbeat_parameters(helper_params["heartbeat_parameters"])

        # set up communication parameters
        self._communication_params = helper_params["communication_parameters"]
        # similar to the data layer rendezvous point for message delivery, we listen to a local topic
        # allowing us to queue messages and deliver multiple messages to the session function if desired
        self._local_topic_communication = self._communication_params["local_topic_communication"]
        # by default, assign a simple poll timeout
        # if the heartbeat is specified, it will be updated to the heartbeat to ensure
        # we can send regular heartbeats
        self._local_poll_timeout = py3utils.ensure_long(10000)

        # use a queue to keep the incoming update messages for blocking and/or blocking get_update_messages() requests
        self._message_queue = queue.Queue()

        self._local_queue_client = LocalQueueClient(connect=self._queue_service)

        self._special_messages = {}
        self._special_messages["--stop"] = True
        self._special_messages["--update-heartbeat"] = True

        self._is_running = False

        #self._logger.debug("[SessionHelperThread] init done.")

        threading.Thread.__init__(self)

    def _init_heartbeat_parameters(self, heartbeat_params):
        if "heartbeat_method" not in heartbeat_params:
            #self._logger.debug("No heartbeat method is specified; disabling heartbeat.")
            return
        else:
            self._heartbeat_enabled = True
            self._heartbeat_method = heartbeat_params["heartbeat_method"]
            #self._logger.debug("[SessionHelperThread] New heartbeat method: " + str(self._heartbeat_method))

        if self._heartbeat_method == "function":
            if "heartbeat_function" in heartbeat_params:
                # enable function related heartbeat
                self._heartbeat_function = heartbeat_params["heartbeat_function"]
                #self._logger.debug("[SessionHelperThread] New heartbeat function: " + str(self._heartbeat_function))
                if self._local_queue_client_heartbeat is None:
                    self._local_queue_client_heartbeat = LocalQueueClient(connect=self._queue_service)

                # disable data layer related heartbeat
                if self._data_layer_client_heartbeat is not None:
                    self._data_layer_client_heartbeat.delete(self._heartbeat_data_layer_key)
                    self._heartbeat_data_layer_key = None
                    self._data_layer_client_heartbeat.shutdown()
                    self._data_layer_client_heartbeat = None
        elif self._heartbeat_method == "data_layer":
            # needs to be unique among session functions, so use session id + session function id
            # TODO: how do you check the heartbeat in the data layer?
            # checker service or user function needs to know the key
            # OR keep a new map for heartbeats of the session functions
            # so that the checker can retrieve the keys and their values (e.g., timestamps)
            # if a session function misses a heartbeat, the checker function reports to policy handler

            # enable data layer related heartbeat
            self._heartbeat_data_layer_key = "heartbeat_" + self._session_id + "_" + self._session_function_id
            if self._data_layer_client_heartbeat is None:
                self._data_layer_client_heartbeat = DataLayerClient(locality=1, for_mfn=True, sid=self._sandboxid, connect=self._datalayer)

            # disable function related heartbeat
            if self._local_queue_client_heartbeat is not None:
                self._local_queue_client_heartbeat.shutdown()
                self._local_queue_client_heartbeat = None
                self._heartbeat_function = None


        else:
            raise MicroFunctionsSessionAPIException("Unsupported heartbeat method for session function.")

        # must be in milliseconds
        if "heartbeat_interval_ms" in heartbeat_params:
            self._heartbeat_interval = heartbeat_params["heartbeat_interval_ms"]
            self._local_poll_timeout = self._heartbeat_interval / 2.0
            #self._logger.debug("[SessionHelperThread] New heartbeat interval: " + str(self._heartbeat_interval))

    def run(self):
        self._is_running = True

        # initially, it is the heartbeat_interval / 2
        poll_timeout = self._local_poll_timeout

        if self._heartbeat_enabled:
            t_cur = time.time() * 1000.0
            self._send_heartbeat()
            last_heartbeat_time = t_cur

        # _XXX_: our location is stored as part of our metadata
        # so that the remote functions can
        # look it up and send their message via that that location
        # first, create local topic
        self._local_queue_client.addTopic(self._local_topic_communication)

        while self._is_running:
            #self._logger.debug("[SessionHelperThread] polling new session update messages...")
            # wait until the polling interval finishes
            # the polling interval depends on the heartbeat interval and when we actually receive a message
            # if we get a message before, then update the polling interval as (heartbeat_interval - passed_time)
            lqm = self._local_queue_client.getMessage(self._local_topic_communication, poll_timeout)

            # double check we are still running
            # if the long-running function finished while we were polling, no need to send another heartbeat
            if not self._is_running:
                break

            if lqm is not None:
                self._process_message(lqm)

            if self._heartbeat_enabled:
                # send heartbeat
                # even if there are no messages, we might need to send a heartbeat
                t_cur = time.time() * 1000.0
                if (t_cur - last_heartbeat_time) >= self._heartbeat_interval:
                    self._send_heartbeat()
                    last_heartbeat_time = t_cur
                # update the poll time
                # if we sent a heartbeat recently, last_heartbeat and t_cur will cancel each other out
                poll_timeout = py3utils.ensure_long(last_heartbeat_time + self._local_poll_timeout - t_cur)
                #self._logger.debug("updated poll timeout: " + str(poll_timeout))
                if poll_timeout <= 0:
                    # we just missed a deadline; send a heartbeat right away
                    t_cur = time.time() * 1000.0
                    self._send_heartbeat()
                    last_heartbeat_time = t_cur
                    # reset the poll timeout accordingly
                    poll_timeout = self._local_poll_timeout
                    #self._logger.debug("updated poll timeout (after missing deadline): " + str(poll_timeout))

        self._cleanup()

    def _process_message(self, lqm):
        try:
            lqcm = LocalQueueClientMessage(lqm=lqm)
            value = lqcm.get_value()
            #key = lqcm.get_key()
            #self._logger.debug("[SessionHelperThread] new message: " + key + " " + value)
        except Exception as exc:
            self._logger.exception("Exception in handling message to running function: " + str(self._session_function_id) + " " + str(exc))

        # we need to decapsulate and decode this message,
        # because it has been delivered
        # to us without going through the function worker
        value, metadata = self._publication_utils.decapsulate_input(value)
        #self._logger.debug("metadata for session function message: " + str(metadata))

        # need to handle the special messages here
        # check if the message is in json
        is_json = True
        try:
            msg = json.loads(value)
            #self._logger.debug("[SessionHelperThread] JSON value: " + str(msg))
        except Exception as exc:
            is_json = False
            msg = value
            #self._logger.debug("[SessionHelperThread] non-JSON value: " + str(msg))

        # cannot be a special message; queue whatever it is
        # _XXX_: we are encoding/decoding the delivered message; should not actually execute this code
        # it is here for not envisioned corner case (i.e., let the user code deal with it)
        if not is_json:
            self._store_message(msg)
            self._publication_utils.set_metadata(metadata)
        else:
            # the message is json encoded, but it doesn't guarantee that it is a special message
            if "action" in msg and msg["action"] in self._special_messages:
                self._handle_special_message(msg)
            else:
                self._store_message(msg)
                self._publication_utils.set_metadata(metadata)


    def _store_message(self, msg):
        self._message_queue.put(msg)

    def _handle_special_message(self, msg):
        action = msg["action"]

        if action == "--stop":
            self._session_utils.set_session_function_running(False)
            self.shutdown()

        elif action == "--update-heartbeat":
            self._init_heartbeat_parameters(msg["heartbeat_parameters"])

    def get_messages(self, count=1, block=False):
        messages = []

        for i in range(count):
            try:
                msg = self._message_queue.get(block=block)
                messages.append(msg)
                self._message_queue.task_done()
            except Exception as exc:
                pass

        #self._logger.debug("returning messages: " + str(messages))
        return messages

    def _send_heartbeat(self):
        # check if heartbeat is enabled. if not, just return
        # if heartbeat is enabled, then double check we are still running
        # if the long-running function finished while we were processing messages, no need to send another heartbeat
        if not self._heartbeat_enabled or not self._is_running:
            return

        #self._logger.debug("[SessionHelperThread] sending heartbeat to function: " + self._heartbeat_function)

        hb_message = self._get_heartbeat_message()

        # either to another function via a local queue client or to data layer or another method
        if self._heartbeat_method == "function":
            self._send_heartbeat_to_function(hb_message)
        elif self._heartbeat_method == "data_layer":
            self._send_heartbeat_to_data_layer(hb_message)

    def _get_heartbeat_message(self):
        hb_message = {}
        hb_message["session_id"] = self._session_id
        hb_message["session_function_id"] = self._session_function_id
        hb_message["timestamp"] = time.time() * 1000.0
        hb_message["action"] = "--heartbeat"

        #self._logger.debug("heartbeat msg: "+ json.dumps(hb_message))

        return hb_message

    def _send_heartbeat_to_function(self, hb_message):
        # TODO: what if the heartbeat function is a session function as well?
        # either running and/or not started yet, but will continue running after the first message

        # pass our own local queue client, so that there won't be any concurrent access
        # to publication utils' local queue client
        trigger_hb = {}
        trigger_hb["next"] = self._heartbeat_function
        trigger_hb["value"] = hb_message
        self._publication_utils.send_to_function_now("-1l", trigger_hb, self._local_queue_client_heartbeat)

    def _send_heartbeat_to_data_layer(self, hb_message):
        self._data_layer_client_heartbeat.put(self._heartbeat_data_layer_key, json.dumps(hb_message))

    def _cleanup(self):
        #self._logger.debug("[SessionHelperThread] cleaning up...")
        # clean up connections
        if self._data_layer_client_heartbeat is not None:
            self._data_layer_client_heartbeat.delete(self._heartbeat_data_layer_key)
            self._heartbeat_data_layer_key = None
            self._data_layer_client_heartbeat.shutdown()
            self._data_layer_client_heartbeat = None

        if self._local_queue_client_heartbeat is not None:
            self._local_queue_client_heartbeat.shutdown()
            self._local_queue_client_heartbeat = None

        # remove/unregister the topic
        self._local_queue_client.removeTopic(self._local_topic_communication)

        self._local_queue_client.shutdown()
        self._local_queue_client = None

    def shutdown(self):
        self._is_running = False
        # put a dummy message to get out of any blocking 'self.get_messages()' call
        self._message_queue.put(None)
