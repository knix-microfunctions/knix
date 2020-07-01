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

import unittest
import os, sys
import json
import time

sys.path.append("../")
from mfn_test_utils import MFNTest

class ParallelTest(unittest.TestCase):

    """ Parallel state test

    """

    def test_parallel(self):
        """ creates and executes the parallel workflow from the ASL description """
        testtuplelist = []

        event = [10, 20]
        expectedResponse = [[10, 20, 'Branch1Task.py'], [10, 20, 'Branch2Task.py'], [10, 20, 'Branch3Task.py']]

        testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

        event = 'a'
        expectedResponse = ['a Branch1Task.py', 'a Branch2Task.py', 'a Branch3Task.py']

        testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

        event = {"a": "b"}
        expectedResponse = [{"a": "b", "functionName": "Branch1Task.py"}, {"a": "b", "functionName": "Branch2Task.py"}, {"a": "b", "functionName": "Branch3Task.py"}]

        testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

        test = MFNTest(test_name="Parallel", workflow_filename="workflow_parallel_state_test.json")
        test.exec_tests(testtuplelist)

    def test_parallel_fun_with_math(self):
        """ creates and executes the parallel fun with math workflow from the ASL description """
        testtuplelist = []

        event = [3, 2]
        expectedResponse = [5, 1]
        testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

        event = [5, 1]
        expectedResponse = [6, 4]
        testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

        test = MFNTest(test_name="Parallel Fun with Math", workflow_filename="workflow_parallel_state_fun_test.json")
        test.exec_tests(testtuplelist)
