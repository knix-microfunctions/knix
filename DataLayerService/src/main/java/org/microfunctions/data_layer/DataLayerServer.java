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

import java.io.FileInputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.thrift.TException;
import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.server.TServer;
import org.apache.thrift.server.TThreadedSelectorServer;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TNonblockingServerSocket;
import org.apache.thrift.transport.TNonblockingServerTransport;
import org.apache.thrift.transport.TTransportException;
import org.microfunctions.data_layer.DataLayerService.Iface;

public class DataLayerServer implements Iface, Callable<Object> {
	
	private static final Logger LOGGER = LogManager.getLogger(DataLayerServer.class);

	private static final int LOCAL_DATALAYER = Commons.LOCAL_DATALAYER;
	private static final int RIAK_DATALAYER = Commons.RIAK_DATALAYER;
	private static final int WRITE_RIAK_ASYNC_LOCAL_SYNC = Commons.WRITE_RIAK_ASYNC_LOCAL_SYNC;
	private static final int READ_RIAK_ASYNC = Commons.READ_RIAK_ASYNC;
	private static final int READ_LOCAL_THEN_RIAK = Commons.READ_LOCAL_THEN_RIAK;
	
	private static final AbstractMap.SimpleEntry<String, ByteBuffer> NO_ROW = new AbstractMap.SimpleEntry<String, ByteBuffer>(new String(), ByteBuffer.allocate(0));
	private static final AbstractMap.SimpleEntry<String, Long> NO_COUNTER = new AbstractMap.SimpleEntry<String, Long>(new String(), 0L);
	private static final AbstractMap.SimpleEntry<String, Set<String>> NO_SET = new AbstractMap.SimpleEntry<String, Set<String>>(new String(), new HashSet<String>(0));
	private static final AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> NO_MAP = new AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>>(new String(), new HashMap<String, ByteBuffer>(0));
	private static final List<AbstractMap.SimpleEntry<String, String>> NO_TABLES = new ArrayList<AbstractMap.SimpleEntry<String, String>>(0);
	private static final List<AbstractMap.SimpleEntry<String, Integer>> NO_KEYSPACES = new ArrayList<AbstractMap.SimpleEntry<String, Integer>>(0);
	private static final List<String> NO_KEYS = new ArrayList<String>(0);
	
	public static final int DEFAULT_SELECTOR_THREADS = 50; //Math.max(2, 2 * Runtime.getRuntime().availableProcessors());
    public static final int DEFAULT_WORKER_THREADS = 100;  //Math.max(4, 4 * Runtime.getRuntime().availableProcessors());
	public static final int DEFAULT_CLIENT_TIMEOUT = 0;
	public static final int DEFAULT_MAX_FRAME_LENGTH = Integer.MAX_VALUE;
	
	private TServer server = null;
	private LocalAccess dbLocal = null;
	private RiakAccess dbRiak = null;

	public static final int THREAD_CONCURRENCY = 2 * Runtime.getRuntime().availableProcessors();
	private List<ExecutorService> executors = null;
	
	private int function = 0;
	private List<Object> parameters = null;
	private boolean isMainDataLayerServer = false;
	
	private static final int CREATE_KEYSPACE = 1;
	private static final int DROP_KEYSPACE = 2;
	private static final int GET_REPLICATION_FACTOR = 3;
	private static final int LIST_KEYSPACES = 4;
	private static final int LIST_TABLES = 5;
	private static final int CREATE_TABLE = 6;
	private static final int CREATE_COUNTER_TABLE = 7;
	private static final int CREATE_SET_TABLE = 8;
	private static final int CREATE_MAP_TABLE = 9;
	private static final int DROP_TABLE = 10;
	private static final int DROP_COUNTER_TABLE = 11;
	private static final int DROP_SET_TABLE = 12;
	private static final int DROP_MAP_TABLE = 13;
	private static final int INSERT_ROW = 14;
	private static final int SELECT_ROW = 15;
	private static final int UPDATE_ROW = 16;
	private static final int DELETE_ROW = 17;
	private static final int SELECT_KEYS = 18;
	private static final int CREATE_COUNTER = 19;
	private static final int GET_COUNTER = 20;
	private static final int INCREMENT_COUNTER = 21;
	private static final int DECREMENT_COUNTER = 22;
	private static final int DELETE_COUNTER = 23;
	private static final int SELECT_COUNTERS = 24;
	private static final int CREATE_SET = 25;
	private static final int RETRIEVE_SET = 26;
	private static final int ADD_ITEM_TO_SET = 27;
	private static final int REMOVE_ITEM_FROM_SET = 28;
	private static final int CONTAINS_ITEM_IN_SET = 29;
	private static final int CLEAR_SET = 30;
	private static final int GET_SIZE_OF_SET = 31;
	private static final int DELETE_SET = 32;
	private static final int SELECT_SETS = 33;
	private static final int CREATE_MAP = 34;
	private static final int RETRIEVE_KEYSET_FROM_MAP = 35;
	private static final int RETRIEVE_ALL_ENTRIES_FROM_MAP = 36;
	private static final int PUT_ENTRY_TO_MAP = 37;
	private static final int GET_ENTRY_FROM_MAP = 38;
	private static final int REMOVE_ENTRY_FROM_MAP = 39;
	private static final int CONTAINS_KEY_IN_MAP = 40;
	private static final int CLEAR_MAP = 41;
	private static final int GET_SIZE_OF_MAP = 42;
	private static final int DELETE_MAP = 43;
	private static final int SELECT_MAPS = 44;
	
	public DataLayerServer(Map<String,Integer> riakNodes, Map<String,Integer> allDatalayerNodes) {
        this.isMainDataLayerServer = true;
        dbLocal = new LocalAccess();
        dbRiak = new RiakAccess(allDatalayerNodes);
        dbRiak.connect(riakNodes);
		
		executors = new ArrayList<ExecutorService>(THREAD_CONCURRENCY);
		for (int i = 0; i < THREAD_CONCURRENCY; ++i) {
			executors.add(Executors.newSingleThreadExecutor());
		}
	}
	
