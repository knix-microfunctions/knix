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
import sys
import time
from random import randint

import unittest

sys.path.append("../")
from mfn_test_utils import MFNTest

class StateResourceNameDecouplingTest(unittest.TestCase):

    #@unittest.skip("")
    def test_empty_input(self):
        test_tuple_list = []

        event = []
        expected_output = ["A", "B", "C", "D", "E"]

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="workflow_state_resource.json")
        test.exec_tests(test_tuple_list)

    #@unittest.skip("")
    def test_non_empty_input(self):
        test_tuple_list = []

        event = ["a", "b", "c"]
        expected_output = ["a", "b", "c", "D", "E"]

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="workflow_state_resource.json")
        test.exec_tests(test_tuple_list)

def main():
    unittest.main()

if __name__ == '__main__':
    main()

