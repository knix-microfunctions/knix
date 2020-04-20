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

class MicroFunctionsLogWriter:
    '''
    MicroFunctionsLogWriter class
    This class provides the mechanisms
    to utilize the 'print' statements inside the user functions.
    Alternatively, MicroFunctionsAPI.log() statement can be used.
    '''
    def __init__(self, logger, level=logging.DEBUG):
        self._logger = logger
        self._level = level

    def write(self, msg):
        msg = msg.rstrip()
        lines = msg.splitlines()
        for line in lines:
            line = line.rstrip()
            self._logger.log(self._level, line)

    def flush(self):
        pass

