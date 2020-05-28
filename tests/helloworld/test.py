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
    """ Example Hello World Test

    There's various ways to bundle tests. This class uses the fixtures setUpClass and tearDownClass to get a client, but it could also use it to
    create/delete the workflow and function and store them as class members to have them created only once.

    The run of python unittest from the Makefile will find this class as it is derived from unittest.TestCase and it will check for
    its methods named 'test_*()' to run tests (unless the tests are otherwise assembled in an __init__.py by a load_tests function (see unittest convention)
    """

    #@unittest.skip("")
    def test_helloworld_asl(self):
        """ creates and executes the hello world workflow from an ASL description """
        event = {"Hello,": "World!"}
        testtuplelist = [(json.dumps(event), '{"Hello,": "World!"}')]

        test = MFNTest(test_name="Hello World ASL", workflow_filename="helloworld-asl.json")
        test.exec_tests(testtuplelist)

    #@unittest.skip("")
    def test_helloworld_wfd(self):
        """ creates and executes the hello world workflow from a KNIX MicroFunctions workflow description """
        event = {"Hello,": "World!"}
        testtuplelist = [(json.dumps(event), '{"Hello,": "World!"}')]

        test = MFNTest(test_name="Hello World KNIX MicroFunctions", workflow_filename="helloworld-knix.json")
        test.exec_tests(testtuplelist)
