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

class TriggerableTablesTest(unittest.TestCase):

    #@unittest.skip("")
    def test_triggerable_tables(self):
        test = MFNTest(test_name='triggerable_tables', workflow_filename='wf_triggerable_tables.json')

        input_data = []
        input_data.append("wf_triggerable_tables")
        input_data.append("triggerable_table_" + str(random.randint(0, 10000)))
        input_data.append("triggerable_key_" + str(random.randint(0, 10000)))

        response = test.execute(input_data)

        time.sleep(5)

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")
        start_with_list = False
        start_without_list = False
        for line in log_lines:
            if line.find("start with list") != -1:
                start_with_list = True
            elif line.find("start WITHOUT list") != -1:
                start_without_list = True


        if start_with_list and start_without_list:
            test.report(True, str(input_data), input_data, response)
        else:
            test.report(False, str(input_data), input_data, response)
            for line in log_lines:
                print(line)

        test.undeploy_workflow()
        test.cleanup()
