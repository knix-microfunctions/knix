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

import unittest
import os, sys
import json
import time

class StorageActionsTest(unittest.TestCase):

    def setUp(self):
        self._settings = self._get_settings()
        self._client = MfnClient()

    def test_list_keys(self):
        key_list = self._client.list_keys()

        old_len = len(key_list)

        ts = str(time.time() * 1000.0)
        key = "my_random_key_" + ts

        self._client.put(key, ts)

        key_list2 = self._client.list_keys()

        new_len = len(key_list2)

        if (old_len+1) == new_len:
            self._report("test_list_keys", True)
        else:
            self._report("test_list_keys", False, old_len + 1, new_len)

    def test_get_put_delete(self):
        ts = str(time.time() * 1000.0)
        key = "my_random_key_" + ts
        val = self._client.get(key)

        # should be None
        if val is None:
            self._report("test_get_non-existing_key", True)
        else:
            self._report("test_get_non-existing_key", False, None, val)

        self._client.put(key, ts)
        val2 = self._client.get(key)

        # should be ts
        if val2 == ts:
            self._report("test_get_existing_key", True)
        else:
            self._report("test_get_existing_key", False, ts, val2)

        self._client.delete(key)
        val3 = self._client.get(key)

        # should be None
        if val3 is None:
            self._report("test_delete_key", True)
        else:
            self._report("test_delete_key", False, None, val3)

    def tearDown(self):
        self._client.disconnect()

    # internal functions

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

        return settings

    def _report(self, test_name, success, expected=None, actual=None):
        if success:
            print(test_name + " test " + mfntestpassed)
        else:
            print(test_name + " test " + mfntestfailed + '(result: ' + json.dumps(actual) + ', expected: ' + json.dumps(expected) + ')')