	private DataLayerServer(RiakAccess dbRiak, int function, List<Object> parameters) {
        this.isMainDataLayerServer = false;
        this.dbRiak = dbRiak;
        this.function = function;
        this.parameters = parameters;
	}

	@Override
	public Object call() throws Exception {
		String keyspace = null;
		Metadata metadata = null;
		int locality = 0;
		String tableType = null;
		int start = 0;
		int count = 0;
		String table = null;
		KeyValuePair keyValuePair = null;
		String key = null;
		String counterName = null;
		long initialValue = 0;
		long increment = 0;
		long decrement = 0;
		String setName = null;
		String setItem = null;
		String mapName = null;
		String entryKey = null;
		
		switch (function) {
		case CREATE_KEYSPACE:
			keyspace = parameters.get(0).toString();
			metadata = (Metadata)(parameters.get(1));
			locality = (Integer)(parameters.get(2));
			return (Boolean)createKeyspace(keyspace, metadata, locality);
		case DROP_KEYSPACE:
			keyspace = parameters.get(0).toString();
			locality = (Integer)(parameters.get(1));
			return (Boolean)dropKeyspace(keyspace, locality);
		case GET_REPLICATION_FACTOR:
			keyspace = parameters.get(0).toString();
			locality = (Integer)(parameters.get(1));
			return (Integer)getReplicationFactor(keyspace, locality);
		case LIST_KEYSPACES:
			start = (Integer)(parameters.get(0));
			count = (Integer)(parameters.get(1));
			locality = (Integer)(parameters.get(2));
			return listKeyspaces(start, count, locality);			
		case LIST_TABLES:
			keyspace = parameters.get(0).toString();
			tableType = parameters.get(1).toString();
			start = (Integer)(parameters.get(2));
			count = (Integer)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return listTables(keyspace, tableType, start, count, locality);
		case CREATE_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			metadata = (Metadata)(parameters.get(2));
			locality = (Integer)(parameters.get(3));
			return (Boolean)createTable(keyspace, table, metadata, locality);
		case CREATE_COUNTER_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			metadata = (Metadata)(parameters.get(2));
			locality = (Integer)(parameters.get(3));
			return (Boolean)createCounterTable(keyspace, table, metadata, locality);
		case CREATE_SET_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)createSetTable(keyspace, table, locality);
		case CREATE_MAP_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)createMapTable(keyspace, table, locality);
		case DROP_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)dropTable(keyspace, table, locality);
		case DROP_COUNTER_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)dropCounterTable(keyspace, table, locality);
		case DROP_SET_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)dropSetTable(keyspace, table, locality);
		case DROP_MAP_TABLE:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			locality = (Integer)(parameters.get(2));
			return (Boolean)dropMapTable(keyspace, table, locality);
		case INSERT_ROW:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			keyValuePair = (KeyValuePair)(parameters.get(2));
			locality = (Integer)(parameters.get(3));
			return (Boolean)insertRow(keyspace, table, keyValuePair, locality);
		case SELECT_ROW:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			key = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return selectRow(keyspace, table, key, locality);
		case UPDATE_ROW:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			keyValuePair = (KeyValuePair)(parameters.get(2));
			locality = (Integer)(parameters.get(3));
			return (Boolean)updateRow(keyspace, table, keyValuePair, locality);
		case DELETE_ROW:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			key = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)deleteRow(keyspace, table, key, locality);
		case SELECT_KEYS:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			start = (Integer)(parameters.get(2));
			count = (Integer)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return selectKeys(keyspace, table, start, count, locality);
		case CREATE_COUNTER:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			counterName = parameters.get(2).toString();
			initialValue = (Long)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return (Boolean)createCounter(keyspace, table, counterName, initialValue, locality);
		case GET_COUNTER:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			counterName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return getCounter(keyspace, table, counterName, locality);
		case INCREMENT_COUNTER:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			counterName = parameters.get(2).toString();
			increment = (Long)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return incrementCounter(keyspace, table, counterName, increment, locality);
		case DECREMENT_COUNTER:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			counterName = parameters.get(2).toString();
			decrement = (Long)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return decrementCounter(keyspace, table, counterName, decrement, locality);
		case DELETE_COUNTER:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			counterName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)deleteCounter(keyspace, table, counterName, locality);
		case SELECT_COUNTERS:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			start = (Integer)(parameters.get(2));
			count = (Integer)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return selectCounters(keyspace, table, start, count, locality);
		case CREATE_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)createSet(keyspace, table, setName, locality);
		case RETRIEVE_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return retrieveSet(keyspace, table, setName, locality);
		case ADD_ITEM_TO_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			setItem = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return (Boolean)addItemToSet(keyspace, table, setName, setItem, locality);
		case REMOVE_ITEM_FROM_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			setItem = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return (Boolean)removeItemFromSet(keyspace, table, setName, setItem, locality);
		case CONTAINS_ITEM_IN_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			setItem = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return (Boolean)containsItemInSet(keyspace, table, setName, setItem, locality);
		case CLEAR_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)clearSet(keyspace, table, setName, locality);
		case GET_SIZE_OF_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Integer)getSizeOfSet(keyspace, table, setName, locality);
		case DELETE_SET:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			setName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)deleteSet(keyspace, table, setName, locality);
		case SELECT_SETS:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			start = (Integer)(parameters.get(2));
			count = (Integer)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return selectSets(keyspace, table, start, count, locality);
		case CREATE_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)createMap(keyspace, table, mapName, locality);
		case RETRIEVE_KEYSET_FROM_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return retrieveKeysetFromMap(keyspace, table, mapName, locality);
		case RETRIEVE_ALL_ENTRIES_FROM_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return retrieveAllEntriesFromMap(keyspace, table, mapName, locality);
		case PUT_ENTRY_TO_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			keyValuePair = (KeyValuePair)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return (Boolean)putEntryToMap(keyspace, table, mapName, keyValuePair, locality);
		case GET_ENTRY_FROM_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			entryKey = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return getEntryFromMap(keyspace, table, mapName, entryKey, locality);
		case REMOVE_ENTRY_FROM_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			entryKey = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return (Boolean)removeEntryFromMap(keyspace, table, mapName, entryKey, locality);
		case CONTAINS_KEY_IN_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			entryKey = parameters.get(3).toString();
			locality = (Integer)(parameters.get(4));
			return (Boolean)containsKeyInMap(keyspace, table, mapName, entryKey, locality);
		case CLEAR_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)clearMap(keyspace, table, mapName, locality);
		case GET_SIZE_OF_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Integer)getSizeOfMap(keyspace, table, mapName, locality);
		case DELETE_MAP:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			mapName = parameters.get(2).toString();
			locality = (Integer)(parameters.get(3));
			return (Boolean)deleteMap(keyspace, table, mapName, locality);
		case SELECT_MAPS:
			keyspace = parameters.get(0).toString();
			table = parameters.get(1).toString();
			start = (Integer)(parameters.get(2));
			count = (Integer)(parameters.get(3));
			locality = (Integer)(parameters.get(4));
			return selectMaps(keyspace, table, start, count, locality);
		}
		
		return null;
	}
	
	private Future<Object> execute (String keyspace, String table, DataLayerServer server) {
		try {
			int executorId = Math.floorMod((keyspace + ";" + table).hashCode(), THREAD_CONCURRENCY);
			return executors.get(executorId).submit(server);
		} catch (Exception e) {
			LOGGER.error("execute() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Function: " + server.function + "  Parameters: " + server.parameters, e);
			return null;
		}
	}

	@Override
	public boolean createKeyspace(String keyspace, Metadata metadata, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createKeyspace(keyspace);
		case RIAK_DATALAYER:
			return dbRiak.createKeyspace(keyspace, metadata);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_KEYSPACE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(metadata);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, "", new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createKeyspace(keyspace);
		default:
			return false;
		}
	}

	@Override
	public boolean dropKeyspace(String keyspace, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.dropKeyspace(keyspace);
		case RIAK_DATALAYER:
			return dbRiak.dropKeyspace(keyspace);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DROP_KEYSPACE;
			List<Object> parameters = new ArrayList<Object>(2);
			parameters.add(keyspace);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, "", new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.dropKeyspace(keyspace);
		default:
			return false;
		}
	}

	@Override
	public int getReplicationFactor(String keyspace, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.getReplicationFactor(keyspace);
		case RIAK_DATALAYER:
			return dbRiak.getReplicationFactor(keyspace);
		case READ_RIAK_ASYNC:
			try {
				int function = GET_REPLICATION_FACTOR;
				List<Object> parameters = new ArrayList<Object>(2);
				parameters.add(keyspace);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, "", new DataLayerServer(dbRiak, function, parameters));
				return (Integer)future.get();
			} catch (Exception e) {
			    LOGGER.error("getReplicationFactor() failed.  Keyspace: " + keyspace + "  Locality: " + locality, e);
				return 0;
			}
		case READ_LOCAL_THEN_RIAK:
			int factor = dbLocal.getReplicationFactor(keyspace);
			if (factor <= 0) {
				factor = dbRiak.getReplicationFactor(keyspace);
			}
			return factor;
		default:
			return 0;
		}
	}

	@SuppressWarnings("unchecked")
    @Override
    public List<KeyIntPair> listKeyspaces(int start, int count, int locality) throws TException {
        List<AbstractMap.SimpleEntry<String, Integer>> keyspaces = NO_KEYSPACES;
        switch (locality) {
        case LOCAL_DATALAYER:
            keyspaces = dbLocal.listKeyspaces(start, count);
            break;
        case RIAK_DATALAYER:
            keyspaces = dbRiak.listKeyspaces(start, count);
            break;
        case READ_RIAK_ASYNC:
            try {
                int function = LIST_KEYSPACES;
                List<Object> parameters = new ArrayList<Object>(3);
                parameters.add((Integer)start);
                parameters.add((Integer)count);
                parameters.add((Integer)RIAK_DATALAYER);
                Future<Object> future = execute("", "", new DataLayerServer(dbRiak, function, parameters));
                return (List<KeyIntPair>)future.get();
            } catch (Exception e) {
                LOGGER.error("listKeyspaces() failed.  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
                return new ArrayList<KeyIntPair>(0);
            }
        case READ_LOCAL_THEN_RIAK:
            keyspaces = dbLocal.listKeyspaces(start, count);
            if (keyspaces.size() <= 0) {
                keyspaces = dbRiak.listKeyspaces(start, count);
            }
            break;
        }
        
        List<KeyIntPair> list = new ArrayList<KeyIntPair>(keyspaces.size());
        for (AbstractMap.SimpleEntry<String, Integer> keyspace: keyspaces) {
            list.add(new KeyIntPair(keyspace.getKey(), keyspace.getValue()));
        }
        return list;
    }

	@SuppressWarnings("unchecked")
	@Override
	public List<StringPair> listTables(String keyspace, String tableType, int start, int count, int locality) throws TException {
		List<AbstractMap.SimpleEntry<String, String>> tables = NO_TABLES;
		switch (locality) {
		case LOCAL_DATALAYER:
			tables = dbLocal.listTables(keyspace, tableType, start, count);
			break;
		case RIAK_DATALAYER:
			tables = dbRiak.listTables(keyspace, tableType, start, count);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = LIST_TABLES;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(tableType);
				parameters.add((Integer)start);
				parameters.add((Integer)count);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, "", new DataLayerServer(dbRiak, function, parameters));
				return (List<StringPair>)future.get();
			} catch (Exception e) {
			    LOGGER.error("listTables() failed.  Keyspace: " + keyspace + "  TableType: " + tableType + "  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
				return new ArrayList<StringPair>(0);
			}
		case READ_LOCAL_THEN_RIAK:
			tables = dbLocal.listTables(keyspace, tableType, start, count);
			if (tables.size() <= 0) {
				tables = dbRiak.listTables(keyspace, tableType, start, count);
			}
			break;
		}
		
		List<StringPair> list = new ArrayList<StringPair>(tables.size());
		for (AbstractMap.SimpleEntry<String, String> table: tables) {
			list.add(new StringPair(table.getKey(), table.getValue()));
		}
		return list;
	}

	@Override
    public boolean createTable(String keyspace, String table, Metadata metadata, int locality) throws TException {
        switch (locality) {
        case LOCAL_DATALAYER:
            return dbLocal.createTable(keyspace, table);
        case RIAK_DATALAYER:
            return dbRiak.createTable(keyspace, table, metadata);
        case WRITE_RIAK_ASYNC_LOCAL_SYNC:
            int function = CREATE_TABLE;
            List<Object> parameters = new ArrayList<Object>(4);
            parameters.add(keyspace);
            parameters.add(table);
            parameters.add(metadata);
            parameters.add((Integer)RIAK_DATALAYER);
            execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
            return dbLocal.createTable(keyspace, table);
        default:
            return false;
        }
    }

	@Override
	public boolean createCounterTable(String keyspace, String table, Metadata metadata, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createCounterTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.createCounterTable(keyspace, table, metadata);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_COUNTER_TABLE;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(metadata);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createCounterTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean createSetTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createSetTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.createSetTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_SET_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createSetTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean createMapTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createMapTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.createMapTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_MAP_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createMapTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean dropTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.dropTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.dropTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DROP_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.dropTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean dropCounterTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.dropCounterTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.dropCounterTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DROP_COUNTER_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.dropCounterTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean dropSetTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.dropSetTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.dropSetTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DROP_SET_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.dropSetTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean dropMapTable(String keyspace, String table, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.dropMapTable(keyspace, table);
		case RIAK_DATALAYER:
			return dbRiak.dropMapTable(keyspace, table);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DROP_MAP_TABLE;
			List<Object> parameters = new ArrayList<Object>(3);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.dropMapTable(keyspace, table);
		default:
			return false;
		}
	}

	@Override
	public boolean insertRow(String keyspace, String table, KeyValuePair keyValuePair, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.insertRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case RIAK_DATALAYER:
			return dbRiak.insertRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = INSERT_ROW;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(keyValuePair);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.insertRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		default:
			return false;
		}
	}
	
	@Override
	public KeyValuePair selectRow(String keyspace, String table, String key, int locality) throws TException {
		AbstractMap.SimpleEntry<String, ByteBuffer> row = NO_ROW;
		switch (locality) {
		case LOCAL_DATALAYER:
			row = dbLocal.selectRow(keyspace, table, key);
			break;
		case RIAK_DATALAYER:
			row = dbRiak.selectRow(keyspace, table, key);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = SELECT_ROW;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(key);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeyValuePair)future.get();
			} catch (Exception e) {
			    LOGGER.error("selectRow() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeyValuePair(NO_ROW.getKey(), NO_ROW.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			row = dbLocal.selectRow(keyspace, table, key);
			if (row.getKey().compareTo(key) != 0) {
				row = dbRiak.selectRow(keyspace, table, key);
			}
			break;
		}
		return new KeyValuePair(row.getKey(), row.getValue());
	}

	@Override
	public boolean updateRow(String keyspace, String table, KeyValuePair keyValuePair, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.updateRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case RIAK_DATALAYER:
			return dbRiak.updateRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = UPDATE_ROW;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(keyValuePair);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.updateRow(keyspace, table, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		default:
			return false;
		}
	}

	@Override
	public boolean deleteRow(String keyspace, String table, String key, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.deleteRow(keyspace, table, key);
		case RIAK_DATALAYER:
			return dbRiak.deleteRow(keyspace, table, key);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DELETE_ROW;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(key);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.deleteRow(keyspace, table, key);
		default:
			return false;
		}
	}

	@SuppressWarnings("unchecked")
	@Override
	public List<String> selectKeys(String keyspace, String table, int start, int count, int locality) throws TException {
		List<String> keys = NO_KEYS;
		switch (locality) {
		case LOCAL_DATALAYER:
			keys = dbLocal.selectKeys(keyspace, table, start, count);
			break;
		case RIAK_DATALAYER:
			keys = dbRiak.selectKeys(keyspace, table, start, count);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = SELECT_KEYS;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add((Integer)start);
				parameters.add((Integer)count);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (List<String>)future.get();
			} catch (Exception e) {
			    LOGGER.error("selectKeys() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
				return NO_KEYS;
			}
		case READ_LOCAL_THEN_RIAK:
			keys = dbLocal.selectKeys(keyspace, table, start, count);
			if (keys.size() <= 0) {
				keys = dbRiak.selectKeys(keyspace, table, start, count);
			}
			break;
		}
		return keys;
	}

	@Override
	public boolean createCounter(String keyspace, String table, String counterName, long initialValue, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createCounter(keyspace, table, counterName, initialValue);
		case RIAK_DATALAYER:
			return dbRiak.createCounter(keyspace, table, counterName, initialValue);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_COUNTER;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(counterName);
			parameters.add((Long)initialValue);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createCounter(keyspace, table, counterName, initialValue);
		default:
			return false;
		}
	}

	@Override
	public KeyCounterPair getCounter(String keyspace, String table, String counterName, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Long> counter = NO_COUNTER;
		switch (locality) {
		case LOCAL_DATALAYER:
			counter = dbLocal.getCounter(keyspace, table, counterName);
			break;
		case RIAK_DATALAYER:
			counter = dbRiak.getCounter(keyspace, table, counterName);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = GET_COUNTER;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(counterName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeyCounterPair)future.get();
			} catch (Exception e) {
			    LOGGER.error("getCounter() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeyCounterPair(NO_COUNTER.getKey(), NO_COUNTER.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			counter = dbLocal.getCounter(keyspace, table, counterName);
			if (counter.getKey().compareTo(counterName) != 0) {
				counter = dbRiak.getCounter(keyspace, table, counterName);
			}
			break;
		}
		return new KeyCounterPair(counter.getKey(), counter.getValue());
	}

	@Override
	public KeyCounterPair incrementCounter(String keyspace, String table, String counterName, long increment, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Long> counter = NO_COUNTER;
		switch (locality) {
		case LOCAL_DATALAYER:
			counter = dbLocal.incrementCounter(keyspace, table, counterName, increment);
			break;
		case RIAK_DATALAYER:
			counter = dbRiak.incrementCounter(keyspace, table, counterName, increment);
			break;
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = INCREMENT_COUNTER;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(counterName);
			parameters.add((Long)increment);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			counter = dbLocal.incrementCounter(keyspace, table, counterName, increment);
			break;
		}
		return new KeyCounterPair(counter.getKey(), counter.getValue());
	}

	@Override
	public KeyCounterPair decrementCounter(String keyspace, String table, String counterName, long decrement, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Long> counter = NO_COUNTER;
		switch (locality) {
		case LOCAL_DATALAYER:
			counter = dbLocal.decrementCounter(keyspace, table, counterName, decrement);
			break;
		case RIAK_DATALAYER:
			counter = dbRiak.decrementCounter(keyspace, table, counterName, decrement);
			break;
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DECREMENT_COUNTER;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(counterName);
			parameters.add((Long)decrement);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			counter = dbLocal.decrementCounter(keyspace, table, counterName, decrement);
			break;
		}
		return new KeyCounterPair(counter.getKey(), counter.getValue());
	}

	@Override
	public boolean deleteCounter(String keyspace, String table, String counterName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.deleteCounter(keyspace, table, counterName);
		case RIAK_DATALAYER:
			return dbRiak.deleteCounter(keyspace, table, counterName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DELETE_COUNTER;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(counterName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.deleteCounter(keyspace, table, counterName);
		default:
			return false;
		}
	}

	@SuppressWarnings("unchecked")
	@Override
	public List<String> selectCounters(String keyspace, String table, int start, int count, int locality) throws TException {
		List<String> keys = NO_KEYS;
		switch (locality) {
		case LOCAL_DATALAYER:
			keys = dbLocal.selectCounters(keyspace, table, start, count);
			break;
		case RIAK_DATALAYER:
			keys = dbRiak.selectCounters(keyspace, table, start, count);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = SELECT_COUNTERS;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add((Integer)start);
				parameters.add((Integer)count);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (List<String>)future.get();
			} catch (Exception e) {
			    LOGGER.error("selectCounters() failed.  Kepsace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
				return NO_KEYS;
			}
		case READ_LOCAL_THEN_RIAK:
			keys = dbLocal.selectCounters(keyspace, table, start, count);
			if (keys.size() <= 0) {
				keys = dbRiak.selectCounters(keyspace, table, start, count);
			}
			break;
		}
		return keys;
	}

	@Override
	public boolean createSet(String keyspace, String table, String setName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createSet(keyspace, table, setName);
		case RIAK_DATALAYER:
			return dbRiak.createSet(keyspace, table, setName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_SET;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(setName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createSet(keyspace, table, setName);
		default:
			return false;
		}
	}

	@Override
	public KeySetPair retrieveSet(String keyspace, String table, String setName, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Set<String>> set = NO_SET;
		switch (locality) {
		case LOCAL_DATALAYER:
			set = dbLocal.retrieveSet(keyspace, table, setName);
			break;
		case RIAK_DATALAYER:
			set = dbRiak.retrieveSet(keyspace, table, setName);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = RETRIEVE_SET;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(setName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeySetPair)future.get();
			} catch (Exception e) {
			    LOGGER.error("retrieveSet() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeySetPair(NO_SET.getKey(), NO_SET.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			set = dbLocal.retrieveSet(keyspace, table, setName);
			if (set.getKey().compareTo(setName) != 0) {
				set = dbRiak.retrieveSet(keyspace, table, setName);
			}
			break;
		}
		return new KeySetPair(set.getKey(), set.getValue());
	}

	@Override
	public boolean addItemToSet(String keyspace, String table, String setName, String setItem, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.addItemToSet(keyspace, table, setName, setItem);
		case RIAK_DATALAYER:
			return dbRiak.addItemToSet(keyspace, table, setName, setItem);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = ADD_ITEM_TO_SET;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(setName);
			parameters.add(setItem);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.addItemToSet(keyspace, table, setName, setItem);
		default:
			return false;
		}
	}

	@Override
	public boolean removeItemFromSet(String keyspace, String table, String setName, String setItem, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.removeItemFromSet(keyspace, table, setName, setItem);
		case RIAK_DATALAYER:
			return dbRiak.removeItemFromSet(keyspace, table, setName, setItem);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = REMOVE_ITEM_FROM_SET;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(setName);
			parameters.add(setItem);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.removeItemFromSet(keyspace, table, setName, setItem);
		default:
			return false;
		}
	}

	@Override
	public boolean containsItemInSet(String keyspace, String table, String setName, String setItem, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.containsItemInSet(keyspace, table, setName, setItem);
		case RIAK_DATALAYER:
			return dbRiak.containsItemInSet(keyspace, table, setName, setItem);
		case READ_RIAK_ASYNC:
			try {
				int function = CONTAINS_ITEM_IN_SET;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(setName);
				parameters.add(setItem);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (Boolean)future.get();
			} catch (Exception e) {
			    LOGGER.error("containsItemInSet() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return false;
			}
		case READ_LOCAL_THEN_RIAK:
			if (dbLocal.selectSets(keyspace, table, 0, Integer.MAX_VALUE).contains(setName)) {
				return dbLocal.containsItemInSet(keyspace, table, setName, setItem);
			} else {
				return dbRiak.containsItemInSet(keyspace, table, setName, setItem);
			}
		default:
			return false;
		}
	}

	@Override
	public boolean clearSet(String keyspace, String table, String setName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.clearSet(keyspace, table, setName);
		case RIAK_DATALAYER:
			return dbRiak.clearSet(keyspace, table, setName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CLEAR_SET;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(setName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.clearSet(keyspace, table, setName);
		default:
			return false;
		}
	}

	@Override
	public int getSizeOfSet(String keyspace, String table, String setName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.getSizeOfSet(keyspace, table, setName);
		case RIAK_DATALAYER:
			return dbRiak.getSizeOfSet(keyspace, table, setName);
		case READ_RIAK_ASYNC:
			try {
				int function = GET_SIZE_OF_SET;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(setName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (Integer)future.get();
			} catch (Exception e) {
			    LOGGER.error("getSizeOfSet() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return 0;
			}
		case READ_LOCAL_THEN_RIAK:
			if (dbLocal.selectSets(keyspace, table, 0, Integer.MAX_VALUE).contains(setName)) {
				return dbLocal.getSizeOfSet(keyspace, table, setName);
			} else {
				return dbRiak.getSizeOfSet(keyspace, table, setName);
			}
		default:
			return 0;
		}
	}

	@Override
	public boolean deleteSet(String keyspace, String table, String setName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.deleteSet(keyspace, table, setName);
		case RIAK_DATALAYER:
			return dbRiak.deleteSet(keyspace, table, setName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DELETE_SET;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(setName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.deleteSet(keyspace, table, setName);
		default:
			return false;
		}
	}

	@SuppressWarnings("unchecked")
	@Override
	public List<String> selectSets(String keyspace, String table, int start, int count, int locality) throws TException {
		List<String> keys = NO_KEYS;
		switch (locality) {
		case LOCAL_DATALAYER:
			keys = dbLocal.selectSets(keyspace, table, start, count);
			break;
		case RIAK_DATALAYER:
			keys = dbRiak.selectSets(keyspace, table, start, count);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = SELECT_SETS;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add((Integer)start);
				parameters.add((Integer)count);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (List<String>)future.get();
			} catch (Exception e) {
			    LOGGER.error("selectSets() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
				return NO_KEYS;
			}
		case READ_LOCAL_THEN_RIAK:
			keys = dbLocal.selectSets(keyspace, table, start, count);
			if (keys.size() <= 0) {
				keys = dbRiak.selectSets(keyspace, table, start, count);
			}
			break;
		}
		return keys;
	}

	@Override
	public boolean createMap(String keyspace, String table, String mapName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.createMap(keyspace, table, mapName);
		case RIAK_DATALAYER:
			return dbRiak.createMap(keyspace, table, mapName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CREATE_MAP;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(mapName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.createMap(keyspace, table, mapName);
		default:
			return false;
		}
	}

	@Override
	public KeySetPair retrieveKeysetFromMap(String keyspace, String table, String mapName, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Set<String>> set = NO_SET;
		switch (locality) {
		case LOCAL_DATALAYER:
			set = dbLocal.retrieveKeysetFromMap(keyspace, table, mapName);
			break;
		case RIAK_DATALAYER:
			set = dbRiak.retrieveKeysetFromMap(keyspace, table, mapName);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = RETRIEVE_KEYSET_FROM_MAP;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(mapName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeySetPair)future.get();
			} catch (Exception e) {
			    LOGGER.error("retrieveKeysetFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeySetPair(NO_SET.getKey(), NO_SET.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			set = dbLocal.retrieveKeysetFromMap(keyspace, table, mapName);
			if (set.getKey().compareTo(mapName) != 0) {
				set = dbRiak.retrieveKeysetFromMap(keyspace, table, mapName);
			}
			break;
		}
		return new KeySetPair(set.getKey(), set.getValue());
	}

	@Override
	public KeyMapPair retrieveAllEntriesFromMap(String keyspace, String table, String mapName, int locality) throws TException {
		AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> map = NO_MAP;
		switch (locality) {
		case LOCAL_DATALAYER:
			map = dbLocal.retrieveAllEntriesFromMap(keyspace, table, mapName);
			break;
		case RIAK_DATALAYER:
			map = dbRiak.retrieveAllEntriesFromMap(keyspace, table, mapName);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = RETRIEVE_ALL_ENTRIES_FROM_MAP;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(mapName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeyMapPair)future.get();
			} catch (Exception e) {
			    LOGGER.error("retrieveAllEntriesFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeyMapPair(NO_MAP.getKey(), NO_MAP.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			map = dbLocal.retrieveAllEntriesFromMap(keyspace, table, mapName);
			if (map.getKey().compareTo(mapName) != 0) {
				map = dbRiak.retrieveAllEntriesFromMap(keyspace, table, mapName);
			}
			break;
		}
		return new KeyMapPair(map.getKey(), map.getValue());
	}

	@Override
	public boolean putEntryToMap(String keyspace, String table, String mapName, KeyValuePair keyValuePair, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.putEntryToMap(keyspace, table, mapName, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case RIAK_DATALAYER:
			return dbRiak.putEntryToMap(keyspace, table, mapName, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = PUT_ENTRY_TO_MAP;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(mapName);
			parameters.add(keyValuePair);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.putEntryToMap(keyspace, table, mapName, keyValuePair.getKey(), ByteBuffer.wrap(keyValuePair.getValue()));
		default:
			return false;
		}
	}

	@Override
	public KeyValuePair getEntryFromMap(String keyspace, String table, String mapName, String entryKey, int locality) throws TException {
		AbstractMap.SimpleEntry<String, ByteBuffer> row = NO_ROW;
		switch (locality) {
		case LOCAL_DATALAYER:
			row = dbLocal.getEntryFromMap(keyspace, table, mapName, entryKey);
			break;
		case RIAK_DATALAYER:
			row = dbRiak.getEntryFromMap(keyspace, table, mapName, entryKey);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = GET_ENTRY_FROM_MAP;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(mapName);
				parameters.add(entryKey);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (KeyValuePair)future.get();
			} catch (Exception e) {
			    LOGGER.error("getEntryFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return new KeyValuePair(NO_ROW.getKey(), NO_ROW.getValue());
			}
		case READ_LOCAL_THEN_RIAK:
			row = dbLocal.getEntryFromMap(keyspace, table, mapName, entryKey);
			if (row.getKey().compareTo(entryKey) != 0) {
				row = dbRiak.getEntryFromMap(keyspace, table, mapName, entryKey);
			}
			break;
		}
		return new KeyValuePair(row.getKey(), row.getValue());
	}

	@Override
	public boolean removeEntryFromMap(String keyspace, String table, String mapName, String entryKey, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.removeEntryFromMap(keyspace, table, mapName, entryKey);
		case RIAK_DATALAYER:
			return dbRiak.removeEntryFromMap(keyspace, table, mapName, entryKey);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = REMOVE_ENTRY_FROM_MAP;
			List<Object> parameters = new ArrayList<Object>(5);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(mapName);
			parameters.add(entryKey);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.removeEntryFromMap(keyspace, table, mapName, entryKey);
		default:
			return false;
		}
	}

	@Override
	public boolean containsKeyInMap(String keyspace, String table, String mapName, String entryKey, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.containsKeyInMap(keyspace, table, mapName, entryKey);
		case RIAK_DATALAYER:
			return dbRiak.containsKeyInMap(keyspace, table, mapName, entryKey);
		case READ_RIAK_ASYNC:
			try {
				int function = CONTAINS_KEY_IN_MAP;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(mapName);
				parameters.add(entryKey);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (Boolean)future.get();
			} catch (Exception e) {
			    LOGGER.error("containsKeyInMap() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return false;
			}
		case READ_LOCAL_THEN_RIAK:
			if (dbLocal.selectMaps(keyspace, table, 0, Integer.MAX_VALUE).contains(mapName)) {
				return dbLocal.containsKeyInMap(keyspace, table, mapName, entryKey);
			} else {
				return dbRiak.containsKeyInMap(keyspace, table, mapName, entryKey);
			}
		default:
			return false;
		}
	}

	@Override
	public boolean clearMap(String keyspace, String table, String mapName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.clearMap(keyspace, table, mapName);
		case RIAK_DATALAYER:
			return dbRiak.clearMap(keyspace, table, mapName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = CLEAR_MAP;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(mapName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.clearMap(keyspace, table, mapName);
		default:
			return false;
		}
	}

	@Override
	public int getSizeOfMap(String keyspace, String table, String mapName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.getSizeOfMap(keyspace, table, mapName);
		case RIAK_DATALAYER:
			return dbRiak.getSizeOfMap(keyspace, table, mapName);
		case READ_RIAK_ASYNC:
			try {
				int function = GET_SIZE_OF_MAP;
				List<Object> parameters = new ArrayList<Object>(4);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add(mapName);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (Integer)future.get();
			} catch (Exception e) {
			    LOGGER.error("getSizeOfMap() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Locality: " + locality, e);
				return 0;
			}
		case READ_LOCAL_THEN_RIAK:
			if (dbLocal.selectMaps(keyspace, table, 0, Integer.MAX_VALUE).contains(mapName)) {
				return dbLocal.getSizeOfMap(keyspace, table, mapName);
			} else {
				return dbRiak.getSizeOfMap(keyspace, table, mapName);
			}
		default:
			return 0;
		}
	}

	@Override
	public boolean deleteMap(String keyspace, String table, String mapName, int locality) throws TException {
		switch (locality) {
		case LOCAL_DATALAYER:
			return dbLocal.deleteMap(keyspace, table, mapName);
		case RIAK_DATALAYER:
			return dbRiak.deleteMap(keyspace, table, mapName);
		case WRITE_RIAK_ASYNC_LOCAL_SYNC:
			int function = DELETE_MAP;
			List<Object> parameters = new ArrayList<Object>(4);
			parameters.add(keyspace);
			parameters.add(table);
			parameters.add(mapName);
			parameters.add((Integer)RIAK_DATALAYER);
			execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
			return dbLocal.deleteMap(keyspace, table, mapName);
		default:
			return false;
		}
	}

	@SuppressWarnings("unchecked")
	@Override
	public List<String> selectMaps(String keyspace, String table, int start, int count, int locality) throws TException {
		List<String> keys = NO_KEYS;
		switch (locality) {
		case LOCAL_DATALAYER:
			keys = dbLocal.selectMaps(keyspace, table, start, count);
			break;
		case RIAK_DATALAYER:
			keys = dbRiak.selectMaps(keyspace, table, start, count);
			break;
		case READ_RIAK_ASYNC:
			try {
				int function = SELECT_MAPS;
				List<Object> parameters = new ArrayList<Object>(5);
				parameters.add(keyspace);
				parameters.add(table);
				parameters.add((Integer)start);
				parameters.add((Integer)count);
				parameters.add((Integer)RIAK_DATALAYER);
				Future<Object> future = execute(keyspace, table, new DataLayerServer(dbRiak, function, parameters));
				return (List<String>)future.get();
			} catch (Exception e) {
			    LOGGER.error("selectMaps() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  Locality: " + locality, e);
				return NO_KEYS;
			}
		case READ_LOCAL_THEN_RIAK:
			keys = dbLocal.selectMaps(keyspace, table, start, count);
			if (keys.size() <= 0) {
				keys = dbRiak.selectMaps(keyspace, table, start, count);
			}
			break;
		}
		return keys;
	}
	
	@Override
	public long totalMemory() throws TException {
		return Runtime.getRuntime().maxMemory();
	}

	@Override
	public long freeMemory() throws TException {
		return Runtime.getRuntime().maxMemory() - Runtime.getRuntime().totalMemory() + Runtime.getRuntime().freeMemory();
	}

	@Override
	public boolean updateTableTypeCache(String action, String table, String tableType) throws TException {
		return dbRiak.updateTableTypeCache(action, table, tableType);
	}


	public void start(InetSocketAddress bindAddr) throws TTransportException {
	    TNonblockingServerTransport transport = new TNonblockingServerSocket(bindAddr, DEFAULT_CLIENT_TIMEOUT);
        TThreadedSelectorServer.Args args = new TThreadedSelectorServer.Args(transport)
                .transportFactory(new TFramedTransport.Factory(DEFAULT_MAX_FRAME_LENGTH))
                .protocolFactory(new TCompactProtocol.Factory())
                .processor(new DataLayerService.Processor<Iface>(this))
                .selectorThreads(DEFAULT_SELECTOR_THREADS)
                .workerThreads(DEFAULT_WORKER_THREADS);
        server = new TThreadedSelectorServer(args);

		LOGGER.info("Listening on "+bindAddr);
		server.serve();
	}
	
	public void stop () {
		if (server != null) {
			server.stop();
		}
		
		if (executors != null) {
			for (ExecutorService executor: executors) {
				executor.shutdown();
			}
		}
		
		if (this.isMainDataLayerServer && dbRiak != null) {
			dbRiak.close();
		}
	}
	
	protected void finalize () throws Throwable {
		try {
			this.stop();
		} finally {
			super.finalize();
		}
	}
	
	public static void usage () {
		System.err.println("Usage: please provide configuration options either \n"
				+ " in a properties file as first argument\n"
				+ " or as environment variables\n"
				+ " or as Java system properties\n");
		System.err.println("OPTIONS:\n"
				+ " - datalayer.bind (DATALAYER_BIND)\t<host> ':' <port>\t(default: 0.0.0.0:4998)\n"
				+ " - riak.connect (RIAK_CONNECT)\t<host> ':' (<port>) [ ',' <host> ':' (<port>)? ]\t(default: 127.0.0.1:8087"
				+ " - all.datalayer.bind (ALL_DATALAYER_BIND)\t<host> ':' (<port>) [ ',' <host> ':' (<port>)? ]\t(default: 127.0.0.1:4998");
	}

	public static void main(String[] args) {
		Properties config = new Properties();
		if (args.length == 1) {
			try {
				config.load(new FileInputStream(args[0]));
			} catch (Exception e) {
				System.err.println("Error loading configuration from properties file: "+args[0]);
				DataLayerServer.usage();
				return;
			}
		} else {
			// Copy properties from env or system props
			Map<String,String> env = System.getenv();
			Properties sys = System.getProperties();
			for(String key : new String[]{"riak.connect","datalayer.bind", "all.datalayer.bind"}) {
				String envkey = key.replace('.', '_').toUpperCase();
				if(env.containsKey(envkey))
					config.put(key,env.get(envkey));
				else if(sys.containsKey(key))
					config.put(key, sys.get(key));
			}
		}

		DataLayerServer server = null;
		try {
			// Provide default values
			String[] bind = config.getProperty("datalayer.bind", "127.0.0.1:4998").split(":");
			String[] riak = config.getProperty("riak.connect","127.0.0.1:8087").split(",");
			String all_datalayer_binds_str = config.getProperty("all.datalayer.bind");
			String[] all_datalayer_binds = null;
			if (all_datalayer_binds_str != null)
			{
				all_datalayer_binds = config.getProperty("all.datalayer.bind").split(",");
			}
			// Parse riak nodes from <host1>':'(<port1>)? [',' <host2> ':' (<port2>)?]+
			Map<String,Integer> riakNodes = new HashMap<String,Integer>(riak.length);
			for(String node : riak) {
				String[] addr = node.split(":");
				Integer port = addr.length > 1 ? Integer.valueOf(addr[1]) : 8087;
				try {
					for(int i=20;i>0;i--) {
						try {
							InetAddress la = InetAddress.getByName(addr[0]);
							Socket s = new Socket(la, port);
							s.close();
							riakNodes.put(la.getHostAddress(), port);
							System.out.println("Using riak node: "+la.getHostAddress()+":"+port.toString());
							break;
						} catch (UnknownHostException e) {
							System.err.println("Error resolving "+addr[0]+", "+Integer.toString(i)+" retries remaining, waiting 5s");
							e.printStackTrace();
						} catch (IOException e) {
							System.err.println("Error connecting to "+addr[0]+":"+port+", "+Integer.toString(i)+" retries remaining, waiting 5s");
							e.printStackTrace();
						}
						Thread.sleep(5000);
					}
				} catch (InterruptedException e) {
					System.err.println("Interrupted trying to resolve riak node name "+addr[0]);
				}
			}

			Map<String,Integer> allDatalayerNodes = new HashMap<String,Integer>();
			if (all_datalayer_binds != null)
			{
				for(String node : all_datalayer_binds) {
					String[] addr = node.split(":");
					Integer port = addr.length > 1 ? Integer.valueOf(addr[1]) : 4998;
					LOGGER.info("New datalayer node: " + addr[0] + ":" + port.toString());
					allDatalayerNodes.put(addr[0], port);
				}
			}

			LOGGER.info("List of Datalayer Nodes: " + allDatalayerNodes.toString());
			// Create DataLayerServer
			server = new DataLayerServer(riakNodes, allDatalayerNodes);

			// Parse bind address from <host>':'(<port>)?
			InetSocketAddress bindAddr = new InetSocketAddress(bind[0],Integer.valueOf(bind[1]));

			server.start(bindAddr);
		} catch (TTransportException e) {
			System.err.println(e.getMessage());
		}
		catch (Exception e)
		{
		    System.err.println("Some other exception " + e.getMessage());
		    e.printStackTrace();
		}
		finally {
			if (server != null) {
				server.stop();
			}
		}
	}
}
