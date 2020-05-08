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

    def test_map_state(self):
            """ creates and executes the Map state test workflow from the ASL description """

            testtuplelist = []
                         
            event = {"ship-date": "2016-03-14T01:59:00Z", 
                     "detail": 
                         {"delivery-partner": "UQS",
                          "shipped": [
                             { "prod": "R31", "dest-code": 9511, "quantity": 1344 },
                             { "prod": "S39", "dest-code": 9511, "quantit_y": 40 },
                             { "prod": "R31", "dest-code": 9833, "quantity": 12 },
                             { "prod": "R40", "dest-code": 9860, "quantity": 887 },
                             { "prod": "R40", "dest-code": 9511, "quantity": 1220 }
                                     ]
                         }
            }                     

            expectedResponse = {"detail": {"shipped": ["All keys are OK!", "item OK!", "All keys are OK!", "All keys are OK!", "All keys are OK!"]}}

            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))
        
            test = MFNTest(test_name="Map State Test", workflow_filename="workflow_map_state_example_test.json" ) 

            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()

            print ("test duration (s): %s" % str(et-st))

