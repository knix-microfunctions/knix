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

        expected_response = [4,1,2,0]
        received_reponse = []
        try:
            received_reponse = [response["trigger_start_main_wf"], response["explicit_start_main_wf"], response["trigger_start_other_wf"], response["explicit_start_other_wf"]]
        except Exception as e:
            print("Error: " + str(e))
            pass

        if expected_response == received_reponse:
            test.report(True, str(input_data), input_data, response)
        else:
            test.report(False, str(input_data), input_data, response)
            for line in log_lines:
                print(line.strip())

        test.undeploy_workflow()
        test.cleanup()
