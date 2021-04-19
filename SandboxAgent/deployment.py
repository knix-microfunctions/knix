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

import base64
import json
import os
import sys
import time
import threading

import process_utils
import state_utils
from workflow import Workflow

sys.path.insert(1, os.path.join(sys.path[0], '../FunctionWorker/python'))

from DataLayerClient import DataLayerClient
from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage

SINGLE_JVM_FOR_FUNCTIONS = True

class Deployment:

    def __init__(self, deployment_info, hostname, userid, sandboxid, workflowid, workflowname, queue, datalayer, logger, external_endpoint, internal_endpoint, management_endpoints):
        self._logger = logger
        self._deployment_info = deployment_info
        self._hostname = hostname
        self._userid = userid
        self._sandboxid = sandboxid
        self._workflowid = workflowid
        self._workflowname = workflowname
        self._queue = queue
        self._datalayer = datalayer
        self._external_endpoint = external_endpoint
        self._internal_endpoint = internal_endpoint
        self._management_endpoints = management_endpoints

        self._python_version = sys.version_info

        self._storage_userid = self._userid.replace("@", "AT")
        self._storage_userid = self._storage_userid.replace("-", "_").replace(".", "_")

        self._process_id = os.getpid()

        self._functionworker_process_map = {}
        self._javarequesthandler_process_list = []
        self._queue_service_process = None
        self._frontend_process = None
        self._fluentbit_process = None
        # it will be probably updated to be something else
        self._fluentbit_actual_pid = -1

        self._child_process_command_args_map = {}

        # to be declared later when parsing the deployment info
        self._workflow = None

        self._global_data_layer_client = DataLayerClient(locality=1, suid=self._storage_userid, connect=self._datalayer)

        self._local_queue_client = None

    def get_workflow(self):
        return self._workflow

    def set_child_process(self, which, process, command_args_map):
        pid = process.pid
        if which == "qs":
            self._queue_service_process = process
        elif which == "fe":
            self._frontend_process = process
        elif which == "fb":
            self._fluentbit_process = process
            output, error = process_utils.run_command_return_output('ps --no-headers -o pid -C fluent-bit', self._logger)
            fbpid = int(output.strip())
            self._fluentbit_actual_pid = fbpid
            pid = fbpid

        # store command and args
        self._child_process_command_args_map[pid] = command_args_map

    def get_all_children_pids(self):
        children_pids = []
        for state in self._functionworker_process_map:
            p = self._functionworker_process_map[state]
            children_pids.append(p.pid)

        for jrhp in self._javarequesthandler_process_list:
            children_pids.append(jrhp.pid)

        children_pids.append(self._queue_service_process.pid)
        children_pids.append(self._frontend_process.pid)

        # looks like this pid does not match the actual process; perhaps because it also spawns another process?
        #children_pids.append(self._fluentbit_process.pid)
        ## find actual fluentbit pid
        output, error = process_utils.run_command_return_output('ps --no-headers -o pid -C fluent-bit', self._logger)
        fbpid = int(output.strip())
        self._fluentbit_actual_pid = fbpid
        children_pids.append(fbpid)

        return children_pids

    def check_child_process(self):
        pid, status = os.waitpid(-1, os.WNOHANG|os.WUNTRACED|os.WCONTINUED)
        failed_process_name = ""
        if os.WIFCONTINUED(status) or os.WIFSTOPPED(status):
            return False, _
        if os.WIFSIGNALED(status) or os.WIFEXITED(status):
            self._logger.error("Process with pid: " + str(pid) + " stopped.")
            if pid == self._fluentbit_actual_pid:
                failed_process_name = "Fluent-bit"
                log_filepath = "/opt/mfn/LoggingService/fluent-bit/fluent-bit.log"
            elif pid == self._queue_service_process.pid:
                failed_process_name = "Queue service"
                log_filepath = "/opt/mfn/logs/queueservice.log"
            elif pid == self._frontend_process.pid:
                failed_process_name = "Frontend"
                log_filepath = "/opt/mfn/logs/frontend.log"
            else:
                for jrhp in self._javarequesthandler_process_list:
                    if pid == jrhp.pid:
                        failed_process_name = "Java request handler"
                        log_filepath = "/opt/mfn/logs/javaworker.log"
                        break
                for state_name in self._functionworker_process_map:
                    process = self._functionworker_process_map[state_name]
                    if pid == process.pid:
                        failed_process_name = "Function worker (" + state_name + ")"
                        log_filepath = "/opt/mfn/logs/function_" + state_name + ".log"
                        del self._functionworker_process_map[state_name]
                        break

            self._logger.error("Failed process name: " + failed_process_name)

        if os.path.exists('/var/run/secrets/kubernetes.io'):
            return True, pid, failed_process_name, log_filepath
        else:
            # TODO: try to relaunch some of the processes (FWs, fluentbit, frontend)
            self._logger.info(self._child_process_command_args_map[pid])
            return True, pid, failed_process_name, log_filepath

    def shutdown(self):
        shutdown_message = {}
        shutdown_message["action"] = "stop"

        lqcm_shutdown = LocalQueueClientMessage(key="0l", value=json.dumps(shutdown_message))

        workflow_nodes = self._workflow.getWorkflowNodeMap()
        for function_topic in workflow_nodes:
            ack = self._local_queue_client.addMessage(function_topic, lqcm_shutdown, True)
            while not ack:
                ack = self._local_queue_client.addMessage(function_topic, lqcm_shutdown, True)

        self._logger.info("Waiting for function workers to shutdown")
        self._wait_for_child_processes()

        for jrh_process in self._javarequesthandler_process_list:
            process_utils.terminate_and_wait_child(jrh_process, "JavaRequestHandler", 5, self._logger)

        self._local_queue_client.shutdown()

    def force_shutdown(self):
        # called when the queue service has crashed and we need to shut down the function workers
        for state in self._functionworker_process_map:
            p = self._functionworker_process_map[state]
            process_utils.terminate_and_wait_child(p, "FunctionWorker", 5, self._logger)

        for jrh_process in self._javarequesthandler_process_list:
            process_utils.terminate_and_wait_child(jrh_process, "JavaRequestHandler", 5, self._logger)

        self._local_queue_client.shutdown()

    def _wait_for_child_processes(self):
        output, error = process_utils.run_command_return_output('pgrep -P ' + str(self._process_id), self._logger)
        if error is not None:
            self._logger.error("[SandboxAgent] wait_for_child_processes: Failed to get children process ids: %s", str(error))
            return

        children_pids = set(output.split())
        self._logger.info("[SandboxAgent] wait_for_child_processes: Parent pid: %s, Children pids: %s", str(self._process_id), str(children_pids))

        for jrh_process in self._javarequesthandler_process_list:
            if str(jrh_process.pid) in children_pids:
                children_pids.remove(str(jrh_process.pid))
                self._logger.info("[SandboxAgent] wait_for_child_processes: Not waiting on JavaRequestHandler pid: %s", str(jrh_process.pid))

        ## find fluentbit PID
        output, error = process_utils.run_command_return_output('ps --no-headers -o pid -C fluent-bit', self._logger)
        fbpid = output.strip()
        if fbpid in children_pids:
            children_pids.remove(fbpid)
            self._logger.info("[SandboxAgent] wait_for_child_processes: Not waiting on fluent-bit pid: %s", fbpid)

        if self._queue_service_process is not None:
            if str(self._queue_service_process.pid) in children_pids:
                children_pids.remove(str(self._queue_service_process.pid))
                self._logger.info("[SandboxAgent] wait_for_child_processes: Not waiting on queue service pid: %s", str(self._queue_service_process.pid))

        if self._frontend_process is not None:
            if str(self._frontend_process.pid) in children_pids:
                children_pids.remove(str(self._frontend_process.pid))
                self._logger.info("[SandboxAgent] wait_for_child_processes: Not waiting on frontend pid: %s", str(self._frontend_process.pid))

        if not children_pids:
            self._logger.info("[SandboxAgent] wait_for_child_processes: No remaining pids to wait for")
            return

        while True:
            try:
                cpid, status = os.waitpid(-1, 0)
                self._logger.info("[SandboxAgent] wait_for_child_processes: Status changed for pid: %s, Status: %s", str(cpid), str(status))
                if str(cpid) not in children_pids:
                    #print('wait_for_child_processes: ' + str(cpid) + "Not found in children_pids")
                    continue
                children_pids.remove(str(cpid))
                if not children_pids:
                    self._logger.info("[SandboxAgent] wait_for_child_processes: No remaining pids to wait for")
                    break
            except Exception as exc:
                self._logger.error('[SandboxAgent] wait_for_child_processes: %s', str(exc))

    def _start_python_function_worker(self, worker_params, env_var_list):
        error = None
        function_name = worker_params["function_name"]
        state_name = worker_params["function_state_name"]
        custom_env = os.environ.copy()
        old_ld_library_path = ""
        if "LD_LIBRARY_PATH" in custom_env:
            old_ld_library_path = custom_env["LD_LIBRARY_PATH"]
        custom_env["LD_LIBRARY_PATH"] = "/opt/mfn/workflow/states/" + state_name + "/" + function_name + ":/opt/mfn/workflow/states/" + state_name + "/" + function_name + "/lib"

        if old_ld_library_path != "":
            custom_env["LD_LIBRARY_PATH"] = custom_env["LD_LIBRARY_PATH"] + ":" + old_ld_library_path

        #custom_env["PYTHONPATH"] = "/opt/mfn/workflow/states/" + state_name + "/" + function_name

        for env_var in env_var_list:
            idx = env_var.find("=")
            if idx == -1:
                continue
            env_var_key = env_var[0:idx]
            env_var_value = env_var[idx+1:]
            custom_env[env_var_key] = env_var_value

        #self._logger.info("environment variables (after user env vars): %s", str(custom_env))

        if self._python_version >= (3, ):
            cmd = "python3 "
        else:
            cmd = "python "
        cmd = cmd + "/opt/mfn/FunctionWorker/python/FunctionWorker.py"
        cmd = cmd + " " + '\"/opt/mfn/workflow/states/%s/worker_params.json\"' % state_name # state_name can contain whitespace

        filename = '/opt/mfn/logs/function_' + state_name + '.log'
        log_handle = open(filename, 'a')

        # store command arguments for when/if we need to restart the process if it fails
        command_args_map = {}
        command_args_map["command"] = cmd
        command_args_map["custom_env"] = custom_env
        command_args_map["log_filename"] = filename

        #self._logger.info("Starting function worker: " + state_name + "  with stdout/stderr redirected to: " + filename)
        error, process = process_utils.run_command(cmd, self._logger, custom_env=custom_env, process_log_handle=log_handle)
        if error is None:
            self._functionworker_process_map[state_name] = process
            self._child_process_command_args_map[process.pid] = command_args_map
            self._logger.info("Started function worker: %s, pid: %s, with stdout/stderr redirected to: %s", state_name, str(process.pid), filename)
        return error

    def _start_function_worker(self, worker_params, runtime, env_var_list):
        error = None

        if runtime.find("python") != -1:
            error = self._start_python_function_worker(worker_params, env_var_list)
        elif runtime.find("java") != -1:
            # TODO: environment/JVM variables need to be utilized by the java request handler, not by the function worker

            if SINGLE_JVM_FOR_FUNCTIONS:
                # _XXX_: we'll launch the single JVM handling all java functions later
                error = self._start_python_function_worker(worker_params, env_var_list)
            else:
                # if jar, the contents have already been extracted as if it was a zip archive
                # start the java request handler if self._function_runtime == "java"
                # we wrote the parameters to json file at the state directory
                self._logger.info("Launching JavaRequestHandler for state: %s", worker_params["function_state_name"])
                cmdjavahandler = "java -jar /opt/mfn/JavaRequestHandler/target/javaworker.jar "
                cmdjavahandler += "/opt/mfn/workflow/states/" + worker_params["function_state_name"] + "/java_worker_params.json"

                error, process = process_utils.run_command(cmdjavahandler, self._logger, wait_until="Waiting for requests on:")
                if error is not None:
                    error = "Could not launch JavaRequestHandler: " + worker_params["function_name"] + " " + error
                    self._logger.error(error)
                else:
                    self._javarequesthandler_process_list.append(process)
                    error = self._start_python_function_worker(worker_params, env_var_list)
        else:
            error = "Unsupported function runtime: " + runtime

        return error

    def _prepare_update_for_locally_running(self, local_functions):
        update = {}
        update["action"] = "update-local-functions"
        update["localFunctions"] = local_functions
        update = json.dumps(update)

        lqcm_update = LocalQueueClientMessage(key="0l", value=update)

        return lqcm_update

    def _update_function_worker(self, topic, lqcm_update):
        ack = self._local_queue_client.addMessage(topic, lqcm_update, True)
        while not ack:
            ack = self._local_queue_client.addMessage(topic, lqcm_update, True)

    def _update_remaining_function_workers(self, excluded_function_topic, lqcm_update=None):
        local_functions = self._workflow.getWorkflowLocalFunctions()
        if lqcm_update is None:
            lqcm_update = self._prepare_update_for_locally_running(local_functions)

        for locally_running_ft in local_functions:
            if locally_running_ft == excluded_function_topic:
                continue
            self._update_function_worker(locally_running_ft, lqcm_update)

    def stop_function_worker(self, function_topic):
        # remove from locally running functions
        self._workflow.removeLocalFunction(function_topic)

        # first, update locally running functions with remaining functions
        self._update_remaining_function_workers(function_topic)

        # send stop message to function worker's queue
        stop = {}
        stop["action"] = "stop"
        stop = json.dumps(stop)
        lqcm_update = LocalQueueClientMessage(key="0l", value=stop)
        self._update_function_worker(function_topic, lqcm_update)

    def _install_sandbox_requirements(self, parameters):
        error = None
        installer = parameters["installer"]
        requirements = parameters["requirements"]
        additional_installer_options = {}
        if "additional_installer_options" in parameters:
            additional_installer_options = parameters["additional_installer_options"]

        if requirements:
            # TODO: other installers (e.g., apt-get)?
            if installer == "pip":
                # launch 'pip install' with any parameters related to proxy etc.
                # store requirements into /opt/mfn/requirements.txt
                reqfname = "/opt/mfn/requirements.txt"
                with open(reqfname, "w+") as reqf:
                    for req in requirements:
                        reqf.write(req + "\n")

                # modify command to add additional installer options
                if self._python_version >= (3, ):
                    cmd = "python3 "
                else:
                    cmd = "python "
                cmd = cmd + "-m pip install --user"
                cmd += " --no-compile --no-clean --no-cache-dir"
                for opt in additional_installer_options:
                    cmd = cmd + " " + opt + " " + additional_installer_options[opt]

                cmd = cmd + " -r " + reqfname

                # launch 'pip install [additional_options] -r /opt/mfn/requirements.txt
                error, _ = process_utils.run_command(cmd, self._logger, wait_output=True)

            else:
                error = "Unsupported installer: " + installer

        return error

    def _retrieve_and_store_function_code(self, resource_name, resource_info):
        error = None

        rpath = "/opt/mfn/code/resources/" + resource_name + "/"
        fpath = rpath + resource_name

        if resource_info["runtime"].find("python") != -1:
            fpath = fpath + ".py"
        elif resource_info["runtime"].find("java") != -1:
            fpath = fpath + ".java"
        else:
            error = "Unsupported runtime: " + resource_info["runtime"]
            return (error, None)

        if not os.path.exists(os.path.dirname(fpath)):
            try:
                os.makedirs(os.path.dirname(fpath))
            except OSError as err:
                if err.errno != os.errno.EEXIST:
                    error = err
                    return (error, None)

        resource_code = self._global_data_layer_client.get(resource_info["ref"])

        if resource_code is None:
            error = "Empty function code."
            return (error, None)

        try:
            resource_code = base64.b64decode(resource_code).decode()
        except Exception as exc:
            error = "Invalid value for code: " + str(exc)
            self._logger.error(error)
            return (error, None)

        with open(fpath, "w") as funcf:
            funcf.write(resource_code)

        return (error, rpath)

    def _retrieve_and_store_function_zip(self, resource_name, resource_info):
        error = None

        zipref = resource_info["ref"]
        num_chunks_str = self._global_data_layer_client.get(zipref)

        try:
            num_chunks = int(num_chunks_str)
        except Exception as exc:
            error = "Invalid value for key " + zipref + "; expected number of chunks: " + str(exc)
            self._logger.error(error)
            return (error, None)

        zip_content = ""
        ind = zipref.find("num_chunks_")
        gid = zipref[ind+11:]
        pref = zipref[0:ind] + gid + "_chunk_"
        for i in range(num_chunks):
            chunkref = pref + str(i)
            chunk = self._global_data_layer_client.get(chunkref)
            if chunk is None:
                error = "Empty zip chunk."
                return (error, None)

            zip_content = zip_content + chunk

        old_len = len(zip_content)
        rem = old_len % 4
        if rem > 0:
            num_pad = 4 - rem
            for i in range(num_pad):
                zip_content = zip_content + "="

        try:
            decodedzip = base64.b64decode(zip_content)
        except Exception as exc:
            error = "Invalid value for assembled chunks; couldn't decode base64: " + str(exc)
            self._logger.error(error)
            return (error, None)

        runtime = resource_info["runtime"]

        # 1. store zip file
        zipfname = "/opt/mfn/code/zips/" + resource_name + ".zip"
        if not os.path.exists(os.path.dirname(zipfname)):
            try:
                os.makedirs(os.path.dirname(zipfname))
            except OSError as err:
                if err.errno != os.errno.EEXIST:
                    error = err
                    return (error, None)

        with open(zipfname, "wb") as zipfile:
            zipfile.write(decodedzip)

        gextractedpath = "/opt/mfn/code/resources/" + resource_name + "/"
        # 2. extract zip file
        if not os.path.exists(os.path.dirname(gextractedpath)):
            try:
                os.makedirs(os.path.dirname(gextractedpath))
            except OSError as err:
                if err.errno != os.errno.EEXIST:
                    error = err
                    return (error, None)

        cmdunzip = "unzip " + zipfname + " -d " + gextractedpath
        error, _ = process_utils.run_command(cmdunzip, self._logger, wait_output=True)

        if error is not None:
            error = "Could not extract zip file: " + resource_name + " " + error
            self._logger.error(error)
            return (error, None)

        # 3. need to set executable permissions for the extracted libs
        cmdperm = "sh -c \"find " + gextractedpath + "| xargs -I {} file {}"
        cmdperm = cmdperm + "| grep ELF" + "| grep -v grep"
        cmdperm = cmdperm + "| awk -F ':' '{print $1}'"
        cmdperm = cmdperm + "| xargs -I {} chmod +x {}\""

        error, _ = process_utils.run_command(cmdperm, self._logger, wait_output=True)

        if error is not None:
            error = "Could not set lib permissions: " + resource_name + " " + error
            self._logger.error(error)
            return (error, None)

        if runtime.find("python") != -1:
            fpath = gextractedpath + resource_name
            fpath = fpath + ".py"

            resource_code = self._global_data_layer_client.get("grain_source_" + resource_info["id"])
            if resource_code is not None or resource_code != "":
                try:
                    resource_code = base64.b64decode(resource_code).decode()
                except Exception as exc:
                    error = "Invalid value for function code: " + str(exc)
                    self._logger.error(error)
                    return (error, None)

                self._logger.info("Overwriting zip resource file with the updated resource code...")
                with open(fpath, "w") as funcf:
                    funcf.write(resource_code)

        elif runtime.find("java") != -1:
            # TODO: try to retrieve the updated resource?
            # To do that, we'd need to know the actual state name (i.e., in the workflow description),
            # which (for now) has to be the same as the Java class.
            # This class name can differ from the resource name
            # (e.g., one jar containing multiple classes with handle functions, such that each function is used as a separate state)
            # that means, we'd need to do the code update just at the beginning of when we create the state and also the compilation,
            # but before copying the resource to each state's separate location
            # TODO: double check whether this is also the case for python
            pass

        else:
            error = "Unsupported runtime: " + resource_info["runtime"]
            return (error, None)

        return (error, gextractedpath)

    def _init_storage_dlc(self, locality, for_mfn, is_wf_private):
        t_start_thread = time.time()
        self._logger.info("Starting thread for storage init: %s, %s, %s", str(locality), str(for_mfn), str(is_wf_private))
        if for_mfn:
            dlc = DataLayerClient(locality=locality, for_mfn=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
        elif is_wf_private:
            dlc = DataLayerClient(locality=locality, is_wf_private=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
        else:
            dlc = DataLayerClient(locality=locality, suid=self._storage_userid, connect=self._datalayer, init_tables=True)

        dlc.shutdown()
        t_total = (time.time() - t_start_thread) * 1000.0
        self._logger.info("Thread to init storage finished: %s (ms), %s, %s, %s", str(t_total), str(locality), str(for_mfn), str(is_wf_private))

    def _initialize_data_layer_storage(self):
        # each data layer client will automatically create the local keyspace and tables
        # upon instantiation

        threads = []

        # mfn internal tables
        #local_dlc = DataLayerClient(locality=0, for_mfn=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
        #local_dlc.shutdown()
        t_local_mfn = threading.Thread(target=self._init_storage_dlc, args=(0, True, False, ))
        t_local_mfn.start()
        threads.append(t_local_mfn)

        # user storage tables
        #local_dlc = DataLayerClient(locality=0, suid=self._storage_userid, connect=self._datalayer, init_tables=True)
        #local_dlc.shutdown()
        t_local_user = threading.Thread(target=self._init_storage_dlc, args=(0, False, False, ))
        t_local_user.start()
        threads.append(t_local_user)

        # workflow private tables
        #local_dlc = DataLayerClient(locality=0, is_wf_private=True, sid=self._sandboxid, wid=self._workflowid, connect=self._datalayer, init_tables=True)
        #local_dlc.shutdown()
        t_local_private = threading.Thread(target=self._init_storage_dlc, args=(0, False, True, ))
        t_local_private.start()
        threads.append(t_local_private)

        # for global access:
        # user storage is created by management service at login
        # mfn internal storage and workflow-private storage is created by management service at workflow addition

        return threads

    def _populate_worker_params(self, function_topic, wf_node, state):
        worker_params = {}
        worker_params["userid"] = self._userid
        worker_params["storage_userid"] = self._storage_userid
        worker_params["sandboxid"] = self._sandboxid
        worker_params["workflowid"] = self._workflowid
        worker_params["workflowname"] = self._workflowname

        worker_params["function_topic"] = function_topic
        worker_params["function_path"] = state["resource_filepath"]
        worker_params["function_name"] = state["resource_filename"]
        worker_params["function_folder"] = state["resource_dirpath"]
        worker_params["function_runtime"] = state["resource_runtime"]

        worker_params["function_state_type"] = wf_node.getGWFType()
        worker_params["function_state_name"] = wf_node.getGWFStateName()
        worker_params["function_state_info"] = wf_node.getGWFStateInfo()

        worker_params["hostname"] = self._hostname
        worker_params["queue"] = self._queue
        worker_params["datalayer"] = self._datalayer
        worker_params["external_endpoint"] = self._external_endpoint
        worker_params["internal_endpoint"] = self._internal_endpoint
        worker_params["management_endpoints"] = self._management_endpoints

        worker_params["wf_next"] = wf_node.getNextMap()
        worker_params["wf_pot_next"] = wf_node.getPotentialNextMap()
        worker_params["wf_function_list"] = self._workflow.getWorkflowFunctionMap()
        worker_params["wf_exit"] = self._workflow.getWorkflowExitPoint()
        worker_params["wf_entry"] = self._workflow.getWorkflowEntryTopic()

        worker_params["is_session_workflow"] = self._workflow.is_session_workflow()
        worker_params["is_session_function"] = wf_node.is_session_function()
        worker_params["session_function_parameters"] = wf_node.get_session_function_parameters()

        worker_params["should_checkpoint"] = self._workflow.are_checkpoints_enabled()

        return worker_params

    def _compile_java_resources_if_necessary(self, resource, mvndeps):
        error = None

        cmdmkdir = "mkdir -p " + resource["dirpath"] + "target/classes"

        self._logger.info("Preparing for compilation of Java function resources: %s", resource["name"])
        error, _ = process_utils.run_command(cmdmkdir, self._logger, wait_output=True)
        if error is not None:
            error = "Could not create target directory for resource: " + resource["name"] + " " + error
            self._logger.error(error)
            return error

        #cmdjavac = "javac -classpath /opt/mfn/JavaRequestHandler/mfnapi.jar -d " + resource["dirpath"] + "target/classes "
        #cmdjavac += resource["dirpath"] + resource["name"] + ".java"

        cmdfind = "find " + resource["dirpath"] + " -name *.java"
        output, error = process_utils.run_command_return_output(cmdfind, self._logger)
        if error is not None:
            self._logger.error("[SandboxAgent] could not search for any Java sources: %s", str(error))
            error = "Could not search for any Java sources: " + resource["name"] + " " + str(error)
            return error
        source_files = set(output.split("\n"))
        source_files = ' '.join(source_files).strip()
        should_compile = False
        if source_files != "":
            should_compile = True
            self._logger.info("Found following Java sources: %s", str(source_files))
        else:
            self._logger.info("No java sources to compile.")

        # 2. check for pom.xml or the requirements; if it is there, then:
        if mvndeps is not None and not os.path.exists(resource["dirpath"] + "pom.xml"):
            # write the content of mvndeps into the pom.xml
            self._logger.info("Writing maven build file: %spom.xml", resource["dirpath"])
            with open(resource["dirpath"] + "pom.xml", "w") as fpom:
                fpom.write(mvndeps)

        # we either had a pom.xml file in the archive or non-empty mvndeps from uploaded requirements, which we wrote as the pom.xml file
        # regardless, if there is a pom file, then resolve and copy maven dependencies
        if os.path.exists(resource["dirpath"] + "pom.xml"):
            cmdmvn = "mvn -Duser.home=/tmp -DskipTests -gs /opt/mfn/JavaRequestHandler/maven/sandbox-mvn-settings.xml -f " + resource["dirpath"]
            cmdmvn += " dependency:copy-dependencies -DoutputDirectory=" + resource["dirpath"] + "target/classes"

            self._logger.info("Copying maven dependencies for Java function: %s", resource["name"])
            error, _ = process_utils.run_command(cmdmvn, self._logger, wait_output=True)
            if error is not None:
                error = "Could not copy maven dependencies: " + resource["name"] + " " + error
                self._logger.error(error)
                return error
            self._logger.info("Finished copying dependencies for Java function: %s", resource["name"])

        if should_compile:
            cmdjavac = "javac -classpath /opt/mfn/JavaRequestHandler/mfnapi.jar:"
            cmdjavac += resource["dirpath"] + "target/classes/* "
            cmdjavac += "-d " +  resource["dirpath"] + "target/classes " + source_files

            self._logger.info("Compiling Java function resources: %s", resource["name"])
            self._logger.info(cmdjavac)
            error, _ = process_utils.run_command(cmdjavac, self._logger, wait_output=True)
            if error is not None:
                error = "Could not compile resource: " + resource["name"] + " " + error
                self._logger.error(error)
                return error
            self._logger.info("Finished compiling Java function resources: %s", resource["name"])

        return error

    def process_deployment_info(self):
        has_error = False
        errmsg = ""

        t_start_storage = time.time()
        # initialize local data layer space for user and workflow
        # do so in separate threads
        # join these threads just before returning
        init_storage_threads = self._initialize_data_layer_storage()
        total_time_threads_storage = (time.time() - t_start_storage) * 1000.0
        self._logger.info("Storage thread initialization time: %s (ms)", str(total_time_threads_storage))

        if self._deployment_info is not None and self._deployment_info != "":
            try:
                self._deployment_info = json.loads(self._deployment_info)
                self._logger.debug("Deployment info: %s", json.dumps(self._deployment_info))
            except Exception as exc:
                errmsg = "Could not parse deployment info: " + str(exc)
                self._logger.error(errmsg)
                has_error = True
                return has_error, errmsg
        else:
            errmsg = "Empty deployment info."
            has_error = True
            return has_error, errmsg

        if "workflow" not in self._deployment_info or "resources" not in self._deployment_info:
            errmsg = "Incomplete deployment info: " + json.dumps(self._deployment_info)
            self._logger.error(errmsg)
            has_error = True
            return has_error, errmsg

        # get workflow info
        workflow_info = self._deployment_info["workflow"]
        sid = workflow_info["sandboxId"]
        if sid != self._sandboxid:
            warnmsg = "WARN: workflow info sandboxid doesn't match provided sandboxid ("+sid+" <-> "+workflow_info["sandboxId"]+")"
            self._logger.info(warnmsg)
        wid = workflow_info["workflowId"]
        if wid != self._workflowid:
            warnmsg = "WARN: workflow info workflowid doesn't match provided workflowid ("+wid+" <-> "+workflow_info["workflowId"]+")"
            print(warnmsg)
        wf_type = workflow_info["workflowType"]

        usertoken = ''
        if "usertoken" in workflow_info:
            usertoken = workflow_info["usertoken"]
        os.environ["USERTOKEN"] = usertoken

        os.environ["PYTHONWARNINGS"] = "ignore:Unverified HTTPS request"

        # get workflow json, parse workflow json and init params
        workflow_json = self._global_data_layer_client.get(workflow_info["json_ref"])
        if workflow_json is None or workflow_json == "":
            has_error = True
            errmsg = "Empty workflow description."
            return has_error, errmsg

        try:
            workflow_json = base64.b64decode(workflow_json).decode()
        except Exception as exc:
            has_error = True
            errmsg = "Invalid value for workflow json: " + str(exc)
            return has_error, errmsg

        self._workflow = Workflow(self._userid, sid, wid, wf_type, workflow_json, self._logger)

        has_error = self._workflow.has_error()
        if has_error:
            errmsg = "Problem in workflow description: " + str(workflow_json)
            self._logger.error(errmsg)
            return has_error, errmsg

        # get workflow nodes
        workflow_nodes = self._workflow.getWorkflowNodeMap()

        # get resources info and find functions
        resource_map = {}
        resource_info_map = self._deployment_info["resources"]

        if any(resource_info_map[res_name]["runtime"] == "Java" for res_name in resource_info_map):
            # run setup_maven.sh to update the proxy settings at runtime
            # (i.e., the sandbox image may have been built on a machine with a proxy, or vice versa)
            cmd_maven_proxy_initer = "/opt/mfn/JavaRequestHandler/./setup_maven.sh"
            self._logger.info("Updating maven proxy settings...")
            error, _ = process_utils.run_command(cmd_maven_proxy_initer, self._logger, wait_output=True)
            if error is not None:
                has_error = True
                errmsg = "Could not reinitialize maven proxy settings: " + error
                return has_error, errmsg
            self._logger.info("Finished updating maven proxy settings.")

        # for pip installable dependencies for python functions
        req_map = {}
        t_start_download = time.time()
        # store functions in local filesystem
        for resource_name in resource_info_map:
            resource_info = resource_info_map[resource_name]
            resource_info["runtime"] = resource_info["runtime"].lower()

            if resource_info["type"] == "code":
                error, resource_dirpath = self._retrieve_and_store_function_code(resource_name, resource_info)
            else:
                error, resource_dirpath = self._retrieve_and_store_function_zip(resource_name, resource_info)

            if error is not None:
                errmsg = "Could not retrieve and store function: " + resource_name + " " + error
                self._logger.error(errmsg)
                has_error = True
                return has_error, errmsg

            # these requirements can now be also for java maven dependencies
            resource_id = resource_info["id"]
            greq = self._global_data_layer_client.get("grain_requirements_" + resource_id)
            mvndeps = None
            if greq is not None and greq != "":
                greq = base64.b64decode(greq).decode()
                if resource_info["runtime"].find("python") == 0:
                    # get function requirements and put it into a map
                    lines = greq.strip().split("\n")
                    for line in lines:
                        req_map[line] = True
                elif resource_info["runtime"].find("java") == 0:
                    mvndeps = greq

            # get function environment variables
            env_var_list = []
            genv = self._global_data_layer_client.get("grain_environment_variables_" + resource_id)
            if genv is not None and genv != "":
                genv = base64.b64decode(genv).decode()
                lines = genv.split("\n")
                env_var_list = lines

            resource = {}
            resource["name"] = resource_name
            resource["dirpath"] = resource_dirpath
            resource["runtime"] = resource_info["runtime"]
            resource["env_var_list"] = env_var_list
            resource_map[resource_name] = resource

            # compile the java sources
            if resource["runtime"].find("java") == 0:
                # even if it was just a single java file
                # or a jar file uploaded with source files
                # or a jar file with just class files,
                # the following function will
                # 1. download maven dependencies (if there is a pom.xml in the jar or was separately uploaded)
                # 2. compile the source files if any
                error = self._compile_java_resources_if_necessary(resource, mvndeps)

                if error is not None:
                    errmsg = "Could not compile Java function resources: " + resource_name + " " + error
                    self._logger.error(errmsg)
                    has_error = True
                    return has_error, errmsg

        total_time_download = (time.time() - t_start_download) * 1000.0
        self._logger.info("Download time for all function code: %s (ms)", str(total_time_download))

        t_start_requirements = time.time()
        # this list will only contain pip installable dependencies
        # java maven dependencies will be handled while compiling the java resources
        sbox_req_list = []
        for req_line in req_map:
            sbox_req_list.append(req_line)

        # install sandbox requirements
        req = workflow_info["sandbox_requirements"]
        req["requirements"] = sbox_req_list
        error = self._install_sandbox_requirements(req)
        if error is not None:
            errmsg = "Could not install sandbox requirements. " + str(error)
            self._logger.error(errmsg)
            has_error = True
            return has_error, errmsg

        total_time_requirements = (time.time() - t_start_requirements) * 1000.0
        self._logger.info("Requirements install time: %s (ms)", str(total_time_requirements))

        self._local_queue_client = LocalQueueClient(connect=self._queue)

        self._local_queue_client.addTopic(self._workflow.getWorkflowExitTopic())

        t_start_launch = time.time()
        # accummulate all java worker params into one
        # later, we'll launch a single JVM to handle all java functions
        if SINGLE_JVM_FOR_FUNCTIONS:
            single_jvm_worker_params = {}
            any_java_function = False

        total_time_state = 0.0
        for function_topic in workflow_nodes:
            wf_node = workflow_nodes[function_topic]
            resource_name = wf_node.get_resource_name()

            t_start_state = time.time()
            if resource_name == "":
                # this is an ASL state without a resource (i.e., function) attached to it
                error, resource = state_utils.create_dummy_resource_for_asl_state(wf_node)
                if error is not None:
                    errmsg = "Could not create non-resource state. " + str(error)
                    self._logger.error(errmsg)
                    has_error = True
                    return has_error, errmsg
            else:
                resource = resource_map[resource_name]

            error, state = state_utils.create_state(wf_node, resource, self._logger)
            if error is not None:
                errmsg = "Could not create state: " + str(error)
                self._logger.error(errmsg)
                has_error = True
                return has_error, errmsg

            total_time_state += (time.time() - t_start_state) * 1000.0

            self._local_queue_client.addTopic(function_topic)

            # compile worker parameters
            worker_params = self._populate_worker_params(function_topic, wf_node, state)
            # store worker parameters as a local file
            params_filename = state["dirpath"] + "worker_params.json"

            with open(params_filename, "w") as paramsf:
                json.dump(worker_params, paramsf, indent=4)

            if state["resource_runtime"].find("java") != -1:
                java_worker_params = {}
                java_worker_params["functionPath"] = worker_params["function_folder"]
                java_worker_params["functionName"] = worker_params["function_name"]
                java_worker_params["serverSocketFilename"] = "/tmp/java_handler_" + worker_params["function_state_name"] + ".uds"

                if SINGLE_JVM_FOR_FUNCTIONS:
                    any_java_function = True
                    single_jvm_worker_params[worker_params["function_state_name"]] = java_worker_params
                else:
                    java_params_filename = state["dirpath"] + "java_worker_params.json"
                    with open(java_params_filename, "w") as javaparamsf:
                        json.dump(java_worker_params, javaparamsf, indent=4)

            # launch function workers with the params parsed from workflow info
            error = self._start_function_worker(worker_params, state["resource_runtime"], state["resource_env_var_list"])

            if error is not None:
                errmsg = "Problem launching function worker for: " + worker_params["function_name"]
                self._logger.error(errmsg)
                has_error = True
                return has_error, errmsg

            # add the new function worker to the local list
            self._workflow.addLocalFunction(function_topic)

        # all function workers have been launched; update them with locally running functions
        # prepare update message to be used by all
        local_functions = self._workflow.getWorkflowLocalFunctions()
        lqcm_update = self._prepare_update_for_locally_running(local_functions)
        for function_topic in workflow_nodes:
            self._update_function_worker(function_topic, lqcm_update)

        if SINGLE_JVM_FOR_FUNCTIONS:
            if any_java_function:
                single_jvm_params_filename = "/opt/mfn/workflow/states/single_jvm_worker_params.json"
                with open(single_jvm_params_filename, "w") as jvmparamsf:
                    json.dump(single_jvm_worker_params, jvmparamsf, indent=4)

                self._logger.info("Launching a single JavaRequestHandler for all Java states...")
                cmdjavahandler = "java -jar /opt/mfn/JavaRequestHandler/target/javaworker.jar "
                cmdjavahandler += single_jvm_params_filename

                error, process = process_utils.run_command(cmdjavahandler, self._logger, wait_until="Waiting for requests on:")
                if error is not None:
                    errmsg = "Problem launching JavaRequestHandler for Java states: " + error
                    self._logger.error(errmsg)
                    has_error = True
                    return has_error, errmsg
                else:
                    self._javarequesthandler_process_list.append(process)

        self._logger.info("State creation for all function workers: %s (ms)", str(total_time_state))

        total_time_launch = (time.time() - t_start_launch) * 1000.0
        self._logger.info("Launch time for all function workers: %s (ms)", str(total_time_launch))

        if not has_error:
            # check whether all function workers have launched successfully
            # give some time for function workers to come up
            cmd = "pgrep -P " + str(self._process_id) + " -a"
            output, error = process_utils.run_command_return_output(cmd, self._logger)
            if error is not None:
                self._logger.error("[SandboxAgent] check health of function workers: failed to get FunctionWorker processes: %s", str(error))
                has_error = True
                errmsg = "Could not get FunctionWorker processes."

        if not has_error:
            fwlines = set(output.split("\n"))
            fwpids = []
            for line in fwlines:
                if "FunctionWorker.py" in line:
                    pid = line.split(" ")[0]
                    fwpids.append(pid)

            if str(self._fluentbit_process.pid) in fwpids:
                fwpids.remove(str(self._fluentbit_process.pid))

            self._logger.info(str(len(fwpids)) + " " + str(len(self._functionworker_process_map)))
            #self._logger.info(str(fwpids) + " " + str(self._functionworker_process_map))

            if len(fwpids) != len(self._functionworker_process_map):
                has_error = True
                errmsg = "One or more function workers could not be launched:\n"

                for state_name in self._functionworker_process_map:
                    fwp = self._functionworker_process_map[state_name]
                    if fwp.pid not in fwpids:
                        errmsg += state_name + "\n"

        self._global_data_layer_client.shutdown()

        for t in init_storage_threads:
            t.join()
        self._logger.info("Joined init storage threads.")

        return has_error, errmsg
