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
import random
import sys
import time
import unittest

sys.path.append("../")
from mfn_test_utils import MFNTest

class TriggersTimerTest(unittest.TestCase):

    # @unittest.skip("")
    def test_triggers_storage(self):
        test = MFNTest(test_name='triggers_timer',
                       workflow_filename='wf_triggers_timer.json')
        nonce = str(int(time.time() * 1000))

        input_data = []
        workflowname = "wf_triggers_timer"
        input_data.append(workflowname)
        input_data.append(nonce)

        response = test.execute(input_data)

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        counter_state_1 = 0
        counter_state_2 = 0
        for line in log_lines:
            if "_!_TRIGGER_START_" + nonce + ";triggers_timer;" + workflowname in line.strip():
                counter_state_1 = counter_state_1 + 1
            if "_!_TRIGGER_START_" + nonce + ";triggers_timer_state2;" + workflowname in line.strip():
                counter_state_2 = counter_state_2 + 1
        
        if counter_state_1 >=9 and counter_state_2 >=9:
            print("Number of state1 triggers: " + str(counter_state_1))
            print("Number of state2 triggers: " + str(counter_state_2))
            test.report(True, str(input_data), input_data, response)
        else:
            print("Number of state1 triggers: " + str(counter_state_1))
            print("Number of state2 triggers: " + str(counter_state_2))
            test.report(False, str(input_data), input_data, response)
            for line in log_lines:
                print(line.strip())

        test.undeploy_workflow()
        test.cleanup()
