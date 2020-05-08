#   Copyright 2020 The microfunctions Authors
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
#
import unittest
import os, sys
import json
import time

sys.path.append("../")
from mfn_test_utils import MFNTest

class MapStateTest(unittest.TestCase):

    def test_map_state_context_data(self):
            """ creates and executes the Map state test workflow from the ASL description """

            testtuplelist = []

            event = [{"who": "bob"},{"who": "meg"},{"who": "joe"}]                         
            expectedResponse = [{"ContextValue": {"who": "bob"}, "ContextIndex": 0},{"ContextValue": {"who": "meg"}, "ContextIndex": 1}, {"ContextValue": {"who": "joe"}, "ContextIndex": 2 }]

            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))
        
            test = MFNTest(test_name="Map State Context Object Test", workflow_filename="workflow_map_state_context_test.json" ) 

            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()

            print ("test duration (s): %s" % str(et-st))

