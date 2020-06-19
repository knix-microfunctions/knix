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

import datetime
from random import randint
import sys
import time
import unittest

import json
import statistics

import random

sys.path.append("../")
from mfn_test_utils import MFNTest

class ASL_SessionSupportTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # 1. parse and obtain workflow
        self._test = MFNTest(workflow_filename="wf_asl_session_all.json")
        time.sleep(2)

    def setUp(self):
        self._session_id = self._setup_new_session()
        time.sleep(1)

    #@unittest.skip("")
    def test_session_setup(self):
        self._clear_workflow_logs()
        session_info = self._get_session_info()
        if "session_id" not in session_info:
            self._test.report(False, "session_setup: session_id", True, "session_id" in session_info)
        elif session_info["session_id"] != self._session_id:
            self._test.report(False, "session_setup: session_id equality", True, session_info["session_id"] == self._session_id)
        elif "session_function_ids" not in session_info:
            self._test.report(False, "session_setup: session_function_ids", True, "session_function_ids" in session_info)
        else:
            self._test.report(True, "session_setup", True, True)

    #@unittest.skip("")
    def test_send_message_to_entire_session(self):
        success = True

        update_message = "config2"
        self._send_message_to_entire_session(update_message)

        time.sleep(15)

        new_telemetry_content = self._get_telemetry_content()
        if len(new_telemetry_content) != 2:
            self._test.report(False, "telemetry_content: length", 2, len(new_telemetry_content))
            success = False

        for function_info in new_telemetry_content:
            function_name = function_info.split(":")[0]
            for telemetry in new_telemetry_content[function_info]:
                if telemetry != "telemetry_" + function_name + "::doSomethingElse()":
                    self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doSomethingElse()", telemetry)
                    success = False

        if success:
            self._test.report(True, "send_message_to_session", True, True)

    #@unittest.skip("")
    def test_send_message_with_function_name(self):
        success = True

        update_message = "config2"
        self._send_message_to_function_with_name("sessionFunction1", update_message)

        time.sleep(15)

        new_telemetry_content = self._get_telemetry_content()
        if len(new_telemetry_content) != 2:
            self._test.report(False, "telemetry_content: length", 2, len(new_telemetry_content))
            success = False

        for function_info in new_telemetry_content:
            function_name = function_info.split(":")[0]
            for telemetry in new_telemetry_content[function_info]:
                if function_name == "sessionFunction1":
                    if telemetry != "telemetry_" + function_name + "::doSomethingElse()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doSomethingElse()", telemetry)
                        success = False
                else:
                    if telemetry != "telemetry_" + function_name + "::doStuff()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doStuff()", telemetry)
                        success = False

        if success:
            self._test.report(True, "send_message_to_function", True, True)

    #@unittest.skip("")
    def test_send_message_with_session_function_id(self):
        success = True

        session_info = self._get_session_info()
        # pick a session function and use its id
        picked_function_id = session_info["session_function_ids"][randint(0,1)]

        update_message = "config2"
        self._send_message_to_function_with_id(picked_function_id, update_message)

        time.sleep(15)

        new_telemetry_content = self._get_telemetry_content()
        if len(new_telemetry_content) != 2:
            self._test.report(False, "telemetry_content: length", 2, len(new_telemetry_content))
            success = False

        for function_info in new_telemetry_content:
            info = function_info.split(":")
            function_name = info[0]
            function_id = info[2]
            for telemetry in new_telemetry_content[function_info]:
                if function_id == picked_function_id:
                    if telemetry != "telemetry_" + function_name + "::doSomethingElse()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doSomethingElse()", telemetry)
                        success = False
                else:
                    if telemetry != "telemetry_" + function_name + "::doStuff()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doStuff()", telemetry)
                        success = False

        if success:
            self._test.report(True, "send_message_to_function", True, True)

    #@unittest.skip("")
    def test_session_session_alias_operations(self):
        session_alias_summary = self._get_session_alias_summary()

        if "session" not in session_alias_summary:
            self._test.report(False, "alias_summary: session", True, "session" in session_alias_summary)
        elif self._session_id not in session_alias_summary["session"]:
            self._test.report(False, "alias_summary: session_id", True, self._session_id in session_alias_summary["session"])
        elif session_alias_summary["session"][self._session_id] is not None:
            self._test.report(False, "alias_summary: alias", True, session_alias_summary["session"][self._session_id] is None)
        else:
            self._test.report(True, "alias_summary: init", True, True)

        message = {}
        message["session_id"] = self._session_id
        message["alias_type"] = "session"

        message["action"] = "--set-alias"
        message["alias"] = "mySessionAlias"

        self._send_message(message)

        time.sleep(5)

        session_alias_summary = self._get_session_alias_summary()
        if "session" not in session_alias_summary:
            self._test.report(False, "alias_summary: session 2", True, "session" in session_alias_summary)
        elif self._session_id not in session_alias_summary["session"]:
            self._test.report(False, "alias_summary: session_id 2", True, self._session_id in session_alias_summary["session"])
        elif session_alias_summary["session"][self._session_id] != "mySessionAlias":
            self._test.report(False, "alias_summary: alias 2", True, session_alias_summary["session"][self._session_id] == "mySessionAlias")
        else:
            self._test.report(True, "alias_summary: set", True, True)

        message["action"] = "--unset-alias"

        self._send_message(message)

        time.sleep(5)

        session_alias_summary = self._get_session_alias_summary()

        if "session" not in session_alias_summary:
            self._test.report(False, "alias_summary: session 3", True, "session" in session_alias_summary)
        elif self._session_id not in session_alias_summary["session"]:
            self._test.report(False, "alias_summary: session_id 3", True, self._session_id in session_alias_summary["session"])
        elif session_alias_summary["session"][self._session_id] is not None:
            self._test.report(False, "alias_summary: alias 3", True, session_alias_summary["session"][self._session_id] is None)
        else:
            self._test.report(True, "alias_summary: unset", True, True)

    #@unittest.skip("")
    def test_session_function_alias_operations(self):
        session_alias_summary = self._get_session_alias_summary()

        if "session_functions" not in session_alias_summary:
            self._test.report(False, "alias_summary: session functions", True, "session_functions" in session_alias_summary)
        else:
            self._test.report(True, "alias_summary: session functions", True, True)

        session_info = self._get_session_info()
        function_id_list = session_info["session_function_ids"]

        success = True
        for function_id in function_id_list:
            if "session_functions" not in session_alias_summary:
                self._test.report(False, "alias_summary: session functions 2", True, "session_functions" in session_alias_summary)
            else:
                if function_id not in session_alias_summary["session_functions"]:
                    self._test.report(False, "alias_summary: function id", True, function_id in session_alias_summary["session_functions"])
                    success = False
                elif session_alias_summary["session_functions"][function_id] is not None:
                    self._test.report(False, "alias_summary: function alias 1", True, session_alias_summary["session_functions"][function_id] is None)
                    success = False

        if success:
            self._test.report(True, "alias_summary: init", True, True)

        message = {}
        message["sessionId"] = self._session_id
        message["alias_type"] = "function"

        message["action"] = "--set-alias"

        for function_id in function_id_list:
            message["function_id"] = function_id
            message["alias"] = "alias_" + function_id
            self._send_message(message)

        time.sleep(5)

        session_alias_summary = self._get_session_alias_summary()

        #print(session_alias_summary)

        if "session_functions" not in session_alias_summary:
            self._test.report(False, "alias_summary: session functions 3", True, "session_functions" in session_alias_summary)
        else:
            self._test.report(True, "alias_summary: session functions 3", True, True)

        session_info = self._get_session_info()
        function_id_list = session_info["session_function_ids"]

        success = True

        for function_id in function_id_list:
            if "session_functions" not in session_alias_summary:
                self._test.report(False, "alias_summary: session functions 4", True, "session_functions" in session_alias_summary)
            else:
                if function_id not in session_alias_summary["session_functions"]:
                    self._test.report(False, "alias_summary: function id", True, function_id in session_alias_summary["session_functions"])
                    success = False
                elif session_alias_summary["session_functions"][function_id] != "alias_" + function_id:
                    self._test.report(False, "alias_summary: function alias 2", True, session_alias_summary["session_functions"][function_id] == "alias_" + function_id)
                    success = False

        if success:
            self._test.report(True, "alias_summary: set", True, True)

        # pick a session function and use its id
        picked_function_id = session_info["session_function_ids"][randint(0,1)]

        update_message = "config2"
        self._send_message_to_function_with_alias("alias_" + picked_function_id, update_message)

        time.sleep(15)

        success = True

        new_telemetry_content = self._get_telemetry_content()
        if len(new_telemetry_content) != 2:
            self._test.report(False, "telemetry_content: length", 2, len(new_telemetry_content))
            success = False

        for function_info in new_telemetry_content:
            info = function_info.split(":")
            function_name = info[0]
            function_id = info[2]
            for telemetry in new_telemetry_content[function_info]:
                if function_id == picked_function_id:
                    if telemetry != "telemetry_" + function_name + "::doSomethingElse()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doSomethingElse()", telemetry)
                        success = False
                else:
                    if telemetry != "telemetry_" + function_name + "::doStuff()":
                        self._test.report(False, "telemetry_content", "telemetry_" + function_name + "::doStuff()", telemetry)
                        success = False

        if success:
            self._test.report(True, "send_message_to_function_with_alias", True, True)

        message["action"] = "--unset-alias"

        for function_id in function_id_list:
            message["function_id"] = function_id
            self._send_message(message)

        session_alias_summary = self._get_session_alias_summary()

        if "session_functions" not in session_alias_summary:
            self._test.report(False, "alias_summary: session functions 5", True, "session_functions" in session_alias_summary)
        else:
            self._test.report(True, "alias_summary: session functions 5", True, True)

        session_info = self._get_session_info()
        function_id_list = session_info["session_function_ids"]

        success = True

        for function_id in function_id_list:
            if "session_functions" not in session_alias_summary:
                self._test.report(False, "alias_summary: session functions 6", True, "session_functions" in session_alias_summary)
            else:
                if function_id not in session_alias_summary["session_functions"]:
                    self._test.report(False, "alias_summary: function id", True, function_id in session_alias_summary["session_functions"])
                    success = False
                elif session_alias_summary["session_functions"][function_id] is not None:
                    self._test.report(False, "alias_summary: function alias 3", True, session_alias_summary["session_functions"][function_id] is None)
                    success = False

        if success:
            self._test.report(True, "alias_summary: unset", True, True)

    #@unittest.skip("")
    def test_stop_session(self):
        self._clear_workflow_logs()
        old_session_id = self._session_id
        self._stop_session()
        time.sleep(10)
        self._session_id = None
        session_info = self._get_session_info()
        #print session_info
        if "session_id" not in session_info:
            self._test.report(False, "session_stop: session_id", True, "session_id" in session_info)
        elif "session_function_ids" not in session_info:
            self._test.report(False, "session_stop: session_function_ids", True, "session_function_ids" in session_info)
        elif session_info["session_id"] == old_session_id:
            self._test.report(False, "session_stop: session_id change", False, session_info["session_id"] == old_session_id)
        elif len(session_info["session_function_ids"]) != 0:
            self._test.report(False, "session_stop: session_function_ids count", True, len(session_info["session_function_ids"]) == 0)
        else:
            self._test.report(True, "session_stop", True, True)


    #@unittest.skip("")
    def test_send_heartbeat_update_message(self):
        # old heartbeat was 15000ms, new heartbeat should be 7500ms
        old_heartbeat_interval = 15000.0
        new_heartbeat_interval = 7500.0
        should_be_ratio = round(old_heartbeat_interval / new_heartbeat_interval, 1)

        old_heartbeat_timestamps = self._get_heartbeat_timestamps()

        old_interval_map = self._get_heartbeat_intervals(old_heartbeat_timestamps)

        #HBUPDATEMSG="{\"action\":\"--update-heartbeat\",\"heartbeat_parameters\":{\"heartbeat_interval_ms\":2000,\"heartbeat_function\":\"heartbeatHandler\"}}"
        heartbeat_parameters = {}
        heartbeat_parameters["heartbeat_method"] = "function"
        heartbeat_parameters["heartbeat_interval_ms"] = new_heartbeat_interval
        heartbeat_parameters["heartbeat_function"] = "heartbeatHandler"

        message = {}
        message["action"] = "--update-heartbeat"
        message["heartbeat_parameters"] = heartbeat_parameters

        self._send_message_to_entire_session(message)

        time.sleep(15)

        new_heartbeat_timestamps = self._get_heartbeat_timestamps()

        new_interval_map = self._get_heartbeat_intervals(new_heartbeat_timestamps)

        #print("ratio should be: " + str(should_be_ratio))

        if len(old_interval_map) != len(new_interval_map):
            self._test.report(False, "heartbeat_intervals: length", True, len(old_interval_map) == len(new_interval_map))
        else:
            for function_info in new_interval_map:
                ratio = old_interval_map[function_info] / new_interval_map[function_info]
                # sometimes fails when run on a loaded system due to scheduling
                #print(function_info[:10] + " ratio: " + str(ratio) + " old: " + str(old_interval_map[function_info]) + " new: " + str(new_interval_map[function_info]))
                if round(ratio, 1) == should_be_ratio:
                    self._test.report(True, "heartbeat_intervals: ratio (almost equal)", True, round(ratio) == should_be_ratio)
                elif old_interval_map[function_info] > new_interval_map[function_info]:
                    self._test.report(True, "heartbeat_intervals: ratio 2", True, old_interval_map[function_info] > new_interval_map[function_info])
                else:
                    self._test.report(False, "heartbeat_intervals: ratio 3", True, old_interval_map[function_info] > new_interval_map[function_info])

    def tearDown(self):
        if self._session_id is not None:
            self._stop_session()

    @classmethod
    def tearDownClass(self):
        self._test.undeploy_workflow()

    ####################
    # internal functions
    ####################

    def _setup_new_session(self):
        #MESSAGE="{\"action\":\"--create-new-session\",\"session\":[{\"name\":\"sessionFunction1\",\"parameters\":\"config1\"},{\"name\":\"sessionFunction2\",\"parameters\":\"config1\"}]}"
        message = {}
        message["action"] = "--create-new-session"
        message["session"] = []
        session_function_list = []
        session_function1 = {}
        session_function1["name"] = "sessionFunction1"
        session_function1["parameters"] = "config1"
        session_function_list.append(session_function1)

        session_function2 = {}
        session_function2["name"] = "sessionFunction2"
        session_function2["parameters"] = "config1"
        session_function_list.append(session_function2)

        message["session"] = session_function_list

        session_id = self._send_message(message)

        return session_id

    def _stop_session(self):
        #STOPMSG="{\"action\":\"--stop\"}"
        stop_message = {}
        stop_message["action"] = "--stop"

        self._send_message_to_entire_session(stop_message)

    def _get_heartbeat_intervals(self, heartbeat_timestamps):
        heartbeat_intervals = {}
        for function_info in heartbeat_timestamps:
            timestamps = heartbeat_timestamps[function_info]
            size = len(timestamps)
            ts_list = []
            for ts in timestamps:
                ts_list.append(float(ts))

            total_diff = 0.0
            ts_list.sort()
            for i in range(size-1):
                ts_diff = ts_list[i+1] - ts_list[i]
                #print(str(i) + " " + function_info + " ts_diff: " + str(ts_diff))
                total_diff += ts_diff

            heartbeat_intervals[function_info] = total_diff/(size-1)
            diff = ts_list[-1] - ts_list[0]
            heartbeat_intervals[function_info + "_first_last_average"] = diff/(size-1)

        return heartbeat_intervals

    def _get_log_lines(self, contained_text):
        workflow_logs = self._get_workflow_logs()
        #progress_log = workflow_logs["progress"]
        #print(progress_log)
        log = workflow_logs["log"]
        log_lines = log.split("\n")
        #last_timestamp = workflow_logs["timestamp"]
        #asctime = datetime.utcfromtimestamp(last_timestamp/1000.0/1000.0)
        #print("Log last timestamp: " + str(type(last_timestamp)) + " " + str(last_timestamp) + " " + str(asctime))
        lines = []
        for line in log_lines:
            if line.find("[FunctionWorker]") != -1:
                continue
            if line.find("[__mfn_progress]") != -1:
                continue
            if line.find(contained_text) != -1:
                lines.append(line)

        return lines

    def _get_heartbeat_timestamps(self):
        self._clear_workflow_logs()

        # allow some time for heartbeat content to accummulate
        time.sleep(60)

        heartbeat_lines = self._get_log_lines("[heartbeatHandler]")

        heartbeat_timestamps = {}
        for line in heartbeat_lines:
            line = line.split(" ")[-1]
            fields = line.split("@")
            timestamp = fields[1]
            function_info = fields[0]
            if function_info not in heartbeat_timestamps:
                heartbeat_timestamps[function_info] = []
            heartbeat_timestamps[function_info].append(timestamp)

        return heartbeat_timestamps

    def _get_telemetry_content(self):
        self._clear_workflow_logs()

        # allow some time for telemetry content to accummulate
        time.sleep(60)

        telemetry_lines = self._get_log_lines("[telemetryHandler]")

        telemetry_content = {}
        for line in telemetry_lines:
            #print(line)
            line = line.split(" ")[-1]
            fields = line.split("@")
            function_info = fields[0]
            telemetry = fields[1].split(">")[-1]
            if function_info not in telemetry_content:
                telemetry_content[function_info] = []
            telemetry_content[function_info].append(telemetry)

        return telemetry_content

    def _get_session_info(self):
        #MESSAGE="{\"sessionId\":\"$SESSIONID\",\"action\":\"--get-session-info\"}"
        message = {}
        message["sessionId"] = self._session_id
        message["action"] = "--get-session-info"

        session_info = self._send_message(message)

        return session_info

    def _get_session_alias_summary(self):
        message = {}
        message["sessionId"] = self._session_id
        message["action"] = "--get-session-alias-summary"

        session_alias_summary = self._send_message(message)

        return session_alias_summary

    def _send_message_to_entire_session(self, update_message):
        #MESSAGE="{\"immediate\":false,\"sessionId\":\"$SESSIONID\",\"action\":\"--update-session\",\"messageType\":\"$MSGTYPE\",\"sessionUpdateParams\":$DATA}"
        message = {}
        message["immediate"] = False
        message["sessionId"] = self._session_id
        message["action"] = "--update-session"
        message["messageType"] = "session"
        message["sessionUpdateParams"] = update_message

        self._send_message(message)

    def _send_message_to_function_with_name(self, function_name, update_message):
        #MESSAGE="{\"immediate\":true,\"sessionId\":\"$SESSIONID\",\"action\":\"--update-session\",\"messageType\":\"$MSGTYPE\",\"messageToFunction\":\"sessionFunction1\",\"sessionUpdateParams\":$DATA}"
        message = {}
        message["immediate"] = False
        message["sessionId"] = self._session_id
        message["action"] = "--update-session"
        message["messageType"] = "name"
        message["messageToFunction"] = function_name
        message["sessionUpdateParams"] = update_message

        self._send_message(message)

    def _send_message_to_function_with_id(self, function_id, update_message):
        #MESSAGE="{\"immediate\":true,\"sessionId\":\"$SESSIONID\",\"action\":\"--update-session-function\",\"sessionFunctionId\":\"$SGID\",\"sessionUpdateParams\":$DATA}"
        message = {}
        message["immediate"] = False
        message["sessionId"] = self._session_id
        message["action"] = "--update-session-function"
        message["sessionFunctionId"] = function_id
        message["sessionUpdateParams"] = update_message

        self._send_message(message)

    def _send_message_to_function_with_alias(self, function_alias, update_message):
        message = {}
        message["immediate"] = False
        message["sessionId"] = self._session_id
        message["action"] = "--update-session-function-with-alias"
        message["alias"] = function_alias
        message["sessionUpdateParams"] = update_message

        self._send_message(message)

    def _get_workflow_logs(self):
        logs = self._test.get_workflow_logs()
        return logs

    def _send_message(self, message):
        response = self._test.execute(message)
        return response

    def _clear_workflow_logs(self):
        self._test.clear_workflow_logs()

