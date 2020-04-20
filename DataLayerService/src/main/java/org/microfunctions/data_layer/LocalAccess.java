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
package org.microfunctions.data_layer;

import java.nio.ByteBuffer;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentSkipListSet;
import java.util.concurrent.atomic.AtomicLong;

public class LocalAccess {
	
    public static final String BUCKET_TYPE_ALL = "all";
    public static final String BUCKET_TYPE_DEFAULT = "default";
    public static final String BUCKET_TYPE_COUNTERS = "counters";
    public static final String BUCKET_TYPE_SETS = "sets";
    public static final String BUCKET_TYPE_MAPS = "maps";
    public static final Set<String> ALL_BUCKET_TYPES = new HashSet<String>();
    
	private static final AbstractMap.SimpleEntry<String, ByteBuffer> NO_ROW = new AbstractMap.SimpleEntry<String, ByteBuffer>(new String(), ByteBuffer.allocate(0));
	private static final AbstractMap.SimpleEntry<String, Long> NO_COUNTER = new AbstractMap.SimpleEntry<String, Long>(new String(), 0L);
	private static final AbstractMap.SimpleEntry<String, Set<String>> NO_SET = new AbstractMap.SimpleEntry<String, Set<String>>(new String(), new HashSet<String>(0));
	private static final AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> NO_MAP = new AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>>(new String(), new HashMap<String, ByteBuffer>(0));
	private static final List<AbstractMap.SimpleEntry<String, String>> NO_TABLES = new ArrayList<AbstractMap.SimpleEntry<String, String>>(0);
	private static final List<AbstractMap.SimpleEntry<String, Integer>> NO_KEYSPACES = new ArrayList<AbstractMap.SimpleEntry<String, Integer>>(0);
	private static final List<String> NO_KEYS = new ArrayList<String>(0);
	
	private ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> local = new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>>();
	private ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>>> localCounters = new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>>>();
	private ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>>> localSets = new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>>>();
	private ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>>> localMaps = new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>>>();
	
	public LocalAccess () {
		ALL_BUCKET_TYPES.add(BUCKET_TYPE_ALL);
		ALL_BUCKET_TYPES.add(BUCKET_TYPE_DEFAULT);
		ALL_BUCKET_TYPES.add(BUCKET_TYPE_COUNTERS);
		ALL_BUCKET_TYPES.add(BUCKET_TYPE_SETS);
		ALL_BUCKET_TYPES.add(BUCKET_TYPE_MAPS);
	}
	
	private boolean detectInvalidName (String str) {
		if (str.contains(" ") || str.contains(".") || str.contains(";")) {	// don't change!
			return true;
		}
		
		return false;
	}
	
	public boolean createKeyspace (String keyspace) {
		if (this.detectInvalidName(keyspace)) {
			return false;
		}
		
		local.putIfAbsent(keyspace, new ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>());
		localCounters.putIfAbsent(keyspace, new ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>>());
		localSets.putIfAbsent(keyspace, new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>>());
		localMaps.putIfAbsent(keyspace, new ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>>());
		return true;
	}
	
	public boolean dropKeyspace (String keyspace) {
		if (this.detectInvalidName(keyspace)) {
			return false;
		}
		
		local.remove(keyspace);
		localCounters.remove(keyspace);
		localSets.remove(keyspace);
		localMaps.remove(keyspace);
		return true;
	}
	
	public int getReplicationFactor (String keyspace) {
		if (this.detectInvalidName(keyspace)) {
			return 0;
		}
		
		if (local.containsKey(keyspace)) {
			return 1;
		}
		return 0;
	}

