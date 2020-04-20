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

class LoopIterationTest(unittest.TestCase):

    """ Example ASL state test

    """
    def test_loop_iteration(self):
        """  testing iteration loop with sample data """

        # pairs of input and expected output values

        inp0 = '{"Comment": "Test my Iterator function", "iterator": {"count": 10,"index": 5,"step": 1}}'
        res0 = '{"Comment": "Test my Iterator function", "result": {"success": true}, "iterator": {"count": 10, "index": 10, "step": 1, "continue": false}}'

        inp1 = '{"Comment": "Test my Iterator function", "iterator": {"count": 20,"index": 5,"step": 1}}'
        res1 = '{"Comment": "Test my Iterator function", "result": {"success": true}, "iterator": {"count": 20, "index": 20, "step": 1, "continue": false}}'

        testtuplelist =[(inp0, res0), (inp1, res1)]

        test = MFNTest(test_name = "Loop Iteration Test")
        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

