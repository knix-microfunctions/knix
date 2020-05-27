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
import sys

sys.path.append("../")
from mfn_test_utils import MFNTest

class EchoTest(unittest.TestCase):

    #@unittest.skip("")
    def test_echo_wfd(self):
        test_tuple_list=[]
        for i in range(20):
            # 1MB
            #inp0 = "echo" * 1024 * 256
            #res0 = "echo" * 1024 * 256
            inp0 = "echo"
            res0 = "echo"

            test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        test = MFNTest(test_name='echo', workflow_filename='echo.json')
        test.exec_tests(test_tuple_list, check_duration=True)

        #test.plot_latency_breakdown(20)
