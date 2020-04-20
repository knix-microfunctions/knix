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

sys.path.append("../")
from mfn_test_utils import MFNTest

class CatchTest(unittest.TestCase):
    """
    Example ASL state test
    """

    def test_catch(self):
        """ creates and executes the catch policy from an ASL description """
        # build pairs of input and exepcted output values
        testtuplelist = []

        inp0 = {"invalid_all": "test"}
        res0 = {"invalid_all": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "States.All"}}

        testtuplelist.append((json.dumps(inp0), json.dumps(res0)))


        inp1 = {"invalid_value": "test"}
        res1 = {"invalid_value": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "FailFunction.py does not like this value!"}}

        testtuplelist.append((json.dumps(inp1), json.dumps(res1)))

        inp2 = {"invalid_type": "test"}
        res2 = {"invalid_type": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "FailFunction.py does not like this type!"}}

        testtuplelist.append((json.dumps(inp2), json.dumps(res2)))

        inp3 = {"invalid_denominator": "test"}
        res3 = {"invalid_denominator": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "FailFunction.py does not like this value!"}}

        testtuplelist.append((json.dumps(inp3), json.dumps(res3)))

        test = MFNTest(test_name = "Catch Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

