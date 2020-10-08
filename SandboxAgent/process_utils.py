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

import shlex
import subprocess

def run_command(command, logger, custom_env=None, wait_output=False, process_log_handle=None, wait_until=None):
    command = shlex.split(command)
    error = None
    stdout = process_log_handle
    stderr = process_log_handle
    if wait_output or wait_until:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    try:
        if custom_env is not None:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=custom_env, close_fds=True, bufsize=1)
        else:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, close_fds=True, bufsize=1)

        if wait_output:
            #out, err = process.communicate()
            while True:
                output = process.stdout.readline().decode()
                #error = process.stderr.readline().decode()
                if output == '' and process.poll() is not None:
                    break

                if output != "":
                    logger.info(output.rstrip())
                #logger.error(error.rstrip())
            if process.returncode != 0:
                error = process.communicate()[1]

        elif wait_until:
            while True:
                output = process.stdout.readline().decode()
                if output == '' and process.poll() is not None:
                    break

                if output != "":
                    logger.info(output.rstrip())
                    if output.find(wait_until) != -1:
                        break

        else:
            error = None
    except Exception as exc:
        logger.exception("[SandboxAgent] Could not execute command: %s", str(command))
        error = exc

    if error is not None and not isinstance(error, str):
        error = error.decode()

    return error, process

def run_command_return_output(cmd, logger):
    error = None
    output = None
    try:
        args = shlex.split(cmd)
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        child_stdout_bytes, child_stderr_bytes = child.communicate()
        output = child_stdout_bytes.decode().strip()
        if child.returncode != 0:
            error = child_stderr_bytes.decode().strip()
    except Exception as exc:
        logger.error('[SandboxAgent] Could not execute command and return output: %s', str(exc))
        error = exc

    return output.strip(), error

def terminate_and_wait_child(process, name, timeout, logger):
    logger.info("Terminating %s: pid: %s...", name, str(process.pid))
    process.terminate()
    try:
        process.wait(timeout)
    except subprocess.TimeoutExpired as exc:
        logger.info("Timeout in waiting for %s termination; pid: %s; going to force to stop...", name, str(process.pid));
        if name == "fluent-bit":
            logger.info("Shutdown complete")
        process.kill()
        _, _ = process.communicate()
