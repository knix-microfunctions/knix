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
import sys
import time
from random import randint

import unittest

sys.path.append("../")
from mfn_test_utils import MFNTest

class WorkflowErrorHandlingTest(unittest.TestCase):

    #@unittest.skip("")
    def test_error_frontend_propagation(self):
        test_tuple_list = []

        event = {}
        # something that can NOT be cast as integer
        event["function1_input"] = "one"

        # some input to be checked in the log
        event["function6_input"] = "FINAL"

        expected_output = {}
        expected_output["has_error"] = True
        expected_output["error_type"] = "User code exception: ValueError"

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(test_name="Workflow Error Propogation", workflow_filename="workflow_error_handling.json")
        test.exec_tests(test_tuple_list)

    #@unittest.skip("")
    def test_no_error(self):
        test_tuple_list = []

        event = {}
        # something that can be cast as integer
        event["function1_input"] = "1"

        # some input to be checked in the log
        event["function6_input"] = "FINAL"

        expected_output = {}
        expected_output["function1_input"] = "1"
        expected_output["function6_input"] = "FINAL"
        expected_output["function6_output"] = "FINAL_output"

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(test_name="Workflow No Error", workflow_filename="workflow_error_handling.json")
        test.exec_tests(test_tuple_list)

    #@unittest.skip("")
    def test_error_stop(self):
        test_tuple_list = []

        event = {}
        # something that can NOT be cast as integer
        event["function1_input"] = "one"

        # some input to be checked in the log
        event["function6_input"] = "FINAL"

        expected_output = {}
        expected_output["has_error"] = True
        expected_output["error_type"] = "User code exception: ValueError"

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(test_name="Workflow Error Stop", workflow_filename="workflow_error_handling.json")
        response = test.execute(event)

        # get execution description and/or logs and check the stop message
        time.sleep(10)
        log = self._get_log_lines(test, "Not continuing because workflow execution has been stopped...")
        print(log)
        if log:
            test.report(True, "workflow_stop_with_error", True, True)

        test.undeploy_workflow()
        test.cleanup()

    ## internal methods
    def _get_log_lines(self, test, contained_text):
        workflow_logs = self._get_workflow_logs(test)
        log = workflow_logs["log"]
        log_lines = log.split("\n")

        lines = []
        for line in log_lines:
            if line.find(contained_text) != -1:
                lines.append(line)

        return lines

    def _get_workflow_logs(self, test):
        logs = test.get_workflow_logs()
        return logs

    def _clear_workflow_logs(self, test):
        test.clear_workflow_logs()

def main():
    unittest.main()

if __name__ == '__main__':
    main()

