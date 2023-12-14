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
#import time

sys.path.append("../")
from mfn_test_utils import MFNTest

class TensorFlowTest(unittest.TestCase):

    """ Example ASL state test with Tensorflow

    """
    def test_tensorflow(self):
        """  testing tensorflow """

        inp1 = '"abc"'
        #res1 = '"Hello from Tensorflow 2.1.0"'

        res1 = '"GPU available: True"'

        testtuplelist =[(inp1, res1)]
        test = MFNTest(test_name = "Tensorflow__Test", gpu_usage = "50", gpu_mem_usage="10")

        #time.sleep(10) # wait for deployment
        test.exec_tests(testtuplelist)

