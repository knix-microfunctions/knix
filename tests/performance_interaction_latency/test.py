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

COUNT_EXECUTIONS = 20

class PerformanceFunctionInteractionLatencyTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self._test_tuple_list = []
        for i in range(COUNT_EXECUTIONS):
            inp0 = ""
            res0 = ""

            self._test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

    #@unittest.skip("")
    def test_function_interaction_latency(self):
        test = MFNTest(test_name='function_interaction_latency_checkpoints_off', workflow_filename='wf_function_interaction_latency_checkpoints_off.json')
        test.exec_tests(self._test_tuple_list, check_duration=True, print_report=False, should_undeploy=False)

        logs = test.get_workflow_logs(num_lines=1000)

        self._get_and_print_statistics(test, logs, False)

        #test.plot_latency_breakdown(COUNT_EXECUTIONS)

        test.undeploy_workflow()
        test.cleanup()

        test = MFNTest(test_name='function_interaction_latency_checkpoints_on', workflow_filename='wf_function_interaction_latency_checkpoints_on.json')
        test.exec_tests(self._test_tuple_list, check_duration=True, print_report=False, should_undeploy=False)

        logs = test.get_workflow_logs(num_lines=1000)

        self._get_and_print_statistics(test, logs, True)

        #test.plot_latency_breakdown(COUNT_EXECUTIONS)

        test.undeploy_workflow()
        test.cleanup()

    #@unittest.skip("")
    def test_chain_response_latency(self):
        test = MFNTest(test_name='chain_checkpoints_off', workflow_filename='wf_chain_checkpoints_off.json')
        print("----------------")
        print("Checkpoints: False")

        test.exec_tests(self._test_tuple_list, check_duration=True, print_report=False)

        #test.plot_latency_breakdown(COUNT_EXECUTIONS)

        test = MFNTest(test_name='chain_checkpoints', workflow_filename='wf_chain_checkpoints.json')
        print("----------------")
        print("Checkpoints: True")

        test.exec_tests(self._test_tuple_list, check_duration=True, print_report=False)

        #test.plot_latency_breakdown(COUNT_EXECUTIONS)

    def _get_and_print_statistics(self, test, logs, checkpoints_on):
        log = logs["log"]
        log_lines = log.split("\n")
        lines = []
        for line in log_lines:
            if line == "":
                continue
            if line.find("[FunctionWorker]") != -1:
                continue
            if line.find("[__mfn_progress]") != -1:
                continue
            if line.find("[__mfn_backup]") != -1:
                continue
            lines.append(line)

        tsmap = {}
        for line in lines:
            tokens = line.split(" ")
            length = len(tokens)
            fname = tokens[length-2][1:-1]
            ts = tokens[length-1]
            if fname == "":
                continue
            if fname not in tsmap:
                tsmap[fname] = []
            tsmap[fname].append(float(ts) * 1000.0)

        tslist_function1 = tsmap["function1"]
        tslist_function2 = tsmap["function2"]

        if len(tslist_function1) != len(tslist_function2):
            print("Warning: length of timestamp lists do not match!")
            print(str(len(tslist_function1)) + "!=" + str(len(tslist_function2)))

        diffs = []
        for i in range(len(tslist_function1)):
            diffs.append(tslist_function2[i] - tslist_function1[i])

        print("------")
        print("Function interaction latency statistics (checkpoints: " + str(checkpoints_on) + "):")
        print("Number of executions: " + str(COUNT_EXECUTIONS))
        print("Average (ms): " + str(statistics.mean(diffs)))
        print("Median (ms): " + str(statistics.median(diffs)))
        print("Minimum (ms): " + str(min(diffs)))
        print("Maximum (ms): " + str(max(diffs)))
        print("Stdev (ms): " + str(statistics.stdev(diffs)))
        print("PStdev (ms): " + str(statistics.pstdev(diffs)))

        percentiles = [0.0, 50.0, 90.0, 95.0, 99.0, 99.9, 99.99, 100.0]
        test.print_percentiles(diffs, percentiles)
        print("------")