class ASL_DynamicParallelExecutionGroupsTest(unittest.TestCase):

    #@unittest.skip("")
    def test_wordcount(self):
        # test parameters
        size=100
        num_mappers = 5
        ##

        test_tuple_list = []

        data = self._get_wordcount_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_wordcount_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "wordcount"
        job["input_format"] = "string"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_asl_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    #@unittest.skip("")
    def test_wordcount_nested(self):
        # test parameters
        size = 5000
        num_mappers = 10
        ##

        test_tuple_list = []

        data = self._get_wordcount_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_wordcount_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "wordcount"
        job["input_format"] = "string"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        # add a condition for the mappers, so that they can create more PEGs
        # dynamically if any condition is met
        event["mapper_conditions"] = {}
        # this ensures that there will be at least another level of dynamic PEG
        max_len = int(size * 5 / num_mappers / 2)
        #print("max len: " + str(max_len))
        event["mapper_conditions"]["max_len"] = max_len

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_asl_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    #@unittest.skip("")
    def test_mergesort(self):
        # test parameters
        size = 200
        # mergesort's reducers need to work with 2 mapper outputs (i.e., merge operation)
        num_mappers = 2
        ##

        test_tuple_list = []

        data = self._get_mergesort_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_mergesort_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "mergesort"
        job["input_format"] = "array"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        # add a condition for the mappers, so that they can create more PEGs
        # dynamically if any condition is met
        event["mapper_conditions"] = {}
        max_len = int(size / num_mappers / 5)
        #print("max len: " + str(max_len))
        event["mapper_conditions"]["max_len"] = 10

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_asl_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    ####################
    # internal functions
    ####################

    def _get_wordcount_data(self, size=50):
        data = ""
        for i in range(size):
            data += "a quick brown fox jumped over the lazy dog\n"
            data += "the lazy dog got jumped over by a quick brown fox\n"
            data += "a brown fox is not really brown but orange\n"
            data += "the lazy dog is not really lazy but friendly to brown foxes\n"
            data += "even if the brown foxes are really orange and not brown\n"

        # remove last newline "\n"
        return data.rstrip()

    def _get_mergesort_data(self, size=50):
        data = []
        for i in range(size):
            data.append(random.randint(0, 1000000))

        return data

    def _get_wordcount_expected_result(self, data):
        expected_result = {}
        words = []
        lines = data.split("\n")
        for line in lines:
            words += line.split(" ")
        for word in words:
            if word == "":
                continue
            if word not in expected_result:
                expected_result[word] = 0
            expected_result[word] += 1

        return expected_result

    def _get_mergesort_expected_result(self, data):
        data.sort()
        return data

class ASL_PerformanceFunctionInteractionLatencyTest(unittest.TestCase):

    @unittest.skip("")
    def test_chain_response_latency_checkpoints(self):
        count_executions = 20

        test_tuple_list=[]
        for i in range(count_executions):
            inp0 = ""
            res0 = ""

            test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        test = MFNTest(test_name='chain_checkpoints_off', workflow_filename='wf_asl_chain_checkpoints_off.json', new_user=True)
        print("----------------")
        print("Checkpoints off:")
        test.exec_tests(test_tuple_list, check_duration=True)
        #test.plot_latency_breakdown(20)

        test = MFNTest(test_name='chain_checkpoints', workflow_filename='wf_asl_chain_checkpoints_on.json', new_user=True)
        print("----------------")
        print("Checkpoints on:")
        test.exec_tests(test_tuple_list, check_duration=True)
        #test.plot_latency_breakdown(20)

def main():
    unittest.main()

if __name__ == '__main__':
    main()

