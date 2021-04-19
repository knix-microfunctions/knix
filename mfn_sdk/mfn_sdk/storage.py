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

import requests
import base64
import json
import random
import sys
import time
import logging

from .deprecated import deprecated

#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class Storage(object):

    def __init__(self, s, token, mgmturl):
        self._token = token
        self._mgmturl = mgmturl
        self._session = s

    def _init_common_parameters(self):
        user = {}
        user["token"] = self._token
        data = {}
        data["user"] = user

        data_to_send = {}
        data_to_send["action"] = "performStorageAction"
        data_to_send["data"] = data

        return data_to_send

    def _fill_storage_parameters(self, data_type, parameters, wid):
        storage = {}
        storage["data_type"] = data_type
        storage["parameters"] = parameters
        if wid is not None:
            storage["workflowid"] = wid

        return storage

    # KV operations
    def put(self, key, value, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "putdata"
        parameters["key"] = key
        parameters["value"] = value

        data_to_send["data"]["storage"] = self._fill_storage_parameters("kv", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("PUT failed: " + r.json()["data"]["message"])

    def get(self, key, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "getdata"
        parameters["key"] = key

        data_to_send["data"]["storage"] = self._fill_storage_parameters("kv", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("GET failed: " + r.json()["data"]["message"])
        else:
            val = r.json()["data"]["value"]
            if val is not None:
                val = base64.b64decode(r.json()["data"]["value"]).decode()
            return val

    def delete(self, key, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "deletedata"
        parameters["key"] = key

        data_to_send["data"]["storage"] = self._fill_storage_parameters("kv", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETE failed: " + r.json()["data"]["message"])

    def list_keys(self, start=0, count=2000, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "listkeys"
        parameters["start"] = start
        parameters["count"] = count

        data_to_send["data"]["storage"] = self._fill_storage_parameters("kv", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("LISTKEYS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["keylist"]

    # map operations
    def create_map(self, mapname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "createmap"
        parameters["mapname"] = mapname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CREATEMAP failed: " + r.json()["data"]["message"])

    def put_map_entry(self, mapname, key, value, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "putmapentry"
        parameters["mapname"] = mapname
        parameters["key"] = key
        parameters["value"] = value

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("PUTMAPENTRY failed: " + r.json()["data"]["message"])

    def get_map_entry(self, mapname, key, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "getmapentry"
        parameters["mapname"] = mapname
        parameters["key"] = key

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("GETMAPENTRY failed: " + r.json()["data"]["message"])
        else:
            val = r.json()["data"]["value"]
            if val is not None:
                val = base64.b64decode(r.json()["data"]["value"]).decode()
            return val

    def delete_map_entry(self, mapname, key, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "deletemapentry"
        parameters["mapname"] = mapname
        parameters["key"] = key

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETEMAPENTRY failed: " + r.json()["data"]["message"])

    def retrieve_map(self, mapname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "retrievemap"
        parameters["mapname"] = mapname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("RETRIEVEMAP failed: " + r.json()["data"]["message"])

        return r.json()["data"]["mapentries"]

    def contains_map_key(self, mapname, key, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "containsmapkey"
        parameters["mapname"] = mapname
        parameters["key"] = key

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CONTAINSMAPKEY failed: " + r.json()["data"]["message"])

        return r.json()["data"]["containskey"]

    def get_map_keys(self, mapname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "getmapkeys"
        parameters["mapname"] = mapname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("GETMAPKEYS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["mapkeys"]

    def clear_map(self, mapname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "clearmap"
        parameters["mapname"] = mapname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CLEARMAP failed: " + r.json()["data"]["message"])

    def delete_map(self, mapname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "deletemap"
        parameters["mapname"] = mapname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETEMAP failed: " + r.json()["data"]["message"])

    def list_maps(self, start=0, count=2000, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "listmaps"
        parameters["start"] = start
        parameters["count"] = count

        data_to_send["data"]["storage"] = self._fill_storage_parameters("map", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("LISTMAPS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["maplist"]

    # set operations
    def create_set(self, setname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "createset"
        parameters["setname"] = setname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CREATESET failed: " + r.json()["data"]["message"])

    def add_set_entry(self, setname, item, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "addsetentry"
        parameters["setname"] = setname
        parameters["item"] = item

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("ADDSETENTRY failed: " + r.json()["data"]["message"])

    def remove_set_entry(self, setname, item, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "removesetentry"
        parameters["setname"] = setname
        parameters["item"] = item

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("REMOVESETENTRY failed: " + r.json()["data"]["message"])

    def contains_set_item(self, setname, item, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "containssetitem"
        parameters["setname"] = setname
        parameters["item"] = item

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CONTAINSSETITEM failed: " + r.json()["data"]["message"])

        return r.json()["data"]["containsitem"]

    def retrieve_set(self, setname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "retrieveset"
        parameters["setname"] = setname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("RETRIEVESET failed: " + r.json()["data"]["message"])

        return set(r.json()["data"]["items"])

    def clear_set(self, setname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "clearset"
        parameters["setname"] = setname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CLEARSET failed: " + r.json()["data"]["message"])

    def delete_set(self, setname, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "deleteset"
        parameters["setname"] = setname

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETESET failed: " + r.json()["data"]["message"])

    def list_sets(self, start=0, count=2000, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "listsets"
        parameters["start"] = start
        parameters["count"] = count

        data_to_send["data"]["storage"] = self._fill_storage_parameters("set", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("LISTSETS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["setlist"]

    # counter operations
    def create_counter(self, countername, countervalue, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "createcounter"
        parameters["countername"] = countername
        parameters["countervalue"] = countervalue

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("CREATECOUNTER failed: " + r.json()["data"]["message"])

    def get_counter(self, countername, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "getcounter"
        parameters["countername"] = countername

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("GETCOUNTER failed: " + r.json()["data"]["message"])

        return r.json()["data"]["countervalue"]

    def increment_counter(self, countername, increment, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "incrementcounter"
        parameters["countername"] = countername
        parameters["increment"] = increment

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("INCREMENTCOUNTER failed: " + r.json()["data"]["message"])

    def decrement_counter(self, countername, decrement, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "decrementcounter"
        parameters["countername"] = countername
        parameters["decrement"] = decrement

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DECREMENTCOUNTER failed: " + r.json()["data"]["message"])

    def delete_counter(self, countername, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "deletecounter"
        parameters["countername"] = countername

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETECOUNTER failed: " + r.json()["data"]["message"])

    def list_counters(self, start=0, count=2000, wid=None):
        data_to_send = self._init_common_parameters()

        parameters = {}
        parameters["action"] = "listcounters"
        parameters["start"] = start
        parameters["count"] = count

        data_to_send["data"]["storage"] = self._fill_storage_parameters("counter", parameters, wid)

        r = self._session.post(self._mgmturl, params={}, json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("LISTCOUNTERS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["counterlist"]

class TriggerableBucket(Storage):
    """ TriggerableBucket is a user-defined storage bucket that can also be used to trigger workflows upon data changes
    """

    def __init__(self,client,bname,bassociated_workflows=[],bmetadatalist=[]):
        super().__init__(client._s, client.token, client.mgmturl)
        self.client=client
        self._name=bname
        self._update(bassociated_workflows,bmetadatalist)

    def _fill_storage_parameters(self, data_type, parameters, wid):
        storage = {}
        storage["data_type"] = data_type
        parameters["tableName"] = self._name
        storage["parameters"] = parameters
        if wid is not None:
            storage["workflowid"] = wid

        return storage

    def _update(self,bassociated_workflows,bmetadatalist):
        self._associated_workflows=bassociated_workflows
        self._metadata=bmetadatalist

    @property
    def associated_workflows(self):
        # TODO: decide whether to auto-fetch details when associated_workflows is accessed 
        return self._associated_workflows

    def associate_workflow(self, wf):
        self.client.bind_bucket(self._name,wf._name)

    def disassociate_workflow(self, wf):
        self.client.unbind_bucket(self._name,wf._name)
