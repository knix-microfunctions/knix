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

class RetryTest(unittest.TestCase):

    """ Example ASL state test

    """

    def test_retry(self):
        """ creates and executes the retry policy from an ASL description """
        # build pairs of input and expected output values

        inp0 = '[1,2]'
        inp1 = '""'
        inp2 = '{}'
        inp3 = '0'
        res0 = '{"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "States.All"}'
        res1 = '{"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "FailFunction.py does not like this value!"}'
        res2 = '{"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "FailFunction.py does not like this type!"}'
        res3 = '{"Cause": "Error not caught by MFn ASL Workflow retryer", "Error": "FailFunction.py does not like this value!"}'

        testtuplelist =[(inp0, res0), (inp1, res1), (inp2, res2), (inp3, res3)]

        test = MFNTest(test_name = "Retry Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

