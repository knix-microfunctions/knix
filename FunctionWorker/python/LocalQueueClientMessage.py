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

from struct import pack, unpack

class LocalQueueClientMessage:
    '''
    This class defines the message data structure used by the function worker.
    It provides the utilities to convert the local queue message
    and make the key and value fields easily accessible.
    '''
    def __init__(self, lqm=None, key=None, value=None):
        if lqm is None and key is None and value is None:
            return
        elif lqm is not None:
            self._serialized = lqm.payload
            self._deserialize()
        elif key is not None and value is not None:
            self._key = key
            self._value = value
            self._serialize()

    def _serialize(self):
        length = 4 + len(self._key)
        self._serialized = pack('!I', length)
        self._serialized = self._serialized + self._key.encode() + self._value.encode()
        self._serialized = self._serialized.decode()

    def _deserialize(self):
        length = unpack('!I', self._serialized[0:4])[0]
        self._key = self._serialized[4:length].decode()
        self._value = self._serialized[length:].decode()

    def get_key(self):
        return self._key

    def get_value(self):
        return self._value

    def get_serialized(self):
        return self._serialized

