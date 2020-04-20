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
package org.microfunctions.data_layer.client;

import java.nio.ByteBuffer;
import java.util.List;

import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.protocol.TProtocol;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TSocket;
import org.apache.thrift.transport.TTransport;

import org.microfunctions.data_layer.DataLayerService;
import org.microfunctions.data_layer.KeyCounterPair;
import org.microfunctions.data_layer.KeyIntPair;
import org.microfunctions.data_layer.KeyMapPair;
import org.microfunctions.data_layer.KeySetPair;
import org.microfunctions.data_layer.KeyValuePair;
import org.microfunctions.data_layer.Metadata;
import org.microfunctions.data_layer.StringPair;

public class JavaClient {
	
	private static void displayRow (KeyValuePair row) {
		System.out.print(row.getKey() + " -->");
		for (byte b: row.getValue()) {
			System.out.print(" " + b);
		}
		System.out.println();
	}
	
	private static void displayKeyspace (KeyIntPair pair) {
	    System.out.println(pair.getKey() + " --> " + pair.getNumber());
	}

	private static void displayCounter (KeyCounterPair counter) {
		System.out.println(counter.getKey() + " --> " + counter.getCounter());
	}
	
	private static void displaySet (KeySetPair set) {
		System.out.println(set.getKey() + " --> " + set.getItems());
	}
	
	private static void displayMap (KeyMapPair map) {
		System.out.println(map.getKey() + " --> " + map.getEntries());
	}
	
	private static void displayStringPair (StringPair pair) {
		System.out.println(pair.getKey() + " --> " + pair.getValue());
	}

