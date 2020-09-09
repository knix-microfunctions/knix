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

class TriggersStorageTest(unittest.TestCase):

    #@unittest.skip("")
    def test_triggers_storage(self):
        test = MFNTest(test_name='triggers_storage', workflow_filename='wf_triggers_storage.json')
        nonce = str(int(time.time() * 1000))

        input_data = []
        input_data.append("wf_triggers_storage")
        input_data.append("triggerable_table")
        input_data.append("triggerable_key")
        input_data.append(nonce)

        response = test.execute(input_data)

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        received_reponse = []
        try:
            received_reponse = [response["trigger_start_main_wf"], response["explicit_start_main_wf"], response["trigger_start_other_wf"], response["explicit_start_other_wf"]]
            main_trigger_logs = response["main_trigger_logs"]
            other_trigger_logs = response["other_trigger_logs"]
        except Exception as e:
            print("Error: " + str(e))
            pass

        if self.matches_expected_response(received_reponse) == True and self.log_lines_match(main_trigger_logs, other_trigger_logs, nonce) == True:
            test.report(True, str(input_data), input_data, response)
        else:
            test.report(False, str(input_data), input_data, response)
            for line in log_lines:
                print(line.strip())

        test.undeploy_workflow()
        test.cleanup()
    
    def matches_expected_response(self, received_reponse):
        expected_response = [4,1,2,0]
        if received_reponse == expected_response:
            return True
        else:
            print("ERROR: matches_expected_response = False: received response: " + str(received_reponse))
            return False
    
    def log_lines_match(self, main_trigger_logs, other_trigger_logs, nonce):
        main_log_lines_suffix = [1,2,3,4]
        if len(main_trigger_logs) != len(main_log_lines_suffix):
            print("ERROR: log_lines_match = False, len(main_trigger_logs) does not match")
            return False
        
        for i in range(4):
            suffix = main_log_lines_suffix[i]
            to_match = f"_!_TRIGGER_START_{nonce};{suffix}"
            logline = main_trigger_logs[i].strip()
            if to_match not in logline:
                print("ERROR: log_lines_match = False, main_trigger_logs mismatch: " + to_match + " not found in " + logline)
                return False
        
        other_log_lines_suffix = [1,3]
        if len(other_trigger_logs) != len(other_log_lines_suffix):
            print("ERROR: log_lines_match = False, len(other_trigger_logs) does not match")
            return False

        for i in range(2):
            suffix = other_log_lines_suffix[i]
            to_match = f"_!_TRIGGER_START_{nonce};{suffix}"
            logline = other_trigger_logs[i].strip()
            if to_match not in logline:
                print("ERROR: log_lines_match = False, other_trigger_logs mismatch: " + to_match + " not found in " + logline)
                return False

        return True