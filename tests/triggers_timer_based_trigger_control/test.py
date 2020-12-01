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
    def test_triggers_timer_based_trigger_control(self):
        test = MFNTest(test_name='triggers_timer_based_trigger_control',
                       workflow_filename='wf_triggers_timer_based_trigger_control.json')

        time.sleep(5)
        print("Executing test")
        # ["wf_triggers_timer_based_trigger_control", "trigger_amqp_to_be_controlled_nonce", "amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost", "rabbit.*.*", "egress_exchange", "trigger_timer_controller_nonce", 20000]

        nonce = str(int(time.time() * 1000))
        curr_hostname = socket.gethostname()

        input_data = []
        workflowname = "wf_triggers_timer_based_trigger_control"
        trigger_name_amqp = "trigger_amqp_to_be_controlled_" + nonce
        amqp_addr = "amqp://rabbituser:rabbitpass@" + curr_hostname + ":5672/%2frabbitvhost"
        routingkey = "rabbit.*.*"
        routingkey_to_expect = "rabbit.routing.key"
        exchange = "egress_exchange"
        trigger_name_timer = "trigger_timer_controller_" + nonce
        ttl = 20000

        input_data.append(workflowname)
        input_data.append(trigger_name_amqp)
        input_data.append(amqp_addr)
        input_data.append(routingkey)
        input_data.append(exchange)
        input_data.append(trigger_name_timer)
        input_data.append(ttl)

        response = test.execute(input_data)

        time.sleep((float(ttl)/1000.0) + 10)

        print("Shutting down rabbitmq and publisher")
        pub.terminate()
        rabbit.terminate()
        subprocess.Popen(["scripts/stop_local_rabbitmq.sh"])
        
        time.sleep(5)

        counter_state_1 = 0
        counter_state_2 = 0

        counter_state_1_error = 0
        counter_state_2_error = 0

        logs = test.get_workflow_logs()
        wflog = logs["log"]
        log_lines = wflog.split("\n")

        for line in log_lines:
            if "_!_TRIGGER_START_" + trigger_name_amqp + ";timer_based_trigger_control;" + workflowname + ";" + routingkey_to_expect + ";" in line.strip():
                counter_state_1 = counter_state_1 + 1
                print(line.strip())

            if "_!_TRIGGER_ERROR_" + trigger_name_amqp + ";timer_based_trigger_control;" + workflowname + ";;" in line.strip():
                counter_state_1_error = counter_state_1_error + 1
                print(line.strip())

            if "_!_TRIGGER_START_" + trigger_name_timer + ";timer_based_trigger_control_state2;" + workflowname + ";;" in line.strip():
                counter_state_2 = counter_state_2 + 1
                print(line.strip())

            if "_!_TRIGGER_ERROR_" + trigger_name_timer + ";timer_based_trigger_control_state2;" + workflowname + ";;" in line.strip():
                counter_state_2_error = counter_state_2_error + 1
                print(line.strip())


        if counter_state_1 >=20 and counter_state_2 == 1 and counter_state_1_error == 0 and counter_state_2_error == 0:
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
