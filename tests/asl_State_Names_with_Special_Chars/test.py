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

class CallCenterTest(unittest.TestCase):

    """ Example ASL Call Center workflow    

    """
    def test_cc(self):
        for nn in ["whitespaces", "other_special_chars"]:
            """ creates and executes the Call Center state test with test data """

            # build pairs of input and expected output values
            testtuplelist = [('{"inputCaseID": "001"}', '{"Case": "001", "Status": 1, "Message": "Case 001: opened...assigned...closed."}')]
            # define the test
            test = MFNTest(test_name="State Names with special chars test", workflow_filename=("workflow_state_name_characters_test_%s.json" % nn))
            # execute the test
            test.exec_keys_check(testtuplelist)

