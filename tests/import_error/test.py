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
import unittest
import sys

sys.path.append("../")
from mfn_test_utils import MFNTest

class ImportErrorTest(unittest.TestCase):

    #@unittest.skip("")
    def test_import_error(self):
        test_tuple_list=[]

        test = MFNTest(test_name='import_error', workflow_filename='wf_import_error.json')
        deployment_error = test.get_deployment_error()
        expected_error = "ERROR: Could not find a version that satisfies the requirement numpyu"
        if deployment_error.find(expected_error) != -1:
            test.report(True, "import error report success", None, None)
        else:
            test.report(False, "import error report failure", expected_error, deployment_error)

        test.undeploy_workflow()
        test.cleanup()

