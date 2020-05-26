#   Copyright 2020 The microfunctions Authors
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
#

# Map state test motivated by stackovercloud article "New  Step Functions Support for Dynamic Parallelism"
# https://www.stackovercloud.com/2019/09/18/new-step-functions-support-for-dynamic-parallelism/

import unittest
import os, sys
import json
import time

sys.path.append("../")
from mfn_test_utils import MFNTest

class MapStateHardcodedTest(unittest.TestCase):

    def test_map_state(self):
            """ creates and executes the Map state test workflow from the ASL description """

            testtuplelist = []
                         
            event = {
  "orderId": "12345678",
  "orderDate": "20190820101213",
  "detail": {
    "customerId": "1234",
    "deliveryAddress": "123, Seattle, WA",
    "deliverySpeed": "1-day",
    "paymentMethod": "aCreditCard",
    "items": [
      {
        "productName": "Agile Software Development",
        "category": "book",
        "price": 60.0,
        "quantity": 1
      },
      {
        "productName": "Domain-Driven Design",
        "category": "book",
        "price": 32.0,
        "quantity": 1
      },
      {
        "productName": "The Mythical Man Month",
        "category": "book",
        "price": 18.0,
        "quantity": 1
      },
      {
        "productName": "The Art of Computer Programming",
        "category": "book",
        "price": 180.0,
        "quantity": 1
      },
      {
        "productName": "Ground Coffee, Dark Roast",
        "category": "grocery",
        "price": 8.0,
        "quantity": 6
      }
    ]
  }
}
            """
            expectedResponse = {"summary": "This is a test summary!", "processedItems": [{"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Agile Software Development", "category": "book", "price": 60.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Domain-Driven Design", "category": "book", "price": 32.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "The Mythical Man Month", "category": "book", "price": 18.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "The Art of Computer Programming", "category": "book", "price": 180.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Ground Coffee, Dark Roast", "category": "grocery", "price": 8.0, "quantity": 6}}]}
            """

            expectedResponse = {"summary": "This is a test summary!", "detail": {"processedItems": [{"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Agile Software Development", "category": "book", "price": 60.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Domain-Driven Design", "category": "book", "price": 32.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "The Mythical Man Month", "category": "book", "price": 18.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "The Art of Computer Programming", "category": "book", "price": 180.0, "quantity": 1}}, {"deliveryAddress": "123, Seattle, WA", "item": {"productName": "Ground Coffee, Dark Roast", "category": "grocery", "price": 8.0, "quantity": 6}}]}}            

            testtuplelist.append((json.dumps(event), json.dumps(expectedResponse)))
        
            test = MFNTest(test_name="Map State Input Items Result Output Path Test", workflow_filename="workflow_map_state_ior_path_test.json" ) 

            st = time.time()
            test.exec_tests(testtuplelist)
            et = time.time()

            print ("test duration (s): %s" % str(et-st))

