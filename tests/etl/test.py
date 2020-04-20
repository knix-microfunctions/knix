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

class ExtractTransformLoadTest(unittest.TestCase):

    """ Example ASL ETL test

    """
    def test_etl(self):
        """ creates and executes the an Extract Transform Load sample workflow with external services """
        # build pairs of input and expected output values

        res = {"data": {"success": "true","key": "OefxUg","link": "https://file.io/OefxUg","expiry":"14 days"},"source": "associated-press"}
        testtuplelist = [('{"key":"d39fe5583c934eb18978ecde1040bbca", "source": "associated-press"}', res)]

        test = MFNTest(test_name="MICROFUNCTIONS ETL Test")
        test.exec_keys_check(testtuplelist)

