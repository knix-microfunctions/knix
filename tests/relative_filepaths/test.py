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

class HelloWorldTest(unittest.TestCase):

    #@unittest.skip("")
    def test_relative_filepaths(self):
        test_tuple_list=[]
        inp0 = "echo"
        res0 = "Opening a file using a relative path in the function code works!"

        test_tuple_list.append((json.dumps(inp0), json.dumps(res0)))

        test = MFNTest(test_name='relative_filepaths', workflow_filename='relative_filepaths.json')
        test.exec_tests(test_tuple_list)

