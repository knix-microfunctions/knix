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

class ContextTest(unittest.TestCase):

    """ Example ASL context object test

    """
    def test_task_context(self):
        """  testing task chain """

        inp0 = '{"object_test": "aabbcc"}'
        res0 = {'log_stream_name': '2020/08/07[$LATEST]ContextTest', 'log_group_name': '/knix/mfn/ContextTest', 'aws_request_id': '8f7bdefed89511ea92ab0242ac110003', 'memory_limit_in_mb': None, 'context_identity': None, 'client_context': None, 'get_remaining_time_in_millis': 300000}


        testtuplelist =[(inp0, res0)]

        test = MFNTest(test_name = "Context Object Test")
        test.exec_tests(testtuplelist, check_just_keys=True)

