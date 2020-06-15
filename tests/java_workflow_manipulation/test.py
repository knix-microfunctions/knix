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

class JavaWorkflowManipulationTest(unittest.TestCase):

    #@unittest.skip("")
    def test_workflow_manipulation_java(self):
        test = MFNTest(workflow_filename="wf_workflow_manipulation_java.json")
        test_tuples = []
        test_tuples.append(('"float addWorkflowNext"', '"final_42.0_addWorkflowNext"'))
        test_tuples.append(('"float addDynamicNext"', '"final_42.0_addDynamicNext"'))
        test_tuples.append(('"float addDynamicWorkflowTrigger"', '"final_42.0_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"float addDynamicWorkflowTriggerList"', '"final_42.0_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"int addWorkflowNext"', '"final_42_addWorkflowNext"'))
        test_tuples.append(('"int addDynamicNext"', '"final_42_addDynamicNext"'))
        test_tuples.append(('"int addDynamicWorkflowTrigger"', '"final_42_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"int addDynamicWorkflowTriggerList"', '"final_42_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"double addWorkflowNext"', '"final_42.0_addWorkflowNext"'))
        test_tuples.append(('"double addDynamicNext"', '"final_42.0_addDynamicNext"'))
        test_tuples.append(('"double addDynamicWorkflowTrigger"', '"final_42.0_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"double addDynamicWorkflowTriggerList"', '"final_42.0_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"list addWorkflowNext"', '"final_[myelement]_addWorkflowNext"'))
        test_tuples.append(('"list addDynamicNext"', '"final_[myelement]_addDynamicNext"'))
        test_tuples.append(('"list addDynamicWorkflowTrigger"', '"final_[myelement]_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"list addDynamicWorkflowTriggerList"', '"final_[myelement]_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"string addWorkflowNext"', '"final_mystring_addWorkflowNext"'))
        test_tuples.append(('"string addDynamicNext"', '"final_mystring_addDynamicNext"'))
        test_tuples.append(('"string addDynamicWorkflowTrigger"', '"final_mystring_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"string addDynamicWorkflowTriggerList"', '"final_mystring_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"dict addWorkflowNext"', '"final_{mykey=true}_addWorkflowNext"'))
        test_tuples.append(('"dict addDynamicNext"', '"final_{mykey=true}_addDynamicNext"'))
        test_tuples.append(('"dict addDynamicWorkflowTrigger"', '"final_{mykey=true}_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"dict addDynamicWorkflowTriggerList"', '"final_{mykey=true}_addDynamicWorkflowTriggerList"'))

        test_tuples.append(('"something_else addWorkflowNext"', '"final_null_addWorkflowNext"'))
        test_tuples.append(('"something_else addDynamicNext"', '"final_null_addDynamicNext"'))
        test_tuples.append(('"something_else addDynamicWorkflowTrigger"', '"final_null_addDynamicWorkflowTrigger"'))
        test_tuples.append(('"something_else addDynamicWorkflowTriggerList"', '"final_null_addDynamicWorkflowTriggerList"'))

        test.exec_tests(test_tuples)

def main():
    unittest.main()

if __name__ == '__main__':
    main()

