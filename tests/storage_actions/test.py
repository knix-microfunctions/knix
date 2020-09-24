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

import json
import random
import os, sys
import time
import unittest

class StorageActionsTest(unittest.TestCase):

    def setUp(self):
        self._settings = self._get_settings()
        self._client = MfnClient()

    # kv operations
    #@unittest.skip("")
    def test_get_put_delete(self):
        key_list = self._client.list_keys()
        old_len = len(key_list)

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

        key_list2 = self._client.list_keys()
        new_len = len(key_list2)

        if (old_len+1) == new_len:
            self._report("test_list_keys", True)
        else:
            self._report("test_list_keys", False, old_len + 1, new_len)

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

    # map operations
    def test_map_operations(self):
        map_list = self._client.list_maps()
        old_len = len(map_list)

        ts = str(time.time() * 1000.0)
        mapname = "my_random_mapname_" + ts

        rval = ts + "_" + str(random.randint(0, 1000000))
        rkey = "my_random_key_" + str(random.randint(0, 1000000))
        rkey2 = "my_random_key_" + str(random.randint(0, 1000000))
        rkey3 = "my_random_key_" + str(random.randint(0, 1000000))

        self._client.create_map(mapname)
        # the creation of a map doesn't actually take place unless key-value pair is added
        self._client.put_map_entry(mapname, rkey, rval)

        time.sleep(3)
        map_list2 = self._client.list_maps()
        new_len = len(map_list2)

        if (old_len+1) == new_len:
            self._report("test_create_map", True)
            self._report("test_list_maps", True)
        else:
            self._report("test_create_map", False, old_len + 1, new_len)
            self._report("test_list_maps", False, old_len + 1, new_len)

        val = self._client.get_map_entry(mapname, rkey)
        val_none = self._client.get_map_entry(mapname, rkey2)

        if val == rval and val_none is None:
            self._report("test_get_map_entry", True)
            self._report("test_put_map_entry", True)
        else:
            self._report("test_get_map_entry", False, val, rval)
            self._report("test_put_map_entry", False, val, rval)

        self._client.put_map_entry(mapname, rkey2, rval)
        self._client.put_map_entry(mapname, rkey3, rval)

        mapentries = self._client.retrieve_map(mapname)

        if all (k in mapentries.keys() for k in (rkey, rkey2, rkey3)) and\
            all (v == rval for v in mapentries.values()):
            self._report("test_retrieve_map", True)
        else:
            self._report("test_retrieve_map", False, mapentries, {rkey: rval, rkey2: rval, rkey3: rval})

        mapkeys = self._client.get_map_keys(mapname)

        if all (k in mapkeys for k in mapentries.keys()):
            self._report("test_get_map_keys", True)
        else:
            self._report("test_get_map_keys", False, mapkeys, mapentries.keys())

        contains = self._client.contains_map_key(mapname, rkey)
        contains2 = self._client.contains_map_key(mapname, rkey2)

        self._client.delete_map_entry(mapname, rkey2)

        contains3 = self._client.contains_map_key(mapname, rkey2)

        if contains and contains2 and not contains3:
            self._report("test_contains_map_key", True)
            self._report("test_delete_map_key", True)
        else:
            self._report("test_contains_map_key", False, True, True)
            self._report("test_delete_map_key", False, contains3, False)

        self._client.clear_map(mapname)

        mapkeys2 = self._client.get_map_keys(mapname)

        if not mapkeys2:
            self._report("test_clear_map", True)
        else:
            self._report("test_clear_map", False, mapkeys2, [])

        self._client.delete_map(mapname)
        time.sleep(3)

        map_list3 = self._client.list_maps()
        new_len2 = len(map_list3)

        if old_len == new_len2 and new_len == new_len2 + 1:
            self._report("test_delete_map", True)
        else:
            self._report("test_delete_map", False, new_len2, old_len)



    # set operations
    #@unittest.skip("")
    def test_set_operations(self):
        set_list = self._client.list_sets()
        old_len = len(set_list)

        ts = str(time.time() * 1000.0)
        setname = "my_random_setname_" + ts

        ts2 = str(time.time() * 1000.0)
        ritem = "my_random_item_" + ts2

        self._client.create_set(setname)
        # the creation of a set doesn't actually take place unless an item is added
        self._client.add_set_entry(setname, ritem)

        time.sleep(3)
        set_list2 = self._client.list_sets()
        new_len = len(set_list2)

        if (old_len+1) == new_len:
            self._report("test_create_set", True)
            self._report("test_list_sets", True)
        else:
            self._report("test_create_set", False, old_len + 1, new_len)
            self._report("test_list_sets", False, old_len + 1, new_len)

        contains = self._client.contains_set_item(setname, ritem)

        if contains:
            self._report("test_add_set_entry", True)
        else:
            self._report("test_add_set_entry", False, None, True)

        content = self._client.retrieve_set(setname)

        if isinstance(content, set) and ritem in content:
            self._report("test_retrieve_set", True)
        else:
            self._report("test_retrieve_set", False, ritem in content, True)

        self._client.remove_set_entry(setname, ritem)

        content2 = self._client.retrieve_set(setname)
        contains2 = self._client.contains_set_item(setname, ritem)

        if not contains2 and ritem not in content2:
            self._report("test_remove_set_entry", True)
            self._report("test_retrieve_set", True)
        else:
            self._report("test_remove_set_entry", False, contains2, False)
            self._report("test_retrieve_set", False, ritem in content2, False)

        self._client.add_set_entry(setname, "randomitem1")
        self._client.add_set_entry(setname, "randomitem2")
        self._client.add_set_entry(setname, "randomitem3")
        self._client.add_set_entry(setname, "randomitem4")
        self._client.add_set_entry(setname, "randomitem5")

        content3 = self._client.retrieve_set(setname)

        self._client.clear_set(setname)

        content4 = self._client.retrieve_set(setname)

        if len(content3) == 5 and len(content4) == 0:
            self._report("test_clear_set", True)
        else:
            self._report("test_clear_set", False, len(content4), 0)

        self._client.delete_set(setname)
        time.sleep(3)

        set_list3 = self._client.list_sets()
        new_len2 = len(set_list3)

        if old_len == new_len2 and new_len == new_len2 + 1:
            self._report("test_delete_set", True)
        else:
            self._report("test_delete_set", False, new_len2, old_len)

    # counter operations
    #@unittest.skip("")
    def test_create_get_increment_decrement_delete_counter(self):
        counter_list = self._client.list_counters()
        old_len = len(counter_list)
        ts = str(time.time() * 1000.0)
        countername = "my_random_countername_" + ts

        rval = random.randint(0, 100)

        self._client.create_counter(countername, rval)

        counter_list2 = self._client.list_counters()
        new_len = len(counter_list2)

        if (old_len+1) == new_len:
            self._report("test_list_counters", True)
        else:
            self._report("test_list_counters", False, old_len + 1, new_len)

        if countername not in counter_list and countername in counter_list2:
            self._report("test_create_counter", True)
        else:
            self._report("test_create_counter", False, None, countername)

        val = self._client.get_counter(countername)

        if val == rval:
            self._report("test_get_counter", True)
        else:
            self._report("test_get_counter", False, rval, val)

        r2 = random.randint(0, 100)
        self._client.increment_counter(countername, r2)

        val2 = self._client.get_counter(countername)

        if val2 == val + r2:
            self._report("test_increment_counter", True)
        else:
            self._report("test_increment_counter", False, val + r2, val2)

        r3 = random.randint(0, 100)
        self._client.decrement_counter(countername, r3)

        val3 = self._client.get_counter(countername)

        if val3 == val2 - r3:
            self._report("test_decrement_counter", True)
        else:
            self._report("test_decrement_counter", False, val2 - r3, val3)

        self._client.delete_counter(countername)

        # sleep a little to make the change to take effect
        time.sleep(3)

        counter_list3 = self._client.list_counters()

        if countername not in counter_list3:
            self._report("test_delete_counter", True)
        else:
            self._report("test_delete_counter", False, None, countername)

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
