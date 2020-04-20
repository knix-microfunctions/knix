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

class SucceedStateTest(unittest.TestCase):

    """ Example ASL state test

    """
    def test_succeed(self):
        # build pairs of input and expected output values

        inp0 = '{"fail test": "aabbcc"}'
        res0 = inp0
        inp1 = '"aabbcc"'
        res1 = inp1

        testtuplelist =[(inp0, res0), (inp1, res1)]

        test = MFNTest(test_name = "Succeed State Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

