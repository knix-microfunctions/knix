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

class JavaDataLayerOpsTest(unittest.TestCase):

    #@unittest.skip("")
    def test_datalayer_ops_java(self):
        test = MFNTest(workflow_filename="wf_datalayer_ops_java.json")
        response = test.execute("test")

        passed = []
        failed = []
        for name in response:
            if response[name]:
                passed.append(name)
            else:
                failed.append(name)

        for name in passed:
            test.report(True, name, "", "")

        for name in failed:
            test.report(False, name, "", "")

        print("----------")
        test.undeploy_workflow()
        test.cleanup()

def main():
    unittest.main()

if __name__ == '__main__':
    main()

