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

import datetime
import json
import random
import sys
import time
import unittest

sys.path.append("../")
from mfn_test_utils import MFNTest

class JavaCatchRetryTest(unittest.TestCase):

    #@unittest.skip("")
    def test_catch_java(self):
        """ creates and executes the catch policy from an ASL description """
        # build pairs of input and exepcted output values
        testtuplelist = []

        inp0 = {"invalid_all": "test"}
        res0 = {"invalid_all": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "States.All"}}

        testtuplelist.append((json.dumps(inp0), json.dumps(res0)))

        inp1 = {"invalid_value": "test"}
        res1 = {"invalid_value": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "java.lang.StringIndexOutOfBoundsException"}}

        testtuplelist.append((json.dumps(inp1), json.dumps(res1)))

        inp2 = {"invalid_type": "test"}
        res2 = {"invalid_type": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "java.lang.NumberFormatException"}}

        testtuplelist.append((json.dumps(inp2), json.dumps(res2)))

        inp3 = {"invalid_denominator": "test"}
        res3 = {"invalid_denominator": "test", "error": {"Cause": "this error caught by MFn ASL Workflow catcher!", "Error": "java.lang.ArithmeticException"}}

        testtuplelist.append((json.dumps(inp3), json.dumps(res3)))

        test = MFNTest(test_name="Java Catch Test", workflow_filename="wf_java_catch.json")
        test.exec_tests(testtuplelist)

    #@unittest.skip("")
    def test_retry_java(self):
        """ creates and executes the catch policy from an ASL description """
        # build pairs of input and exepcted output values
        testtuplelist = []

        inp0 = {"invalid_all": "test"}
        res0 = {"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "States.All"}

        testtuplelist.append((json.dumps(inp0), json.dumps(res0)))

        inp1 = {"invalid_value": "test"}
        res1 = {"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "java.lang.StringIndexOutOfBoundsException"}

        testtuplelist.append((json.dumps(inp1), json.dumps(res1)))

        inp2 = {"invalid_type": "test"}
        res2 = {"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "java.lang.NumberFormatException"}

        testtuplelist.append((json.dumps(inp2), json.dumps(res2)))

        inp3 = {"invalid_denominator": "test"}
        res3 = {"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "java.lang.ArithmeticException"}

        testtuplelist.append((json.dumps(inp3), json.dumps(res3)))

        test = MFNTest(test_name="Java Retry Test", workflow_filename="wf_java_retry.json")
        test.exec_tests(testtuplelist)

def main():
    unittest.main()

if __name__ == '__main__':
    main()

