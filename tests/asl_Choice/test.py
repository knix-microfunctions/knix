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

class ChoiceStateTest(unittest.TestCase):

    """ Example ASL state test

    """
    def test_choice(self):
        """ creates and executes the Choice state test with test data """
        # build pairs of input and expected output values

        testtuplelist = [('{"value": 22, "type": "Private"}', '{"type": "Private", "functionName": "ValueInTwenties.py", "value": 22}'),
             ('{"value": 0, "type": "Private"}', '{"type": "Private", "functionName": "ValueIsZero.py", "value": 0}'),
             ('{"value": 22, "type": "Public"}', '{"type": "Public", "functionName": "Public.py", "value": 22}'),
             ('{"value": 4711, "type": "Private"}', '{"type": "Private", "value": 4711}')]

        test = MFNTest(test_name = "Choice State Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

