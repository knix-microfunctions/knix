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

class IOProcessingTest(unittest.TestCase):

    """ Example ASL state test

    """
    def test_io_processing(self):
        """  testing I/O path processing with sample data """

        # pairs of input and expected output values

        inp1 = '{"comment": "An input comment.","data": {"val1": 23,"val2": 17 }, "extra": "foo", "lambda": {"who": "AWS Step Functions" }}'
        inp2 = '{"comment": "An input comment.","data": {"val1": 23,"val2": 17,"lambdaresult": "Hello, AWS Step Functions!"},"extra": "foo","lambda": {"who": "AWS Step Functions" }}'
        res1 = '{"val1": 23, "val2": 17}'
        res2 = '{"val1": 23, "val2": 17,"lambdaresult": "Hello, AWS Step Functions!"}'

        testtuplelist =[(inp1, res1), (inp2, res2)]
        test = MFNTest(test_name = "I/O Processing Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

