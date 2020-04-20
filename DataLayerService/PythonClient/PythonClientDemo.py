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

from data_layer.message.ttypes import KeyValuePair
from data_layer.message.ttypes import KeySetPair
from data_layer.service import DataLayerService

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TCompactProtocol

import time

def main():
    socket = TSocket.TSocket("10.0.2.15", 4998)
    transport = TTransport.TFramedTransport(socket)
    protocol = TCompactProtocol.TCompactProtocol(transport)
    datalayer = DataLayerService.Client(protocol)
    
    try:
        transport.open()
        
        keyspace = 'debug_sand'
        replicationFactor = 1
        locality = 1    # 0 means local, and 1 means remote (Riak)
        
        table = 'DATA'
        key = 'test_key'
        value = "123"
        
        s1 = datalayer.createKeyspace(keyspace, replicationFactor, locality)
        s2 = datalayer.createTable(keyspace, table, locality)
        
        row = KeyValuePair(key, value)
        s3 = datalayer.insertRow(keyspace, table, row, locality)
        
        result = datalayer.selectRow(keyspace, table, key, locality)
        print(result.key)
        print(result.value)
        
        s5 = datalayer.dropTable(keyspace, table, locality)

        print(s5)
        # below shows how to operate CRDT map
        map_table = 'MAPS'
    
        allmaps = datalayer.selectMaps(keyspace, map_table, 0, 10000, 1)
        print(allmaps)
    
        s6 = datalayer.createMapTable(keyspace, map_table, locality)
    
        print("result createMapTable: ", s6)
        time.sleep(2)
    
        map_name = 'MAP'
        s7 = datalayer.createMap(keyspace, map_table, map_name, locality)
    
        print("result createMap: ", s7)
        time.sleep(2)
    
        allmaps = datalayer.selectMaps(keyspace, map_table, 0, 10000, 1)
        print(allmaps)

        s8 = datalayer.putEntryToMap(keyspace, map_table, map_name, KeyValuePair(key, value), locality)
        time.sleep(2)
        
        entry = datalayer.getEntryFromMap(keyspace, map_table, map_name, key, locality)
        print(entry.key + " -> " + entry.value)
        
        keyset = datalayer.retrieveKeysetFromMap(keyspace, map_table, map_name, locality)
        print(keyset.key + " -> " + keyset.items)
        
        entryset = datalayer.retrieveAllEntriesFromMap(keyspace, map_table, map_name, locality)
        print(entryset.key)
        print(entryset.entries)
        
        s9 = datalayer.deleteMap(keyspace, map_table, map_name, locality)
        
        s10 = datalayer.dropMapTable(keyspace, map_table, locality)
        # above shows how to operate CRDT map
    
        
        s11 = datalayer.dropKeyspace(keyspace, locality)


    except Thrift.TException as e:
        print(e)
        
    finally:
        transport.close()

if __name__ == "__main__":
    main()


