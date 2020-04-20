/*
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
namespace java org.microfunctions.data_layer
namespace py data_layer.service

include "./DataLayerMessage.thrift"

service DataLayerService {
	bool createKeyspace (1: string keyspace, 2: DataLayerMessage.Metadata metadata, 3: i32 locality),
	bool dropKeyspace (1: string keyspace, 2: i32 locality),
	
	i32 getReplicationFactor (1: string keyspace, 2: i32 locality),
	list<DataLayerMessage.KeyIntPair> listKeyspaces (1: i32 start, 2: i32 count, 3: i32 locality),
	list<DataLayerMessage.StringPair> listTables (1: string keyspace, 2: string tableType, 3: i32 start, 4: i32 count, 5: i32 locality),
	
	bool createTable (1: string keyspace, 2: string table, 3: DataLayerMessage.Metadata metadata, 4: i32 locality),
	bool createCounterTable (1: string keyspace, 2: string table, 3: DataLayerMessage.Metadata metadata, 4: i32 locality),
	bool createSetTable (1: string keyspace, 2: string table, 3: i32 locality),
	bool createMapTable (1: string keyspace, 2: string table, 3: i32 locality),
	
	bool dropTable (1: string keyspace, 2: string table, 3: i32 locality),
	bool dropCounterTable (1: string keyspace, 2: string table, 3: i32 locality),
	bool dropSetTable (1: string keyspace, 2: string table, 3: i32 locality),
	bool dropMapTable (1: string keyspace, 2: string table, 3: i32 locality),
	
	bool insertRow (1: string keyspace, 2: string table, 3: DataLayerMessage.KeyValuePair keyValuePair, 4: i32 locality),
	DataLayerMessage.KeyValuePair selectRow (1: string keyspace, 2: string table, 3: string key, 4: i32 locality),
	bool updateRow (1: string keyspace, 2: string table, 3: DataLayerMessage.KeyValuePair keyValuePair, 4: i32 locality),
	bool deleteRow (1: string keyspace, 2: string table, 3: string key, 4: i32 locality),
	list<string> selectKeys (1: string keyspace, 2: string table, 3: i32 start, 4: i32 count, 5: i32 locality),
	
	bool createCounter (1: string keyspace, 2: string table, 3: string counterName, 4: i64 initialValue, 5: i32 locality),
	DataLayerMessage.KeyCounterPair getCounter (1: string keyspace, 2: string table, 3: string counterName, 4: i32 locality),
	DataLayerMessage.KeyCounterPair incrementCounter (1: string keyspace, 2: string table, 3: string counterName, 4: i64 increment, 5: i32 locality),
	DataLayerMessage.KeyCounterPair decrementCounter (1: string keyspace, 2: string table, 3: string counterName, 4: i64 decrement, 5: i32 locality),
	bool deleteCounter (1: string keyspace, 2: string table, 3: string counterName, 4: i32 locality),
	list<string> selectCounters (1: string keyspace, 2: string table, 3: i32 start, 4: i32 count, 5: i32 locality),
	
	bool createSet (1: string keyspace, 2: string table, 3: string setName, 4: i32 locality),
	DataLayerMessage.KeySetPair retrieveSet (1: string keyspace, 2: string table, 3: string setName, 4: i32 locality),
	bool addItemToSet (1: string keyspace, 2: string table, 3: string setName, 4: string setItem, 5: i32 locality),
	bool removeItemFromSet (1: string keyspace, 2: string table, 3: string setName, 4: string setItem, 5: i32 locality),
	bool containsItemInSet (1: string keyspace, 2: string table, 3: string setName, 4: string setItem, 5: i32 locality),
	bool clearSet (1: string keyspace, 2: string table, 3: string setName, 4: i32 locality),
	i32 getSizeOfSet (1: string keyspace, 2: string table, 3: string setName, 4: i32 locality),
	bool deleteSet (1: string keyspace, 2: string table, 3: string setName, 4: i32 locality),
	list<string> selectSets (1: string keyspace, 2: string table, 3: i32 start, 4: i32 count, 5: i32 locality),
	
	bool createMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	DataLayerMessage.KeySetPair retrieveKeysetFromMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	DataLayerMessage.KeyMapPair retrieveAllEntriesFromMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	bool putEntryToMap (1: string keyspace, 2: string table, 3: string mapName, 4: DataLayerMessage.KeyValuePair keyValuePair, 5: i32 locality),
	DataLayerMessage.KeyValuePair getEntryFromMap (1: string keyspace, 2: string table, 3: string mapName, 4: string entryKey, 5: i32 locality),
	bool removeEntryFromMap (1: string keyspace, 2: string table, 3: string mapName, 4: string entryKey, 5: i32 locality),
	bool containsKeyInMap (1: string keyspace, 2: string table, 3: string mapName, 4: string entryKey, 5: i32 locality),
	bool clearMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	i32 getSizeOfMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	bool deleteMap (1: string keyspace, 2: string table, 3: string mapName, 4: i32 locality),
	list<string> selectMaps (1: string keyspace, 2: string table, 3: i32 start, 4: i32 count, 5: i32 locality),
	
	i64 totalMemory (),
	i64 freeMemory (),
	
	bool updateTableTypeCache(1: string action, 2: string table, 3: string tableType)
}
