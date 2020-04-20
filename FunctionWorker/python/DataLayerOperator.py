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

from DataLayerClient import DataLayerClient

class DataLayerOperator:

    def __init__(self, suid, sid, wid, datalayer):
        self._storage_userid = suid
        self._sandboxid = sid
        self._workflowid = wid
        self._datalayer = datalayer

        # global data layer clients for either workflow-private data or user storage
        self._data_layer_client = None
        self._data_layer_client_private = None

        # TODO (?): use the local data layer for operations regarding KV, maps, sets and counters instead of in-memory data structures (e.g., transient_data_output)
        # and store the operations/data for is_queued = True operations,
        # so that we can synchronize it with the global data layer
        # (key, value) store
        self.transient_data_output = {}
        self.transient_data_output_private = {}

        self.data_to_be_deleted = {}
        self.data_to_be_deleted_private = {}

        self.map_output = {}
        self.set_output = {}
        self.counter_output = {}

        self.map_output_delete = {}
        self.set_output_delete = {}
        self.counter_output_delete = {}


    # TODO: update to use local data layer for (key, value) operations
    def put(self, key, value, is_private=False, is_queued=False, table=None):
        if is_queued:
            if is_private:
                self.transient_data_output_private[key] = value
                if key in self.data_to_be_deleted_private:
                    self.data_to_be_deleted_private.pop(key, None)
            else:
                self.transient_data_output[key] = value
                if key in self.data_to_be_deleted:
                    self.data_to_be_deleted.pop(key, None)
        else:
            data_layer_client = self._get_data_layer_client(is_private)
            data_layer_client.put(key, value, tableName=table)

    def get(self, key, is_private=False, table=None):
        # check first transient_output
        # if not there, return the actual (global) data layer data item
        # if not there either, return empty string (as defined in the DataLayerClient)
        value = None
        # if the put() or delete() were called with is_queued=False (default),
        # then the below checks will still result in 'value is None'
        # if not, then value will be obtained from the transient output
        if is_private:
            if key in self.data_to_be_deleted_private:
                return ""
            value = self.transient_data_output_private.get(key)
        else:
            if key in self.data_to_be_deleted:
                return ""
            value = self.transient_data_output.get(key)

        if value is None:
            data_layer_client = self._get_data_layer_client(is_private)
            value = data_layer_client.get(key, tableName=table)

        return value

    def delete(self, key, is_private=False, is_queued=False, table=None):
        if is_queued:
            if is_private:
                self.transient_data_output_private.pop(key, None)
                self.data_to_be_deleted_private[key] = True
            else:
                self.transient_data_output.pop(key, None)
                self.data_to_be_deleted[key] = True
        else:
            data_layer_client = self._get_data_layer_client(is_private)
            data_layer_client.delete(key, tableName=table)

    # map operations
    def createMap(self, mapname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.createMap(mapname)

    def putMapEntry(self, mapname, key, value, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.putMapEntry(mapname, key, value)

    def getMapEntry(self, mapname, key, is_private=False):
        value = None

        # TODO: check transient data structure first

        if value is None:
            dlc = self._get_data_layer_client(is_private)
            value = dlc.getMapEntry(mapname, key)

        return value

    def deleteMapEntry(self, mapname, key, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.deleteMapEntry(mapname, key)

    def containsMapKey(self, mapname, key, is_private=False):
        ret = False

        # TODO: check transient data structure first

        if not ret:
            dlc = self._get_data_layer_client(is_private)
            ret = dlc.containsMapKey(mapname, key)

        return ret

    def retrieveMap(self, mapname, is_private=False):
        retmap = {}

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        retmap2 = dlc.retrieveMap(mapname)
        if retmap2 is not None:
            for k in retmap2:
                retmap[k] = retmap2[k]
            # TODO: 3. remove the ones deleted locally

        return retmap

    def getMapKeys(self, mapname, is_private=False):
        keys = set()

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        k2 = dlc.getMapKeys(mapname)
        if k2 is not None:
            # TODO: 3. remove the ones deleted locally
            keys = keys.union(k2)

        return keys

    def clearMap(self, mapname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.clearMap(mapname)

    def deleteMap(self, mapname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.deleteMap(mapname)

    def getMapNames(self, start_index=0, end_index=2147483647, is_private=False):
        maps = set()

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        m2 = dlc.getMapNames(start_index, end_index)
        if m2 is not None:
            # TODO: 3. remove the ones deleted locally
            maps = maps.union(m2)

        return list(maps)

    # set operations
    def createSet(self, setname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.createSet(setname)

    def addSetEntry(self, setname, item, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.addSetEntry(setname, item)

    def removeSetEntry(self, setname, item, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.removeSetEntry(setname, item)

    def containsSetItem(self, setname, item, is_private=False):
        ret = False

        # TODO: check transient data structure first

        if not ret:
            dlc = self._get_data_layer_client(is_private)
            ret = dlc.containsSetItem(setname, item)

        return ret

    def retrieveSet(self, setname, is_private=False):
        items = set()

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        i2 = dlc.retrieveSet(setname)
        if i2 is not None:
            # TODO: 3. remove the ones deleted locally
            items = items.union(i2)

        return items

    def clearSet(self, setname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.clearSet(setname)

    def deleteSet(self, setname, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.deleteSet(setname)

    def getSetNames(self, start_index=0, end_index=2147483647, is_private=False):
        sets = set()

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        s2 = dlc.getSetNames(start_index, end_index)
        if s2 is not None:
            # TODO: 3. remove the ones deleted locally
            sets = sets.union(s2)

        return list(sets)

    # counter operations
    def createCounter(self, countername, count, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.createCounter(countername, count)

    def getCounterValue(self, countername, is_private=False):
        value = 0

        # TODO: check transient data structure first and apply any changes to the global value

        dlc = self._get_data_layer_client(is_private)
        value = dlc.getCounter(countername)

        return value

    def incrementCounter(self, countername, increment, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.incrementCounter(countername, increment)

    def decrementCounter(self, countername, decrement, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.decrementCounter(countername, decrement)

    def deleteCounter(self, countername, is_private=False, is_queued=False):
        if is_queued:
            # TODO: use transient data structure in memory when the operation is queued
            pass
        else:
            dlc = self._get_data_layer_client(is_private)
            dlc.deleteCounter(countername)

    def getCounterNames(self, start_index=0, end_index=2147483647, is_private=False):
        counters = set()

        # XXX: should follow "read your writes"
        # the final result should include:
        # 1. all created locally
        # 2. all existing globally minus the ones deleted locally

        # TODO: 1. check local data layer first: get locally created and deleted

        # 2. retrieve all existing globally
        dlc = self._get_data_layer_client(is_private)
        c2 = dlc.getCounterNames(start_index, end_index)
        if c2 is not None:
            # TODO: 3. remove the ones deleted locally
            counters = counters.union(c2)

        return list(counters)

    def get_transient_data_output(self, is_private=False):
        '''
        Return the transient data, so that it can be committed to the data layer
        when the function instance finishes.
        '''
        if is_private:
            return self.transient_data_output_private

        return self.transient_data_output

    def get_data_to_be_deleted(self, is_private=False):
        '''
        Return the list of deleted data items, so that they can be committed to the data layer
        when the function instance finishes.
        '''
        if is_private:
            return self.data_to_be_deleted_private

        return self.data_to_be_deleted

    def _get_data_layer_client(self, is_private=False):
        '''
        Return the data layer client, so that it can be used to commit to the data layer
        when the function instance finishes.
        If it is not initialized yet, it will be initialized here.
        '''
        # TODO: need also the locality information
        if is_private:
            if self._data_layer_client_private is None:
                self._data_layer_client_private = DataLayerClient(locality=1, sid=self._sandboxid, wid=self._workflowid, is_wf_private=True, connect=self._datalayer)
            return self._data_layer_client_private

        if self._data_layer_client is None:
            self._data_layer_client = DataLayerClient(locality=1, suid=self._storage_userid, is_wf_private=False, connect=self._datalayer)
        return self._data_layer_client

    def _shutdown_data_layer_client(self):
        '''
        Shut down the data layer client if it has been initialized
        after the function instance finishes committing changes
        to the data layer.
        '''
        if self._data_layer_client_private is not None:
            self._data_layer_client_private.shutdown()
            self._data_layer_client_private = None

        if self._data_layer_client is not None:
            self._data_layer_client.shutdown()
            self._data_layer_client = None

