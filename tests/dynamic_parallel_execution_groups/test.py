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

class DynamicParallelExecutionGroupsTest(unittest.TestCase):

    #@unittest.skip("")
    def test_wordcount(self):
        # test parameters
        size=100
        num_mappers = 5
        ##

        test_tuple_list = []

        data = self._get_wordcount_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_wordcount_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "wordcount"
        job["input_format"] = "string"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    #@unittest.skip("")
    def test_wordcount_nested(self):
        # test parameters
        size = 5000
        num_mappers = 10
        ##

        test_tuple_list = []

        data = self._get_wordcount_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_wordcount_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "wordcount"
        job["input_format"] = "string"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        # add a condition for the mappers, so that they can create more PEGs
        # dynamically if any condition is met
        event["mapper_conditions"] = {}
        # this ensures that there will be at least another level of dynamic PEG
        max_len = int(size * 5 / num_mappers / 2)
        #print("max len: " + str(max_len))
        event["mapper_conditions"]["max_len"] = max_len

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    #@unittest.skip("")
    def test_mergesort(self):
        # test parameters
        size = 200
        # mergesort's reducers need to work with 2 mapper outputs (i.e., merge operation)
        num_mappers = 2
        ##

        test_tuple_list = []

        data = self._get_mergesort_data(size=size)

        ts_start_simple = time.time() * 1000.0
        expected_output = self._get_mergesort_expected_result(data)
        total_time_simple = time.time() * 1000.0 - ts_start_simple

        job = {}
        job["type"] = "mergesort"
        job["input_format"] = "array"

        event = {}
        event["job"] = job
        event["data"] = data
        event["num_mappers"] = num_mappers

        # add a condition for the mappers, so that they can create more PEGs
        # dynamically if any condition is met
        event["mapper_conditions"] = {}
        max_len = int(size / num_mappers / 5)
        #print("max len: " + str(max_len))
        event["mapper_conditions"]["max_len"] = 10

        test_tuple_list.append((json.dumps(event), json.dumps(expected_output)))

        test = MFNTest(workflow_filename="wf_mapreduce.json")

        ts_start = time.time() * 1000.0
        test.exec_tests(test_tuple_list)
        total_time = time.time() * 1000.0 - ts_start

        print(job["type"])
        print("Simple time total (ms): " + str(total_time_simple))
        print("MFN time total (ms): " + str(total_time))

    ####################
    # internal functions
    ####################

    def _get_wordcount_data(self, size=50):
        data = ""
        for i in range(size):
            data += "a quick brown fox jumped over the lazy dog\n"
            data += "the lazy dog got jumped over by a quick brown fox\n"
            data += "a brown fox is not really brown but orange\n"
            data += "the lazy dog is not really lazy but friendly to brown foxes\n"
            data += "even if the brown foxes are really orange and not brown\n"

        # remove last newline "\n"
        return data.rstrip()

    def _get_mergesort_data(self, size=50):
        data = []
        for i in range(size):
            data.append(random.randint(0, 1000000))

        return data

    def _get_wordcount_expected_result(self, data):
        expected_result = {}
        words = []
        lines = data.split("\n")
        for line in lines:
            words += line.split(" ")
        for word in words:
            if word == "":
                continue
            if word not in expected_result:
                expected_result[word] = 0
            expected_result[word] += 1

        return expected_result

    def _get_mergesort_expected_result(self, data):
        data.sort()
        return data

def main():
    unittest.main()

if __name__ == '__main__':
    main()

