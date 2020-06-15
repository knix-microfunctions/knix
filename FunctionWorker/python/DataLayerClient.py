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

import time

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TCompactProtocol

from data_layer.message.ttypes import KeyValuePair
from data_layer.message.ttypes import Metadata
from data_layer.service import DataLayerService

MAX_RETRIES=3

class DataLayerClient:

    def __init__(self, locality=1, sid=None, wid=None, suid=None, is_wf_private=False, for_mfn=False, connect="127.0.0.1:4998", init_tables=False, drop_keyspace=False):
        self.dladdress = connect

        if for_mfn:
            self.keyspace = "sbox_" + sid
            self.tablename = "sbox_default_" + sid
            self.maptablename = "sbox_maps_" + sid
            self.settablename = "sbox_sets_" + sid
            self.countertablename = "sbox_counters_" + sid
            self.triggersinfotablename = "triggersInfoTable"
            self.countertriggerstable = "counterTriggersTable"
            self.countertriggersinfotable = "counterTriggersInfoTable"
        else:
            if is_wf_private:
                self.keyspace = "sbox_" + sid
                self.tablename = "wf_" + wid
                self.maptablename = "wf_maps_" + wid
                self.settablename = "wf_sets_" + wid
                self.countertablename = "wf_counters_" + wid
                self.triggersinfotablename = "triggersInfoTable"
                self.countertriggerstable = "counterTriggersTable"
                self.countertriggersinfotable = "counterTriggersInfoTable"

            else:
                self.keyspace = "storage_" + suid
                self.tablename = "defaultTable"
                self.maptablename = "defaultMapTable"
                self.settablename = "defaultSetTable"
                self.countertablename = "defaultCounterTable"
                self.triggersinfotablename = "triggersInfoTable"
                self.countertriggerstable = "counterTriggersTable"
                self.countertriggersinfotable = "counterTriggersInfoTable"

        #print("Creating datalayer client in keyspace=%s, tablename=%s, maptablename=%s, settablename=%s, countertablename=%s" % (self.keyspace,self.tablename, self.maptablename, self.settablename, self.countertablename))
        self.locality = locality

        self.connect()

        if init_tables:
            self._initialize_tables()

        if drop_keyspace:
            self._drop_keyspace()

    def _initialize_tables(self):
        replication_factor = 3
        # just need the local instance
        if self.locality == 0:
            replication_factor = 1

        try:
            self.datalayer.createKeyspace(self.keyspace, Metadata(replicationFactor=replication_factor), self.locality)
            self.datalayer.createTable(self.keyspace, self.tablename, Metadata(tableType="default"), self.locality)
            self.datalayer.createMapTable(self.keyspace, self.maptablename, self.locality)
            self.datalayer.createSetTable(self.keyspace, self.settablename, self.locality)
            self.datalayer.createCounterTable(self.keyspace, self.countertablename, Metadata(tableType="counters"), self.locality)
            self.datalayer.createTable(self.keyspace, self.triggersinfotablename, Metadata(tableType="default"), self.locality)
            self.datalayer.createCounterTable(self.keyspace, self.countertriggerstable, Metadata(tableType="mfn_counter_trigger"), self.locality)
            self.datalayer.createTable(self.keyspace, self.countertriggersinfotable, Metadata(tableType="default"), self.locality)
        except Thrift.TException as exc:
            print("Could not initialize tables: " + str(exc))
            raise

    def _drop_keyspace(self):
        try:
            self.datalayer.dropKeyspace(self.keyspace, self.locality)
        except Thrift.TException as exc:
            print("Could not drop keyspace: " + str(exc))
            raise

    def connect(self):
        retry = 0.5 #s
        while True:
            try:
                host, port = self.dladdress.split(':')
                self.socket = TSocket.TSocket(host, int(port))
                self.transport = TTransport.TFramedTransport(self.socket)
                self.transport.open()
                self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
                self.datalayer = DataLayerService.Client(self.protocol)
                break
            except Thrift.TException as exc:
                if retry < 60:
                    print("[DataLayerClient] Could not connect due to "+str(exc)+", retrying in "+str(retry)+"s")
                    time.sleep(retry)
                    retry = retry * 2
                else:
                    raise

    # (key, value) operations
    def put(self, key, value, locality=None, tableName=None):
        #print("Client keyspace=%s, tablename=%s putting key %s" % (self.keyspace,self.tablename,key))
        status = False
        loc = self.locality if locality is None else locality
        table = self.tablename if tableName is None else tableName
        #print("[DataLayerClient] [PUT] keyspace=%s, tablename=%s putting key %s" % (self.keyspace,table,key))
        if value is None:
            value = ""
        for retry in range(MAX_RETRIES):
            try:
                value = value.encode()
                row = KeyValuePair(key, value)
                status = self.datalayer.insertRow(self.keyspace, table, row, loc)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed put: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed put: " + str(exc))
                raise

        return status

    def get(self, key, locality=None, tableName=None):
        #print("Client keyspace=%s, tablename=%s fetching key %s" % (self.keyspace,self.tablename,key))
        val = None
        loc = self.locality if locality is None else locality
        table = self.tablename if tableName is None else tableName
        #print("[DataLayerClient] [GET] keyspace=%s, tablename=%s getting key %s" % (self.keyspace,table,key))
        for retry in range(MAX_RETRIES):
            try:
                result = self.datalayer.selectRow(self.keyspace, table, key, loc)
                if result.key != "" and result.key == key:
                    val = result.value
                    val = val.decode()
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed get: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed get: " + str(exc))
                raise

        return val

    def delete(self, key, tableName=None):
        status = False
        table = self.tablename if tableName is None else tableName
        #print("[DataLayerClient] [DELETE] keyspace=%s, tablename=%s deleting key %s" % (self.keyspace,table,key))
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.deleteRow(self.keyspace, table, key, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed delete: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed delete: " + str(exc))
                raise

        return status

    # map operations
    def createMap(self, mapname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.createMap(self.keyspace, self.maptablename, mapname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed createMap: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed createMap: " + str(exc))
                raise

        return status

    def putMapEntry(self, mapname, key, value, locality=None):
        status = False
        loc = self.locality if locality is None else locality
        if value is None:
            value = ""
        for retry in range(MAX_RETRIES):
            try:
                value = value.encode()
                row = KeyValuePair(key, value)
                status = self.datalayer.putEntryToMap(self.keyspace, self.maptablename, mapname, row, loc)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed putMapEntry: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed putMapEntry: " + str(exc))
                raise

        return status

    def getMapEntry(self, mapname, key):
        val = None
        for retry in range(MAX_RETRIES):
            try:
                kvp = self.datalayer.getEntryFromMap(self.keyspace, self.maptablename, mapname, key, self.locality)
                if kvp.key != "" and kvp.key == key:
                    val = kvp.value
                    val = val.decode()
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getMapEntry: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed getMapEntry: " + str(exc))
                raise

        return val

    def deleteMapEntry(self, mapname, key):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.removeEntryFromMap(self.keyspace, self.maptablename, mapname, key, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed deleteMapEntry: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed deleteMapEntry: " + str(exc))
                raise
        return status

    def containsMapKey(self, mapname, key):
        ret = False
        for retry in range(MAX_RETRIES):
            try:
                ret = self.datalayer.containsKeyInMap(self.keyspace, self.maptablename, mapname, key, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed containsMapKey: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed containsMapKey: " + str(exc))
                raise

        return ret

    def getMapKeys(self, mapname):
        keys = None
        for retry in range(MAX_RETRIES):
            try:
                keyset = self.datalayer.retrieveKeysetFromMap(self.keyspace, self.maptablename, mapname, self.locality)
                if keyset.key != "" and keyset.key == mapname:
                    keys = keyset.items
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getMapKeys: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed getMapKeys: " + str(exc))
                raise

        return keys

    def retrieveMap(self, mapname):
        mapentries = None
        for retry in range(MAX_RETRIES):
            try:
                mapentries = self.datalayer.retrieveAllEntriesFromMap(self.keyspace, self.maptablename, mapname, self.locality)
                if mapentries.key != "" and mapentries.key == mapname:
                    mapentries = mapentries.entries
                    for key in mapentries:
                        mapentries[key] = mapentries[key].decode()
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed retrieveMap: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed retrieveMap: " + str(exc))
                raise

        return mapentries

    def clearMap(self, mapname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.clearMap(self.keyspace, self.maptablename, mapname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed clearMap: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed clearMap: " + str(exc))
                raise
        return status

    def deleteMap(self, mapname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.deleteMap(self.keyspace, self.maptablename, mapname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed deleteMap: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed deleteMap: " + str(exc))
                raise
        return status

    def getMapNames(self, start_index=0, end_index=2147483647):
        maps = None
        for retry in range(MAX_RETRIES):
            try:
                maps = self.datalayer.selectMaps(self.keyspace, self.maptablename, start_index, end_index, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getMapNames: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed getMapNames: " + str(exc))
                raise
        return maps

    # set operations
    def createSet(self, setname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.createSet(self.keyspace, self.settablename, setname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed createSet: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed createSet: " + str(exc))
                raise
        return status

    def addSetEntry(self, setname, item):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.addItemToSet(self.keyspace, self.settablename, setname, item, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed addSetEntry: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed addSetEntry: " + str(exc))
                raise
        return status

    def removeSetEntry(self, setname, item):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.removeItemFromSet(self.keyspace, self.settablename, setname, item, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed removeSetEntry: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed removeSetEntry: " + str(exc))
                raise
        return status

    def containsSetItem(self, setname, item):
        ret = False
        for retry in range(MAX_RETRIES):
            try:
                ret = self.datalayer.containsItemInSet(self.keyspace, self.settablename, setname, item, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed containsSetItem: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed containsSetItem: " + str(exc))
                raise
        return ret

    def retrieveSet(self, setname):
        items = None
        for retry in range(MAX_RETRIES):
            try:
                itemsset = self.datalayer.retrieveSet(self.keyspace, self.settablename, setname, self.locality)
                if itemsset.key != "" and itemsset.key == setname:
                    items = itemsset.items
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed retrieveSet: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed retrieveSet: " + str(exc))
                raise

        return items

    def clearSet(self, setname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.clearSet(self.keyspace, self.settablename, setname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed clearSet: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed clearSet: " + str(exc))
                raise
        return status

    def deleteSet(self, setname):
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.deleteSet(self.keyspace, self.settablename, setname, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed deleteSet: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed deleteSet: " + str(exc))
                raise
        return status

    def getSetNames(self, start_index=0, end_index=2147483647):
        sets = None
        for retry in range(MAX_RETRIES):
            try:
                sets = self.datalayer.selectSets(self.keyspace, self.settablename, start_index, end_index, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getSetNames: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed getSetNames: " + str(exc))
                raise
        return sets

    # counter operations
    def createCounter(self, countername, count, tableName=None):
        status = False
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.createCounter(self.keyspace, table, countername, count, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed createCounter: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed createCounter: " + str(exc))
                raise
        return status

    def getCounter(self, countername, tableName=None):
        cv = 0
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                kcp = self.datalayer.getCounter(self.keyspace, table, countername, self.locality)
                if kcp.key != "" and kcp.key == countername:
                    cv = kcp.counter
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getCounter: " + str(exc))
            except Exception as exc:
                print("[DataLayerClient] failed getCounter: " + str(exc))
                raise
        return cv

    def incrementCounter(self, countername, increment, tableName=None):
        status = False
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                kcp = self.datalayer.incrementCounter(self.keyspace, table, countername, increment, self.locality)
                if kcp.key != "" and kcp.key == countername:
                    status = True
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed incrementCounter: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed incrementCounter: " + str(exc))
                raise
        return status

    def decrementCounter(self, countername, decrement, tableName=None):
        status = False
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                kcp = self.datalayer.decrementCounter(self.keyspace, table, countername, decrement, self.locality)
                if kcp.key != "" and kcp.key == countername:
                    status = True
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed decrementCounter: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed decrementCounter: " + str(exc))
                raise
        return status

    def deleteCounter(self, countername, tableName=None):
        status = False
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.deleteCounter(self.keyspace, table, countername, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed deleteCounter: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed deleteCounter: " + str(exc))
                raise
        return status

    def getCounterNames(self, start_index=0, end_index=2147483647, tableName=None):
        counters = None
        table = self.countertablename if tableName is None else tableName
        for retry in range(MAX_RETRIES):
            try:
                counters = self.datalayer.selectCounters(self.keyspace, table, start_index, end_index, self.locality)
                break
            except TTransport.TTransportException as exc:
                print("[DataLayerClient] Reconnecting because of failed getCounterNames: " + str(exc))
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed getCounterNames: " + str(exc))
                raise
        return counters

    def createTriggerableTable(self, tableName):
        #print("[DataLayerClient] createTriggerableTable " + tableName + ", keyspace: " + self.keyspace)
        status = False
        for retry in range(MAX_RETRIES):
            try:
                status = self.datalayer.createTable(self.keyspace, tableName, Metadata(tableType="triggers"), self.locality)
                break
            except TTransport.TTransportException as exc:
                self.connect()
            except Exception as exc:
                print("[DataLayerClient] failed createTable: " + str(exc))
                raise
        return status

    def shutdown(self):
        try:
            self.transport.close()
        except Thrift.TException as exc:
            print(str(exc))
        finally:
            self.transport.close()