	public List<AbstractMap.SimpleEntry<String, Integer>> listKeyspaces (int start, int count) {
        if (start < 0 || count < 1) {
            return NO_KEYSPACES;
        }
        
        List<AbstractMap.SimpleEntry<String, Integer>> keyspaces = new ArrayList<AbstractMap.SimpleEntry<String, Integer>>();
        
        List<String> names = new ArrayList<String>(local.keySet());
        Collections.sort(names);
        for (String name: names) {
            keyspaces.add(new AbstractMap.SimpleEntry<String, Integer>(name, 1));
        }
        
        int size = keyspaces.size();
        if (start >= size) {
            return NO_KEYSPACES;
        }
        int end = (start + count > start && start + count <= size)? (start + count): size;
        
        return keyspaces.subList(start, end);
    }
    
	public List<AbstractMap.SimpleEntry<String, String>> listTables (String keyspace, String tableType, int start, int count) {
		if (this.detectInvalidName(keyspace) || ! ALL_BUCKET_TYPES.contains(tableType) || start < 0 || count < 1) {
			return NO_TABLES;
		}
		
		List<AbstractMap.SimpleEntry<String, String>> tables = new ArrayList<AbstractMap.SimpleEntry<String, String>>();

		if (tableType.compareTo(BUCKET_TYPE_ALL) == 0 || tableType.compareTo(BUCKET_TYPE_DEFAULT) == 0) {
			ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
			if (localKeyspace != null) {
				List<String> names = new ArrayList<String>(localKeyspace.keySet());
				Collections.sort(names);
				
				for (String name: names) {
					tables.add(new AbstractMap.SimpleEntry<String, String>(name, BUCKET_TYPE_DEFAULT));
				}
			}
		}
		
		if (tableType.compareTo(BUCKET_TYPE_ALL) == 0 || tableType.compareTo(BUCKET_TYPE_COUNTERS) == 0) {
			ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
			if (localKeyspace != null) {
				List<String> names = new ArrayList<String>(localKeyspace.keySet());
				Collections.sort(names);
				
				for (String name: names) {
					tables.add(new AbstractMap.SimpleEntry<String, String>(name, BUCKET_TYPE_COUNTERS));
				}
			}
		}

		if (tableType.compareTo(BUCKET_TYPE_ALL) == 0 || tableType.compareTo(BUCKET_TYPE_SETS) == 0) {
			ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
			if (localKeyspace != null) {
				List<String> names = new ArrayList<String>(localKeyspace.keySet());
				Collections.sort(names);
				
				for (String name: names) {
					tables.add(new AbstractMap.SimpleEntry<String, String>(name, BUCKET_TYPE_SETS));
				}
			}
		}

		if (tableType.compareTo(BUCKET_TYPE_ALL) == 0 || tableType.compareTo(BUCKET_TYPE_MAPS) == 0) {
			ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
			if (localKeyspace != null) {
				List<String> names = new ArrayList<String>(localKeyspace.keySet());
				Collections.sort(names);
				
				for (String name: names) {
					tables.add(new AbstractMap.SimpleEntry<String, String>(name, BUCKET_TYPE_MAPS));
				}
			}
		}
		
		int size = tables.size();
		if (start >= size) {
			return NO_TABLES;
		}
		int end = (start + count > start && start + count <= size)? (start + count): size;
		
		return tables.subList(start, end);
	}
	
