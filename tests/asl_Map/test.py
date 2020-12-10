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
#import ast

sys.path.append("../")
from mfn_test_utils import MFNTest

class MapStateTest(unittest.TestCase):
    """
    event = '[{"who": "bob"},{"who": "meg"},{"who": "joe"}]'
    expectedResponse = '[{"ContextValue": {"who": "bob"}, "ContextIndex": 0},{"ContextValue": {"who": "meg"}, "ContextIndex": 1}, {"ContextValue": {"who": "joe"}, "ContextIndex": 2 }]'
    test_map = [("asl_Map_State_Context_Data", "wfms_context_test/wfms_context_test.json", [(event, expectedResponse)])]
    """

    def test_map_state(self):
        file_list = ["wfms_delivery_test.data",
                     "wfms_context_test.data",
                     "wfms_example_test.data",
                     "wfms_parameters_test.data",
                     "wfms_thingspiratessay_test.data",
                     "wfms_iro_paths_processing_test.data",
                     "wfms_hardcoded_test.data"
                     ]

        for file in file_list:
          with open(file) as json_input:
            testtuplelist = []
            data = json.load(json_input)
            testtuplelist.append((json.dumps(data["event"]), json.dumps(data["expectedResponse"])))
            test = MFNTest(test_name=data["test_name"], workflow_filename=data["workflow_name"])
            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()
            print ("test duration (s): %s" % str(et-st))

        
        for mc in range(0): # set maxConcurrency parameter
            """ creates and executes the Map state test workflow from the ASL description """

            testtuplelist = []

            event = [{"who": "bob"}, {"who": "meg"}, {"who": "joe"}]
            expectedResponse = ["Hello, bob!", "Hello, meg!", "Hello, joe!"]
            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

            event = [{"who": "meg"}, {"who": "joe"}, {"who": "bob"}]
            expectedResponse = ["Hello, meg!", "Hello, joe!", "Hello, bob!"]
            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

            event = [{"who": "joe"}, {"who": "bob"}, {"who": "meg"}]
            expectedResponse = ["Hello, joe!", "Hello, bob!", "Hello, meg!"]
            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

            event = [{"who": "joe"}, {"who": "bob"}, {"who": "meg"}, {"who":"dave"}, {"who":"tom"}, {"who":"ray"}]
            expectedResponse = ["Hello, joe!", "Hello, bob!", "Hello, meg!", "Hello, dave!", "Hello, tom!", "Hello, ray!"]
            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))

            test = MFNTest(test_name="Map State Test", workflow_filename=("wfms_test_mc%s.json" % mc))

            print("MaxConcurrency level: %i " % mc)

            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()

            print ("test duration (s): %s" % str(et-st))
