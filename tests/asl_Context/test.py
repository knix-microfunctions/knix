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

        inp0 = '"abc"'
        res0 = {
    "context.function_name": "test_context",
    "context.function_version": 1,
    "context.log_stream_name": "2020/08/10[$LATEST]test_context",
    "context.log_groupm_name": "/knix/mfn/test_context",
    "context.aws_request_id": "4f7abd01dae811ea92500242ac110005",
    "context.memory_limit_in_mb": None,
    "context.identity.cognito_identity_id": "cognito_identity_id",
    "context.identity.cognito_identity_pool_id": "cognito_identity_pool_id",
    "context.client_context.client": "<MicroFunctionsAPI.MicroFunctionsAPI.__init__.<locals>.LambdaClientContextMobileClient object at 0x7fb2a0fc7400>",
    "context.client_context.custom": "{'custom': True}",
    "context.client_context.env": "{'env': 'test'}",
    "context.client_context.client.installation_id": "installation_id",
    "context.client_context.client.app_title": "app_title",
    "context.client_context.client.app_version_name": "app_version_name",
    "context.client_context.client.app_version_code": "app_version_code",
    "context.client_context.client.app_package_name": "app_package_name",
    "context.get_remaining_time_in_millis": 300000
}


        testtuplelist =[(inp0, res0)]

        test = MFNTest(test_name = "Context Object Test")
        test.exec_tests(testtuplelist, check_just_keys=True)

