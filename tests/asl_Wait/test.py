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
from datetime import datetime, date, time, timedelta
sys.path.append("../")
from mfn_test_utils import MFNTest

class WaitStateTest(unittest.TestCase):

    """ Example ASL state test

    """
    def test_wait(self):
        """  testing  wait state with sample data """

        test = MFNTest(test_name = "Wait State Test")

        # pairs of input and expected output values
        now = datetime.utcnow()
        now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        soon = now + timedelta(seconds = 20)
        soon_str=soon.strftime('%Y-%m-%dT%H:%M:%SZ')

        inp0 = '{"expirydate": "%s"}' %  soon_str
        res0 = inp0

        testtuplelist =[(inp0, res0)]

        test.exec_tests(testtuplelist)
        #print(str(test.exec_only('"a"')))

