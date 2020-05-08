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

class MapStateHardcodedTest(unittest.TestCase):

    def test_map_state(self):
            """ creates and executes the Map state test workflow from the ASL description """

            testtuplelist = []
                         
            event = "trigger map state input"
            #expectedResponse = ["Iterate", "Over", "This", "Array"] 
            expectedResponse = [{"Value": "Iterate", "Index": 0}, {"Value": "Over", "Index": 1}, {"Value": "This", "Index": 2}, {"Value": "Array", "Index": 3}]

            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))
        
            test = MFNTest(test_name="Map State Hardcoded Input Test", workflow_filename="workflow_map_state_hardcoded_test.json" ) 

            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()

            print ("test duration (s): %s" % str(et-st))

