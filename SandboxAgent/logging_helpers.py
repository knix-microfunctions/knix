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

import logging
import re

import process_utils

def setup_logger(sandboxid, log_filename):
    logger = logging.getLogger(sandboxid)
    logger.setLevel(logging.DEBUG)

    # File handler
    hdlr = logging.FileHandler(log_filename)
    hdlr.setLevel(logging.DEBUG)
    hdlr.formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    logger.addHandler(hdlr)

    # StreamHandler
    shdlr = logging.StreamHandler()
    shdlr.setLevel(logging.DEBUG)
    shdlr.formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    logger.addHandler(shdlr)

    global print
    print = logger.info

    return logger

def setup_fluentbit_and_elasticsearch_index(logger, fluentbit_folder, elasticsearch_address, index_wf, index_fe):
    return setup_fluentbit(logger, fluentbit_folder, elasticsearch_address, index_wf, index_fe)

def setup_fluentbit(logger, fluentbit_folder, elasticsearch_address, index_wf, index_fe):
    elasticsearch = elasticsearch_address.strip().split(':')
    if elasticsearch is not None and len(elasticsearch) > 1 and elasticsearch[0] is not None and elasticsearch[0] != '' and elasticsearch[1] is not None and elasticsearch[1] != '':
        # Generate fluent-bit configuration file
        try:
            gen_fluentbit_config(logger, fluentbit_folder, elasticsearch[0], elasticsearch[1], index_wf, index_fe)
            # Launch fluent-bit
            return launch_fluentbit(logger, fluentbit_folder)
        except Exception as exc:
            logger.exception("Unable to launch fluent-bit: %s", str(exc))

    return None, _

def gen_fluentbit_config(logger, fluentbit_folder, elasticsearch_host, elasticsearch_port, index_wf, index_fe):
    text = ''
    input_file = fluentbit_folder + '/conf/fluent-bit.conf.j2'
    output_file = fluentbit_folder + '/conf/fluent-bit.conf'
    # read template file
    logger.info("Reading: %s", input_file)
    with open(input_file) as f:
        text = f.read()
    # replace templates with real values
    text = re.sub('{{ ELASTICSEARCH_HOST }}', elasticsearch_host, text)
    text = re.sub('{{ ELASTICSEARCH_PORT }}', elasticsearch_port, text)
    text = re.sub('{{ INDEX_NAME_WF }}', index_wf, text)
    text = re.sub('{{ INDEX_NAME_FE }}', index_fe, text)
    # write config file
    with open(output_file, 'w') as f:
        f.write(text)
    logger.info("Written: %s", output_file)

def launch_fluentbit(logger, fluentbit_folder):
    cmd = fluentbit_folder + '/bin/fluent-bit'
    cmd = cmd + ' -c ' + fluentbit_folder + '/conf/fluent-bit.conf'
    logger.info("Launching fluent-bit via cmd: %s", cmd)

    command_args_map = {}
    command_args_map["command"] = cmd
    command_args_map["wait_output"] = True

    error, process = process_utils.run_command(cmd, logger, wait_output=True)
    if error is None:
        logger.info("fluent-bit launched with pid: %s", str(process.pid))
        return process, command_args_map

    return None, _
