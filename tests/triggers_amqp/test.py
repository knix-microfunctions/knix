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
import random
import sys
import time
import unittest
import socket
import os
import subprocess

sys.path.append("../")
from mfn_test_utils import MFNTest

print("Starting rabbitmq")
rabbit = subprocess.Popen(["scripts/run_local_rabbitmq.sh"])
time.sleep(20)
print("Starting publisher")
pub = subprocess.Popen(["scripts/run_local_publisher.sh"])
time.sleep(10)
os.system("scripts/run_local_subscriber.sh")
print("Publisher is ready")

class TriggersAmqpTest(unittest.TestCase):
    # @unittest.skip("")
    def test_triggers_storage(self):
        test = MFNTest(test_name='triggers_amqp',
                       workflow_filename='wf_triggers_amqp.json')

        time.sleep(5)
        print("Executing test")
        nonce = str(int(time.time() * 1000))

        curr_hostname = socket.gethostname()

        input_data = []
        workflowname = "wf_triggers_amqp"
        routingkey_to_expect = "rabbit.routing.key"
        routingkey = "rabbit.*.*"
        input_data.append(workflowname)
        input_data.append(nonce)
        input_data.append("amqp://rabbituser:rabbitpass@" + curr_hostname + ":5672/%2frabbitvhost")
        input_data.append(routingkey)
        input_data.append("egress_exchange")

        response = test.execute(input_data)

        time.sleep(2)

        counter_state_1 = 0
        counter_state_2 = 0

        counter_state_1_error = 0
        counter_state_2_error = 0

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        for line in log_lines:
            if "_!_TRIGGER_START_" + nonce + ";triggers_amqp;" + workflowname + ";" + routingkey_to_expect + ";" in line.strip():
                counter_state_1 = counter_state_1 + 1
                print(line.strip())

            if "_!_TRIGGER_ERROR_" + nonce + ";triggers_amqp;" + workflowname + ";;" in line.strip():
                counter_state_1_error = counter_state_1_error + 1
                print(line.strip())

            if "_!_TRIGGER_START_" + nonce + ";triggers_amqp_state2;" + workflowname + ";" + routingkey_to_expect + ";" in line.strip():
                counter_state_2 = counter_state_2 + 1
                print(line.strip())

            if "_!_TRIGGER_ERROR_" + nonce + ";triggers_amqp_state2;" + workflowname + ";;" in line.strip():
                counter_state_2_error = counter_state_2_error + 1
                print(line.strip())


        print("Force stopping AMQP broker and checking for error message propagation")
        pub.terminate()
        rabbit.terminate()
        subprocess.Popen(["scripts/stop_local_rabbitmq.sh"])
        
        time.sleep(50)

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        for line in log_lines:

            if "_!_TRIGGER_ERROR_" + nonce + ";triggers_amqp;" + workflowname + ";;" in line.strip():
                counter_state_1_error = counter_state_1_error + 1
                print(line.strip())

            if "_!_TRIGGER_ERROR_" + nonce + ";triggers_amqp_state2;" + workflowname + ";;" in line.strip():
                counter_state_2_error = counter_state_2_error + 1
                print(line.strip())


        if counter_state_1 >=2 and counter_state_2 >=4 and counter_state_1_error == 0 and counter_state_2_error == 1:
            print("Number of state1 triggers: " + str(counter_state_1))
            print("Number of state2 triggers: " + str(counter_state_2))
            print("Number of state1 error triggers: " + str(counter_state_1_error))
            print("Number of state1 error triggers: " + str(counter_state_2_error))
            test.report(True, str(input_data), input_data, response)
        else:
            print("Number of state1 triggers: " + str(counter_state_1))
            print("Number of state2 triggers: " + str(counter_state_2))
            print("Number of state1 error triggers: " + str(counter_state_1_error))
            print("Number of state1 error triggers: " + str(counter_state_2_error))
            test.report(False, str(input_data), input_data, response)
            for line in log_lines:
                print(line.strip())

        test.undeploy_workflow()
        test.cleanup()