	public boolean createTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.putIfAbsent(table, new ConcurrentHashMap<String, ByteBuffer>());
		return true;
	}
	
	public boolean createCounterTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.putIfAbsent(table, new ConcurrentHashMap<String, AtomicLong>());
		return true;
	}
	
	public boolean createSetTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.putIfAbsent(table, new ConcurrentHashMap<String, ConcurrentSkipListSet<String>>());
		return true;
	}
	
	public boolean createMapTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.putIfAbsent(table, new ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>());
		return true;
	}
	
	public boolean dropTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.remove(table);
		return true;
	}
	
	public boolean dropCounterTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.remove(table);
		return true;
	}
	
	public boolean dropSetTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.remove(table);
		return true;
	}
	
	public boolean dropMapTable (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		localKeyspace.remove(table);
		return true;
	}
	
	public boolean insertRow (String keyspace, String table, String key, ByteBuffer value) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.put(key, value);
		return true;
	}
	
	public boolean createCounter (String keyspace, String table, String counterName, long initialValue) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, AtomicLong> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.put(counterName, new AtomicLong(initialValue));
		return true;
	}
	
	public boolean createSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.putIfAbsent(setName, new ConcurrentSkipListSet<String>());
		return true;
	}
	
	public boolean createMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.putIfAbsent(mapName, new ConcurrentHashMap<String, ByteBuffer>());
		return true;
	}
	
	public boolean addItemToSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return false;
		}
		
		localResult.add(setItem);
		return true;
	}
	
	public boolean putEntryToMap (String keyspace, String table, String mapName, String entryKey, ByteBuffer entryValue) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return false;
		}
		
		localResult.put(entryKey, entryValue);
		return true;
	}
	
	public AbstractMap.SimpleEntry<String, ByteBuffer> getEntryFromMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_ROW;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return NO_ROW;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_ROW;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return NO_ROW;
		}
		
		ByteBuffer entryValue = localResult.get(entryKey);
		if (entryValue == null) {
			return NO_ROW;
		}
		
		return new AbstractMap.SimpleEntry<String, ByteBuffer>(entryKey, entryValue);
	}
	
	public boolean removeItemFromSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return false;
		}
		
		localResult.remove(setItem);
		return true;
	}
	
	public boolean removeEntryFromMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return false;
		}
		
		localResult.remove(entryKey);
		return true;
	}
	
	public boolean containsKeyInMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return false;
		}
		
		return localResult.containsKey(entryKey);
	}
	
	public boolean clearMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return false;
		}
		
		localResult.clear();
		return true;
	}
	
	public int getSizeOfMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return 0;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return 0;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return 0;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return 0;
		}
		
		return localResult.size();
	}
	
	public boolean containsItemInSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return false;
		}
		
		return localResult.contains(setItem);
	}
	
	public boolean clearSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return false;
		}
		
		localResult.clear();
		return true;
	}
	
	public int getSizeOfSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return 0;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return 0;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return 0;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return 0;
		}
		
		return localResult.size();
	}
	
	public AbstractMap.SimpleEntry<String, ByteBuffer> selectRow (String keyspace, String table, String key) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_ROW;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return NO_ROW;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_ROW;
		}
		
		ByteBuffer localResult = localTable.get(key);
		if (localResult == null) {
			return NO_ROW;
		}
		
		return new AbstractMap.SimpleEntry<String, ByteBuffer>(key, localResult);
	}
	
	public AbstractMap.SimpleEntry<String, Long> getCounter (String keyspace, String table, String counterName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_COUNTER;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return NO_COUNTER;
		}
		
		ConcurrentHashMap<String, AtomicLong> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_COUNTER;
		}
		
		AtomicLong localResult = localTable.get(counterName);
		if (localResult == null) {
			return NO_COUNTER;
		}
		
		return new AbstractMap.SimpleEntry<String, Long>(counterName, localResult.get());
	}
	
	public AbstractMap.SimpleEntry<String, Set<String>> retrieveSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_SET;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return NO_SET;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_SET;
		}
		
		ConcurrentSkipListSet<String> localResult = localTable.get(setName);
		if (localResult == null) {
			return NO_SET;
		}
		
		return new AbstractMap.SimpleEntry<String, Set<String>>(setName, localResult);
	}
	
	public AbstractMap.SimpleEntry<String, Set<String>> retrieveKeysetFromMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_SET;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return NO_SET;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_SET;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return NO_SET;
		}
		
		return new AbstractMap.SimpleEntry<String, Set<String>>(mapName, localResult.keySet());
	}
	
	public AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> retrieveAllEntriesFromMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_MAP;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return NO_MAP;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_MAP;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localResult = localTable.get(mapName);
		if (localResult == null) {
			return NO_MAP;
		}
		
		return new AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>>(mapName, localResult);
	}
	
	public boolean updateRow (String keyspace, String table, String key, ByteBuffer value) {
		return this.insertRow(keyspace, table, key, value);
	}
	
	public AbstractMap.SimpleEntry<String, Long> incrementCounter (String keyspace, String table, String counterName, long increment) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return NO_COUNTER;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return NO_COUNTER;
		}
		
		ConcurrentHashMap<String, AtomicLong> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_COUNTER;
		}
		
		AtomicLong localResult = localTable.get(counterName);
		if (localResult == null) {
			return NO_COUNTER;
		}

		long newResult = localResult.addAndGet(increment);
		return new AbstractMap.SimpleEntry<String, Long>(counterName, newResult);
	}
	
	public AbstractMap.SimpleEntry<String, Long> decrementCounter (String keyspace, String table, String counterName, long decrement) {
		return this.incrementCounter(keyspace, table, counterName, -decrement);
	}
	
	public boolean deleteRow (String keyspace, String table, String key) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.remove(key);
		return true;
	}
	
	public boolean deleteCounter (String keyspace, String table, String counterName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, AtomicLong> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.remove(counterName);
		return true;
	}
	
	public boolean deleteSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.remove(setName);
		return true;
	}
	
	public boolean deleteMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return false;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return false;
		}
		
		localTable.remove(mapName);
		return true;
	}
	
	public List<String> selectKeys(String keyspace, String table, int start, int count) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table) || start < 0 || count < 1) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localKeyspace = local.get(keyspace);
		if (localKeyspace == null) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ByteBuffer> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_KEYS;
		}
		
		List<String> keys = new ArrayList<String>(localTable.keySet());
		
		int size = keys.size();
		if (start >= size) {
			return NO_KEYS;
		}
		int end = (start + count > start && start + count <= size)? (start + count): size;
		
		Collections.sort(keys);
		return keys.subList(start, end);
	}
	
	public List<String> selectCounters (String keyspace, String table, int start, int count) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table) || start < 0 || count < 1) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, AtomicLong>> localKeyspace = localCounters.get(keyspace);
		if (localKeyspace == null) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, AtomicLong> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_KEYS;
		}
		
		List<String> keys = new ArrayList<String>(localTable.keySet());
		
		int size = keys.size();
		if (start >= size) {
			return NO_KEYS;
		}
		int end = (start + count > start && start + count <= size)? (start + count): size;
		
		Collections.sort(keys);
		return keys.subList(start, end);
	}
	
	public List<String> selectSets (String keyspace, String table, int start, int count) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table) || start < 0 || count < 1) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentSkipListSet<String>>> localKeyspace = localSets.get(keyspace);
		if (localKeyspace == null) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentSkipListSet<String>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_KEYS;
		}
		
		List<String> keys = new ArrayList<String>(localTable.keySet());
		
		int size = keys.size();
		if (start >= size) {
			return NO_KEYS;
		}
		int end = (start + count > start && start + count <= size)? (start + count): size;
		
		Collections.sort(keys);
		return keys.subList(start, end);
	}
	
	public List<String> selectMaps (String keyspace, String table, int start, int count) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table) || start < 0 || count < 1) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>>> localKeyspace = localMaps.get(keyspace);
		if (localKeyspace == null) {
			return NO_KEYS;
		}
		
		ConcurrentHashMap<String, ConcurrentHashMap<String, ByteBuffer>> localTable = localKeyspace.get(table);
		if (localTable == null) {
			return NO_KEYS;
		}
		
		List<String> keys = new ArrayList<String>(localTable.keySet());
		
		int size = keys.size();
		if (start >= size) {
			return NO_KEYS;
		}
		int end = (start + count > start && start + count <= size)? (start + count): size;
		
		Collections.sort(keys);
		return keys.subList(start, end);
	}
}