	public static void main(String[] args) {
		String serverHost = "127.0.0.1";
		int serverPort = 4998;
		int connectionTimeout = 0;	// 0 means no timeout (i.e., long-lived).  Optional, measured in ms.  If not set, then the default value is no timeout.
		int maxMessageLength = Integer.MAX_VALUE;	// Optional, measured in bytes.  If not set, then the default value is 16384000 bytes.
		
		TTransport transport = new TFramedTransport(new TSocket(serverHost, serverPort, connectionTimeout), maxMessageLength);
		TProtocol protocol = new TCompactProtocol(transport);
		DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
		
		try {
			transport.open();
			
			/*======== Below is how to create keyspace ========*/
			
			String keyspace = "keyspace";
			int locality = 1;	// Indicate where to store the data.  0 means locally, 1 means remotely (Riak sync), and -1 means remotely (Riak async).

			Metadata metadata = new Metadata();
			metadata.setReplicationFactor(1);
			metadata.setTableType("default");
			
	            boolean s1 = datalayer.createKeyspace(keyspace, metadata, locality);
	            List<KeyIntPair> keyspaces = datalayer.listKeyspaces(0, Integer.MAX_VALUE, locality);
	            for (KeyIntPair k: keyspaces) {
	                displayKeyspace(k);
	            }
	            
	            /*======== Below is how to get replication factor of a keyspace ========*/
	            
	            int replicas = datalayer.getReplicationFactor(keyspace, locality);
	            System.out.println(replicas);
	            
	            /*======== Below is how to operate generic key-value table ========*/
	            
	            String table = "table";
	            String key1 = "key1";
	            String key2 = "key2";
	            byte[] value1 = new byte[]{1, 2, 3};
	            byte[] value2 = new byte[]{11, 22, 33};
	            byte[] value3 = new byte[] {};
	            
	            boolean s2 = datalayer.createTable(keyspace, table, metadata, locality);
	            
	            boolean s3 = datalayer.insertRow(keyspace, table, new KeyValuePair(key1, ByteBuffer.wrap(value1)), locality);
	            boolean s4 = datalayer.insertRow(keyspace, table, new KeyValuePair(key2, ByteBuffer.wrap(value2)), locality);
	            boolean s4_empty = datalayer.updateRow(keyspace, table, new KeyValuePair(key2, ByteBuffer.wrap(value3)), locality);
	            System.out.println("s4_empty: " + s4_empty + " " + locality);
	            KeyValuePair row_empty = datalayer.selectRow(keyspace, table, key2, locality);
	            JavaClient.displayRow(row_empty);

	            KeyValuePair row1 = datalayer.selectRow(keyspace, table, key1, locality);
	            JavaClient.displayRow(row1);
	            
	            boolean s5 = datalayer.updateRow(keyspace, table, new KeyValuePair(key1, ByteBuffer.wrap(value2)), locality);
	            
	            KeyValuePair row2 = datalayer.selectRow(keyspace, table, key1, locality);
	            JavaClient.displayRow(row2);
	            
	            List<String> keys = datalayer.selectKeys(keyspace, table, 0, Integer.MAX_VALUE, locality);
	            System.out.println(keys);
	            
	            boolean s6 = datalayer.deleteRow(keyspace, table, key1, locality);
	            
	            boolean s7 = datalayer.dropTable(keyspace, table, locality);
	            
	            /*======== Below is how to operate "counter" table ========*/

	            String counter_table = "counter_table";
	            String counter1 = "counter1";
	            String counter2 = "counter2";

	            Metadata metadata1 = new Metadata().setTableType("counters");
	            boolean s8 = datalayer.createCounterTable(keyspace, counter_table, metadata1, locality);
	            
	            boolean s9 = datalayer.createCounter(keyspace, counter_table, counter1, 100, locality);
	            boolean s10 = datalayer.createCounter(keyspace, counter_table, counter2, 200, locality);
	            
	            KeyCounterPair c1 = datalayer.getCounter(keyspace, counter_table, counter1, locality);
	            JavaClient.displayCounter(c1);
	            
	            KeyCounterPair c2 = datalayer.incrementCounter(keyspace, counter_table, counter1, 10, locality);
	            JavaClient.displayCounter(c2);
	            
	            KeyCounterPair c3 = datalayer.decrementCounter(keyspace, counter_table, counter1, 20, locality);
	            JavaClient.displayCounter(c3);
	            
	            List<String> counters = datalayer.selectCounters(keyspace, counter_table, 0, Integer.MAX_VALUE, locality);
	            System.out.println(counters);
	            
	            boolean s11 = datalayer.deleteCounter(keyspace, counter_table, counter2, locality);
	            
	            boolean s12 = datalayer.dropCounterTable(keyspace, counter_table, locality);
	            
	            /*======== Below is how to operate "set" table ========*/
	            
	            String set_table = "set_table";
	            String setName1 = "set1";
	            String setName2 = "set2";
	            String setItem1 = "item1";
	            String setItem2 = "item2";
	            
	            boolean s13 = datalayer.createSetTable(keyspace, set_table, locality);
	            
	            boolean s14 = datalayer.createSet(keyspace, set_table, setName1, locality);
	            boolean s15 = datalayer.addItemToSet(keyspace, set_table, setName1, setItem1, locality);
	            boolean s16 = datalayer.addItemToSet(keyspace, set_table, setName1, setItem2, locality);
	            
	            boolean s17 = datalayer.createSet(keyspace, set_table, setName2, locality);
	            boolean s18 = datalayer.addItemToSet(keyspace, set_table, setName2, setItem2, locality);
	            
	            KeySetPair ksp1 = datalayer.retrieveSet(keyspace, set_table, setName1, locality);
	            JavaClient.displaySet(ksp1);
	            
	            boolean s19 = datalayer.removeItemFromSet(keyspace, set_table, setName1, setItem2, locality);
	            
	            KeySetPair ksp2 = datalayer.retrieveSet(keyspace, set_table, setName1, locality);
	            JavaClient.displaySet(ksp2);
	            
	            boolean s20 = datalayer.containsItemInSet(keyspace, set_table, setName1, setItem1, locality);
	            System.out.println(setName1 + " contains " + setItem1 + ": " + s20);
	            
	            int setSize = datalayer.getSizeOfSet(keyspace, set_table, setName1, locality);
	            System.out.println(setName1 + " is of size " + setSize);
	            
	            List<String> sets = datalayer.selectSets(keyspace, set_table, 0, Integer.MAX_VALUE, locality);
	            System.out.println(sets);
	            
	            boolean s211 = datalayer.clearSet(keyspace, set_table, setName2, locality);
	            
	            boolean s21 = datalayer.deleteSet(keyspace, set_table, setName1, locality);
	            
	            boolean s22 = datalayer.dropSetTable(keyspace, set_table, locality);
	            
	            /*======== Below is how to operate "map" table ========*/
	            
	            String map_table = "map_table";
	            String mapName1 = "map1";
	            String mapName2 = "map2";
	            String entryKey1 = "entry1";
	            String entryKey2 = "entry2";
	            byte[] entryValue1 = new byte[]{1, 2, 3};
	            byte[] entryValue2 = new byte[]{11, 22, 33};
	            byte[] entryValue3 = new byte[] {};
	            
	            boolean s23 = datalayer.createMapTable(keyspace, map_table, locality);
	            
	            boolean s24 = datalayer.createMap(keyspace, map_table, mapName1, locality);
	            boolean s25 = datalayer.putEntryToMap(keyspace, map_table, mapName1, new KeyValuePair(entryKey1, ByteBuffer.wrap(entryValue1)), locality);
	            boolean s26 = datalayer.putEntryToMap(keyspace, map_table, mapName1, new KeyValuePair(entryKey2, ByteBuffer.wrap(entryValue2)), locality);
	            boolean s26_empty = datalayer.putEntryToMap(keyspace, map_table, mapName1, new KeyValuePair(entryKey2, ByteBuffer.wrap(entryValue3)), locality);
	            System.out.println("s26_empty: " + s26_empty);
	            
	            boolean s27 = datalayer.createMap(keyspace, map_table, mapName2, locality);
	            boolean s28 = datalayer.putEntryToMap(keyspace, map_table, mapName2, new KeyValuePair(entryKey2, ByteBuffer.wrap(entryValue2)), locality);
	            
	            KeySetPair ksp3 = datalayer.retrieveKeysetFromMap(keyspace, map_table, mapName1, locality);
	            JavaClient.displaySet(ksp3);
	            
	            KeyMapPair kmp = datalayer.retrieveAllEntriesFromMap(keyspace, map_table, mapName1, locality);
	            JavaClient.displayMap(kmp);
	            
	            KeyValuePair kvp1 = datalayer.getEntryFromMap(keyspace, map_table, mapName1, entryKey1, locality);
	            JavaClient.displayRow(kvp1);
	            
	            boolean s29 = datalayer.removeEntryFromMap(keyspace, map_table, mapName1, entryKey2, locality);
	            
	            KeySetPair ksp4 = datalayer.retrieveKeysetFromMap(keyspace, map_table, mapName1, locality);
	            JavaClient.displaySet(ksp4);
	            
	            boolean s30 = datalayer.containsKeyInMap(keyspace, map_table, mapName1, entryKey1, locality);
	            System.out.println(mapName1 + " contains the key of " + entryKey1 + ": " + s30);
	            
	            int mapSize = datalayer.getSizeOfMap(keyspace, map_table, mapName1, locality);
	            System.out.println(mapName1 + " is of size " + mapSize);
	            
	            List<String> maps = datalayer.selectMaps(keyspace, map_table, 0, Integer.MAX_VALUE, locality);
	            System.out.println(maps);
	            
	            boolean s311 = datalayer.clearMap(keyspace, map_table, mapName1, locality);
	            
	            boolean s31 = datalayer.deleteMap(keyspace, map_table, mapName1, locality);
	            
	            boolean s32 = datalayer.dropMapTable(keyspace, map_table, locality);
	            
	            /*======== Below is how to get the table information of a keyspace ========*/
	            boolean s33 = datalayer.createTable(keyspace, "default1", metadata, locality);
	            boolean s34 = datalayer.createCounterTable(keyspace, "counter1", metadata1, locality);
	            boolean s35 = datalayer.createSetTable(keyspace, "set1", locality);
	            boolean s36 = datalayer.createMapTable(keyspace, "map1", locality);
	            boolean s37 = datalayer.createMapTable(keyspace, "map2", locality);
	            
	            // tableType indicates what type of tables is of interest
	            // "all" means getting all tables
	            // "default" means getting only generic key-value tables
	            // "counters" means getting only counter tables
	            // "sets" means getting only set tables
	            // "maps" means getting only map tables
	            String tableType = "all";
	            List<StringPair> tables = datalayer.listTables(keyspace, tableType, 0, Integer.MAX_VALUE, locality);
	            
	            for (StringPair t: tables) {
	                JavaClient.displayStringPair(t);
	            }
	            
	            boolean s38 = datalayer.dropTable(keyspace, "default1", locality);
	            boolean s39 = datalayer.dropCounterTable(keyspace, "counter1", locality);
	            boolean s40 = datalayer.dropSetTable(keyspace, "set1", locality);
	            boolean s41 = datalayer.dropMapTable(keyspace, "map1", locality);
	            boolean s42 = datalayer.dropMapTable(keyspace, "map2", locality);
	            
	            /*======== Below is how to delete keyspace ========*/
	            
	            boolean s130 = datalayer.dropKeyspace(keyspace, locality);

	            /*======== Below is how to get memory usage ========*/
	            
	            long totalMemory = datalayer.totalMemory(); // measured in bytes
	            System.out.println("Total memory: " + totalMemory + " bytes");
	            
	            long freeMemory = datalayer.freeMemory();   // measured in bytes
	            System.out.println("Free memory: " + freeMemory + " bytes");

			
		} catch (Exception e) {
			e.printStackTrace();
		} finally {
			if (transport != null) {
				transport.close();
			}
		}
	}
}
