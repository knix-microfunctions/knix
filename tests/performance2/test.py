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
import unittest
import statistics
import sys
import time

sys.path.append("../")
from mfn_test_utils import MFNTest

class PerformanceLatencyTestSingle(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # 1. parse and obtain workflow
        self._test = MFNTest(test_name="wf_single_checkpoints_on", workflow_filename="wf_single_checkpoints_on.json")
        self._test_checkpoints_off = MFNTest(test_name="wf_single_checkpoints_off", workflow_filename="wf_single_checkpoints_off.json")

    #@unittest.skip("")
    def test_echo_0_bytes(self):
        test_tuple_list=[]
        for i in range(20):
            # 0 bytes
            inp0 = ""
            res0 = ""

            test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        self._test.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

        #test.plot_latency_breakdown(20)
        time.sleep(5)

        self._test_checkpoints_off.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

    #@unittest.skip("")
    def test_echo_4_bytes(self):
        test_tuple_list=[]
        for i in range(20):
            # 4 bytes
            inp0 = "echo"
            res0 = "echo"

            test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        self._test.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

        #test.plot_latency_breakdown(20)
        time.sleep(5)

        self._test_checkpoints_off.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

    #@unittest.skip("")
    def test_echo_1_MByte(self):
        test_tuple_list=[]
        for i in range(20):
            # 1MB
            inp0 = "echo" * 1024 * 256
            res0 = "echo" * 1024 * 256

            test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        self._test.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

        #test.plot_latency_breakdown(20)
        time.sleep(5)

        self._test_checkpoints_off.exec_tests(test_tuple_list, check_duration=True, should_undeploy=False)

    @classmethod
    def tearDownClass(self):
        self._test.undeploy_workflow()
        self._test.cleanup()
        self._test_checkpoints_off.undeploy_workflow()
        self._test_checkpoints_off.cleanup()
