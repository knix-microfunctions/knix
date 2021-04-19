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

import functools
import hashlib
import json
import math
import random
import uuid
import os
import shlex
import statistics
import subprocess
import sys
import time
import ast

from mfn_sdk import MfnClient

class MfnAppTextFormat():
    COLOR_HEADER = '\033[95m'
    COLOR_BLUE = '\033[94m'
    COLOR_GREEN = '\033[92m'
    COLOR_RED = '\033[91m'

    STYLE_BOLD = '\33[1m'
    STYLE_UNDERLINE = '\033[4m'

    END = '\033[0m'

mfntestpassed = MfnAppTextFormat.STYLE_BOLD + MfnAppTextFormat.COLOR_GREEN + 'PASSED' + MfnAppTextFormat.END + MfnAppTextFormat.END
mfntestfailed = MfnAppTextFormat.STYLE_BOLD + MfnAppTextFormat.COLOR_RED + 'FAILED' + MfnAppTextFormat.END + MfnAppTextFormat.END

class MFNTest():
    def __init__(self, test_name=None, timeout=None, workflow_filename=None, new_user=False, delete_user=False, gpu_usage=None, gpu_mem_usage=None):

        self._settings = self._get_settings()

        if new_user:
            random_str = str(random.randint(0, 10000)) + "_" + str(time.time())
            random_user = hashlib.sha256(random_str.encode()).hexdigest()
            random_user = "test_" + random_user[0:31] + "@knix.io"
            print("User: " + random_user)
            self._client = MfnClient(mfn_user=random_user)
        else:
            print("User: " + self._settings["mfn_user"])
            self._client = MfnClient()

        if workflow_filename is None:
            self._workflow_filename = self._settings["workflow_description_file"]
        else:
            self._workflow_filename = workflow_filename

        ind = self._workflow_filename.rfind("/")
        if ind != -1:
            self._workflow_folder = self._workflow_filename[:ind+1]
        else:
            self._workflow_folder = "./"

        self._workflow_description = self._get_json_file(self._workflow_filename)

        if "name" in self._workflow_description:
            self._workflow_name = self._workflow_description["name"]
        else:
            self._workflow_name = self._workflow_filename[0:self._workflow_filename.rfind(".")]

        if test_name is not None:
            self._test_name = test_name
        else:
            self._test_name = self._workflow_filename

        if timeout is not None:
            self._settings["timeout"] = timeout

        if gpu_usage is not None:
            self._settings["gpu_usage"] = gpu_usage

        if gpu_mem_usage is not None:
            self._settings["gpu_mem_usage"] = gpu_mem_usage

        self._log_clear_timestamp = int(time.time() * 1000.0 * 1000.0)

        # will be the deployed workflow object in self._client
        self._workflow = None
        self._deployment_error = ""

        self._workflow_resources = []

        self.upload_workflow()
        self.deploy_workflow()
        time.sleep(15)

    def _get_json_file(self, filename):
        json_data = {}
        if os.path.isfile(filename):
            with open(filename) as json_file:
                json_data = json.load(json_file)
        return json_data

    def _get_settings(self):
        settings = {}
        # read default global settings files
        settings.update(self._get_json_file("../settings.json"))

        # read test specific settings
        settings.update(self._get_json_file("settings.json"))

        if len(settings) == 0:
            raise Exception("Empty settings")

        # Defaults
        settings.setdefault("timeout", 60)
        settings.setdefault("gpu_usage", "None")

        settings.setdefault("gpu_mem_usage", "None")

        return settings

    def _get_resource_info(self, resource_ref):
        #dir_list = next(os.walk('.'))[1]
        dir_list = next(os.walk(self._workflow_folder))[1]
        is_zip = False
        is_jar = False
        runtime = ""
        found = False
        if "zips" in dir_list:
            resource_filename = self._workflow_folder + "zips/" + resource_ref + ".zip"
            if os.path.isfile(resource_filename):
                found = True
                runtime = "Python 3.6"
                is_zip = True

        if not found:
            if "python" in dir_list:
                resource_filename = self._workflow_folder + "python/" + resource_ref + ".py"
                if os.path.isfile(resource_filename):
                    found = True
                    runtime = "Python 3.6"
            else:
                resource_filename = self._workflow_folder + resource_ref + ".py"
                if os.path.isfile(resource_filename):
                    found = True
                    runtime = "Python 3.6"

        if not found and "jars" in dir_list:
            resource_filename = self._workflow_folder + "jars/" + resource_ref + ".jar"
            if os.path.isfile(resource_filename):
                found = True
                runtime = "Java"
                is_jar = True

        if not found:
            if "java" in dir_list:
                resource_filename = self._workflow_folder + "java/" + resource_ref + ".java"
                if os.path.isfile(resource_filename):
                    found = True
                    runtime = "Java"
            else:
                resource_filename = self._workflow_folder + resource_ref + ".java"
                if os.path.isfile(resource_filename):
                    found = True
                    runtime = "Java"

        retval = {}
        retval["resource_filename"] = resource_filename
        retval["resource_runtime"] = runtime
        retval["is_zip"] = is_zip
        retval["is_jar"] = is_jar
        return retval

    def _get_resource_info_map(self, workflow_description=None, resource_info_map=None):
        if workflow_description is None:
            workflow_description = self._workflow_description
        if resource_info_map is None:
            resource_info_map = {}

        if "functions" in self._workflow_description:
            workflow_functions = workflow_description["functions"]
            for wf_function in workflow_functions:
                if "name" in wf_function:
                    resource_name = wf_function["name"]
                    resource_ref = resource_name
                    if "resource" in wf_function:
                        resource_ref = wf_function["resource"]

                    if resource_ref not in resource_info_map.keys():
                        resource_info = self._get_resource_info(resource_ref)
                        resource_info["resource_req_filename"] = "requirements/" + resource_ref + "_requirements.txt"
                        resource_info["resource_env_filename"] = "environment_variables/" + resource_ref + "_environment_variables.txt"
                        resource_info_map[resource_ref] = resource_info
                        #resource_info_map[resource_ref]['num_gpu'] = self._settings['num_gpu']
                        #resource_info_map['num_gpu'] = self._settings['num_gpu']
                        #print("resource_info: " + json.dumps(resource_info))

        elif "States" in workflow_description:
            states = workflow_description["States"]
            for sname in states:
                state = states[sname]
                if "Resource" in state:
                    resource_name = state["Resource"]

                    if resource_name not in resource_info_map.keys():
                        resource_info = self._get_resource_info(resource_name)
                        resource_info["resource_req_filename"] = "requirements/" + resource_name + "_requirements.txt"
                        resource_info["resource_env_filename"] = "environment_variables/" + resource_name + "_environment_variables.txt"
                        resource_info_map[resource_name] = resource_info
                        #resource_info_map[resource_name]['num_gpu'] = self._settings['num_gpu']
                        #resource_info_map['num_gpu'] = self._settings['num_gpu']
                        #print("resource_info: " + json.dumps(resource_info))

                if "Type" in state and state["Type"] == "Parallel":
                    branches = state['Branches']
                    for branch in branches:
                        resource_info_map = self._get_resource_info_map(branch, resource_info_map)

                if "Type" in state and state["Type"] == "Map":
                    branch = state['Iterator']
                    resource_info_map = self._get_resource_info_map(branch, resource_info_map)

        else:
            print("ERROR: invalid workflow description.")
            assert False
        #print("RESOURCE_INFO_MAP: " + json.dumps(resource_info_map))
        return resource_info_map

    def _delete_resource_if_existing(self, existing_resources, resource_name):
        for g in existing_resources:
            if g.name == resource_name:
                self._client.delete_function(g)
                break
        print("deleted resource: " + resource_name)

    def _create_and_upload_resource(self, resource_name, resource_info):
        print("Deploying resource: " + resource_name)

        resource_filename = resource_info["resource_filename"]
        is_zip = resource_info["is_zip"]
        is_jar = resource_info["is_jar"]
        resource_req_filename = resource_info["resource_req_filename"]
        resource_env_filename = resource_info["resource_env_filename"]
        resource_runtime = resource_info["resource_runtime"]

        self._workflow_resources.append(resource_name)

        try:
            # add the resource
            g = self._client.add_function(resource_name, runtime=resource_runtime)

            # upload the resource source
            print('Uploading file: ' + resource_filename)
            if is_zip or is_jar:
                g.upload(resource_filename)
            else:
                source_text = ''
                with open(resource_filename, 'r') as f:
                    source_text = f.read()
                g.source = {"code": source_text}

            # upload the resource requirements
            if os.path.isfile(resource_req_filename):
                with open(resource_req_filename, "r") as f:
                    reqs = f.read().strip()
                    g.requirements = reqs
                    #print("set requirements for function: " + resource_name + " " + reqs)

            # resource environment variables
            # upload the resource environment variables
            if os.path.isfile(resource_env_filename):
                with open(resource_env_filename, "r") as f:
                    env_vars = f.read().strip()
                    g.environment_variables = env_vars
                    #print("set environment variables for function: " + resource_name + " " + env_vars)

        except Exception as e:
            print("ERROR: Could not create resource.")
            print(str(e))
            assert False

    def upload_workflow(self):
        self.undeploy_workflow()

        resource_info_map = self._get_resource_info_map()

        existing_resources = self._client.functions

        for resource_name in resource_info_map.keys():
          #if not resource_name == 'num_gpu':
            self._delete_resource_if_existing(existing_resources, resource_name)

            resource_info = resource_info_map[resource_name]

            self._create_and_upload_resource(resource_name, resource_info)

    def get_deployment_error(self):
        return self._deployment_error

    def deploy_workflow(self):
        try:
            gpu_usage=self._settings["gpu_usage"]
            gpu_mem_usage=self._settings["gpu_mem_usage"]
            wf = self._client.add_workflow(self._workflow_name, None, gpu_usage, gpu_mem_usage)
            wf.json = json.dumps(self._workflow_description)
            wf.deploy(self._settings["timeout"]) 
            self._workflow = wf
            if self._workflow.status != "failed":
                print("MFN workflow " + self._workflow_name + " deployed; workflow id: " + self._workflow.id)
            else:
                print("MFN workflow " + self._workflow_name + " could not be deployed.")
                self._deployment_error = self._workflow.get_deployment_error()
        except Exception as e:
            print("ERROR: Could not deploy workflow.")
            raise e
            assert False

    def undeploy_workflow(self):
        existing_workflows = self._client.workflows
        for wf in existing_workflows:
            if wf.name == self._workflow_name:
                _status = wf.status
                if _status == "deployed" or _status == "deploying":
                    wf.undeploy(self._settings["timeout"])
                    print("Workflow undeployed.")
                time.sleep(2)
                self._client.delete_workflow(wf)
                break

        existing_resources = self._client.functions

        for resource_name in self._workflow_resources:
            self._delete_resource_if_existing(existing_resources, resource_name)

    def get_test_workflow_endpoints(self):
        if self._workflow.status == "deployed":
            return self._workflow.endpoints

    def execute(self, message, timeout=None, check_duration=False, async_=False):
        if timeout is None:
            timeout = self._settings["timeout"]
        if async_:
            return self._workflow.execute_async(message, timeout)
        else:
            return self._workflow.execute(message, timeout, check_duration)

    def get_workflow_logs(self, num_lines=500):
        data = self._workflow.logs(num_lines=num_lines)
        return data

    def clear_workflow_logs(self):
        self._workflow.clear_logs()

    def report(self, success, inp, expected, actual):
        if success:
            short_inp = self._get_printable(inp)
            print(self._test_name + " test " + mfntestpassed + " with input data:", short_inp)
        else:
            print(self._test_name + " test " + mfntestfailed + " with input data:", str(inp) + '(result: ' + json.dumps(actual) + ', expected: ' + json.dumps(expected) + ')')

    def exec_only(self, inp):
        any_failed_tests = False
        try:
            rn = self.execute(json.loads(inp))
            return rn
        except Exception as e:
            any_failed_tests = True
            self.undeploy_workflow()
            self.cleanup()
            print(str(e))
            raise e
        finally:
            time.sleep(2)
            if any_failed_tests:
                self._print_logs(self._workflow.logs())

    def exec_tests(self, testtuplelist, check_just_keys=False, check_duration=False, should_undeploy=True, async_=False, print_report=True):
        any_failed_tests = False
        durations = []

        try:
            i = 0
            num_total = len(testtuplelist)
            for tup in testtuplelist:
                i += 1
                print("Test " + str(i) + "/" + str(num_total), end="\r")
                current_test_passed = False
                inp, res = tup
                if check_duration:
                    rn, t_total = self.execute(json.loads(inp), check_duration=check_duration)
                else:
                    rn = self.execute(json.loads(inp), async_=async_)

                if check_duration:
                    durations.append(t_total)
                    #print("Total time to execute: " + str(t_total) + " (ms)")

                if isinstance(res, str):
                    res = json.loads(res)

                res_to_check = []

                # hold on to the Execution object, so that we can retrieve more results if needed
                if async_:
                    rn_async = rn

                    if not isinstance(res, list):
                        res_to_check.append(res)
                    else:
                        res_to_check = res
                else:
                    # some expected results can be lists
                    res_to_check.append(res)

                for cur_res in res_to_check:
                    # before we can compare results, we need to ensure that we get the actual result
                    # if we executed asynchronously, we'll have to wait until we get the result
                    if async_:
                        rn = rn_async.get()

                    if check_just_keys:
                        if set(rn.keys()) == set(cur_res.keys()):
                             current_test_passed = True
                        else:
                            raise Exception("Error: mismatch in result keys: " + str(rn) + " and " + str(cur_res))

                    else:
                        if rn == cur_res:
                            current_test_passed = True

                    if print_report:
                        self.report(current_test_passed, inp, cur_res, rn)
                    any_failed_tests = any_failed_tests or (not current_test_passed)

                    time.sleep(1)
        except Exception as e:
            print(str(e))
            raise e
        finally:
            print()
            time.sleep(2)
            if check_duration:
                print("------")
                print("Request/response latency statistics:")
                print("Number of executions: " + str(len(durations)))
                print("Average (ms): " + str(statistics.mean(durations)))
                print("Median (ms): " + str(statistics.median(durations)))
                print("Minimum (ms): " + str(min(durations)))
                print("Maximum (ms): " + str(max(durations)))
                print("Stdev (ms): " + str(statistics.stdev(durations)))
                print("PStdev (ms): " + str(statistics.pstdev(durations)))
                percentiles = [0.0, 50.0, 90.0, 95.0, 99.0, 99.9, 99.99, 100.0]
                self.print_percentiles(durations, percentiles)
                print("------")
            if any_failed_tests:
                self._print_logs(self._workflow.logs())
            if should_undeploy:
                self.undeploy_workflow()
                self.cleanup()

    def _print_logs(self, logs):
        print(logs)
        for t in logs:
            if t == "timestamp":
                continue
            cur_log = logs[t]
            lines = cur_log.split("\n")
            for line in lines:
                print(line)
            print("------")

    def print_percentiles(self, data, percentiles):
        data.sort()
        for perc in percentiles:
            print(str(perc) + "th percentile (ms): " + str(self.percentile(data, perc/100.0)))

    def percentile(self, data, percent):
        k = (len(data)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        d0 = data[int(f)] * (c-k)
        d1 = data[int(c)] * (k-f)
        return d0 + d1

    def _get_printable(self, text, max_len=50):
        if len(text) > max_len:
            return text[:max_len] + " ... (showing " + str(max_len) + "/" + str(len(text)) + " characters.)"
        return text

    def plot_latency_breakdown(self, num_last_executions=15):
        eidlist = self.extract_execution_ids(num_last_executions)
        eid_filename = "eidlist_" + self._test_name + ".txt"
        timestamps_filename = "timestamps_" + self._test_name + ".txt"
        eidlist = eidlist[len(eidlist) - num_last_executions:]
        with open(eid_filename, "w") as f:
            for eid in eidlist:
                f.write(eid + "\n")

        self.parse_metrics(eid_filename, timestamps_filename)

        cmd = "python3 ../plotmfnmetrics.py " + timestamps_filename
        output, error = run_command_return_output(cmd)

        # cleanup
        cmd = "rm esresult.json " + eid_filename + " " + timestamps_filename
        _, _ = run_command_return_output(cmd)

    def parse_metrics(self, eid_filename, timestamps_filename):
        cmd = "python3 ../mfnmetrics.py -eidfile " + eid_filename + " -wid " + self._workflow.id
        output, error = run_command_return_output(cmd)
        log_lines = combine_output(output, error)
        with open(timestamps_filename, "w") as f:
            for line in log_lines:
                f.write(line + "\n")

    def extract_execution_ids(self, num_last_executions, num_log_lines=2000):
        cmd = "python3 ../wftail.py -n " + str(num_log_lines) + " -wid " + self._workflow.id
        output, error = run_command_return_output(cmd)
        log_lines = combine_output(output, error)
        eidlist = []
        for line in log_lines:
            line = line.strip()
            if line == "":
                continue
            tokens = line.split(" ")
            eid = tokens[7]
            if eid != "[0l]":
                eid = eid[1:-1]
                eidlist.append(eid)
                #print(eid)

        return eidlist

    def exec_keys_check(self, testtuplelist):
        self.exec_tests(testtuplelist, check_just_keys=True)

    # compatibility with older tests
    def cleanup(self, delete_user=False):
        if delete_user:
            self._client.delete_user()
        self._client.disconnect()

def combine_output(output, error):
    output = output.split("\n")
    error = error.split("\n")
    return output + error

def run_command_return_output(cmd):
    cmd = shlex.split(cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    child_stdout_bytes, child_stderr_bytes = p.communicate()
    output = child_stdout_bytes.decode().strip()
    error = ""
    if p.returncode != 0:
        error = child_stderr_bytes.decode().strip()

    return output, error

