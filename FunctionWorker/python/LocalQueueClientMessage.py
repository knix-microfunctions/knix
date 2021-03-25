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

class LocalQueueClientMessage:

    def __init__(self, lqm=None, key=None, value=None):
        if lqm is None and key is None and value is None:
            return
        elif lqm is not None:
            self._message = lqm
            self._key = self._message["key"]
            self._value = self._message["value"]
        elif key is not None and value is not None:
            self._key = key
            self._value = value
            self._message = {"key": self._key, "value": self._value}

    def get_key(self):
        return self._key

    def get_value(self):
        return self._value

    def get_message(self):
        return self._message
