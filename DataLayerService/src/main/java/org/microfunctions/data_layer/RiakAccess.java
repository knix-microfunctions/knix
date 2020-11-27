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
import java.nio.charset.StandardCharsets;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.Set;

import com.basho.riak.client.api.RiakClient;
import com.basho.riak.client.api.commands.buckets.StoreBucketProperties;
import com.basho.riak.client.api.commands.datatypes.Context;
import com.basho.riak.client.api.commands.datatypes.CounterUpdate;
import com.basho.riak.client.api.commands.datatypes.FetchCounter;
import com.basho.riak.client.api.commands.datatypes.FetchMap;
import com.basho.riak.client.api.commands.datatypes.FetchSet;
import com.basho.riak.client.api.commands.datatypes.MapUpdate;
import com.basho.riak.client.api.commands.datatypes.RegisterUpdate;
import com.basho.riak.client.api.commands.datatypes.SetUpdate;
import com.basho.riak.client.api.commands.datatypes.UpdateCounter;
import com.basho.riak.client.api.commands.datatypes.UpdateMap;
import com.basho.riak.client.api.commands.datatypes.UpdateSet;
import com.basho.riak.client.api.commands.kv.DeleteValue;
import com.basho.riak.client.api.commands.kv.FetchValue;
import com.basho.riak.client.api.commands.kv.ListKeys;
import com.basho.riak.client.api.commands.kv.StoreValue;
import com.basho.riak.client.core.RiakCluster;
import com.basho.riak.client.core.RiakNode;
import com.basho.riak.client.core.query.Location;
import com.basho.riak.client.core.query.Namespace;
import com.basho.riak.client.core.query.RiakObject;
import com.basho.riak.client.core.query.crdt.types.RiakCounter;
import com.basho.riak.client.core.query.crdt.types.RiakDatatype;
import com.basho.riak.client.core.query.crdt.types.RiakMap;
import com.basho.riak.client.core.query.crdt.types.RiakRegister;
import com.basho.riak.client.core.query.crdt.types.RiakSet;
import com.basho.riak.client.core.util.BinaryValue;
import com.basho.riak.client.core.util.Constants;

import org.apache.thrift.TException;
import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.protocol.TProtocol;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TSocket;
import org.apache.thrift.transport.TTransport;

public class RiakAccess {

    private static final Logger LOGGER = LogManager.getLogger(RiakAccess.class);

	public static String BUCKET_TYPE_DEFAULT = "default";
    //public static final String BUCKET_TYPE_STRONG_CONSISTENCY = "strong"; // make sure there is a Riak bucket type called "strong" for strong consistency.
	// public static final String BUCKET_TYPE_TRIGGERS = "triggers"; // make sure there is a Riak bucket type called "triggers".
	public static final String BUCKET_TYPE_COUNTERS = "counters";	// make sure there is a Riak bucket type called "counters" with its data type being "counter".
    // public static final String BUCKET_TYPE_TRIGGERABLE_COUNTERS = "mfn_counter_trigger"; // make sure there is a Riak bucket type called "mfn_counter_trigger".
	public static final String BUCKET_TYPE_SETS = "sets";	// make sure there is a Riak bucket type called "sets" with its data type being "set".
	public static final String BUCKET_TYPE_MAPS = "maps";	// make sure there is a Riak bucket type called "maps" with its data type being "map".
	public static final String BUCKET_TYPE_ALL = "all";
	public static final Set<String> ALL_BUCKET_TYPES = new HashSet<String>();
	public static final Set<String> KV_BUCKET_TYPES = new HashSet<String>();
	public static final Set<String> COUNTER_BUCKET_TYPES = new HashSet<String>();
	public static final Set<String> CONSISTENCY_BUCKET_TYPES = new HashSet<String>();
	
	private static final AbstractMap.SimpleEntry<String, ByteBuffer> NO_ROW = new AbstractMap.SimpleEntry<String, ByteBuffer>(new String(), ByteBuffer.allocate(0));
	private static final AbstractMap.SimpleEntry<String, Long> NO_COUNTER = new AbstractMap.SimpleEntry<String, Long>(new String(), 0L);
	private static final AbstractMap.SimpleEntry<String, Set<String>> NO_SET = new AbstractMap.SimpleEntry<String, Set<String>>(new String(), new HashSet<String>(0));
	private static final AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> NO_MAP = new AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>>(new String(), new HashMap<String, ByteBuffer>(0));
	private static final List<AbstractMap.SimpleEntry<String, String>> NO_TABLES = new ArrayList<AbstractMap.SimpleEntry<String, String>>(0);
	private static final List<AbstractMap.SimpleEntry<String, Integer>> NO_KEYSPACES = new ArrayList<AbstractMap.SimpleEntry<String, Integer>>(0);
	private static final List<String> NO_KEYS = new ArrayList<String>(0);
    private static final String MFN_KEYSPACES = "__MFn_Keyspaces__";
	
	private static int NUM_NODES = 0;
	private static final int MIN_NODES_FOR_STRONG_CONSISTENCY = 3;
	
	public static ConcurrentHashMap<String, String> BUCKET_TO_TYPE = new ConcurrentHashMap<String, String>();
		
	private RiakCluster cluster = null;
	private RiakClient client = null;
	private Map<String,Integer> allDatalayerNodes;
	
	public RiakAccess(Map<String,Integer> allDatalayerNodes) {
		this.allDatalayerNodes = allDatalayerNodes;
	}

	public void connect (Map<String,Integer> riakNodes) {
		List<RiakNode> nodes = new ArrayList<RiakNode>(riakNodes.size());
		for (Entry<String,Integer> addr : riakNodes.entrySet()) {
			RiakNode node = new RiakNode.Builder().withRemoteAddress(addr.getKey()).withRemotePort(addr.getValue()).build();
			nodes.add(node);
		}
		
		cluster = new RiakCluster.Builder(nodes).build();
		cluster.start();

        ALL_BUCKET_TYPES.add(BUCKET_TYPE_DEFAULT);
        //ALL_BUCKET_TYPES.add(BUCKET_TYPE_STRONG_CONSISTENCY);
		// ALL_BUCKET_TYPES.add(BUCKET_TYPE_TRIGGERS);
        ALL_BUCKET_TYPES.add(BUCKET_TYPE_COUNTERS);
        // ALL_BUCKET_TYPES.add(BUCKET_TYPE_TRIGGERABLE_COUNTERS);
        ALL_BUCKET_TYPES.add(BUCKET_TYPE_SETS);
        ALL_BUCKET_TYPES.add(BUCKET_TYPE_MAPS);
        ALL_BUCKET_TYPES.add(BUCKET_TYPE_ALL);
        
        KV_BUCKET_TYPES.add(BUCKET_TYPE_DEFAULT);
        //KV_BUCKET_TYPES.add(BUCKET_TYPE_STRONG_CONSISTENCY);
		// KV_BUCKET_TYPES.add(BUCKET_TYPE_TRIGGERS);
        
        COUNTER_BUCKET_TYPES.add(BUCKET_TYPE_COUNTERS);
        // COUNTER_BUCKET_TYPES.add(BUCKET_TYPE_TRIGGERABLE_COUNTERS);
        
        CONSISTENCY_BUCKET_TYPES.add(BUCKET_TYPE_DEFAULT);
        //CONSISTENCY_BUCKET_TYPES.add(BUCKET_TYPE_STRONG_CONSISTENCY);
        
		NUM_NODES = cluster.getNodes().size();
		//if (NUM_NODES >= MIN_NODES_FOR_STRONG_CONSISTENCY) {
		//    BUCKET_TYPE_DEFAULT = BUCKET_TYPE_STRONG_CONSISTENCY;
		//}
		
        client = new RiakClient(cluster);
        
        try {
            Namespace bucket = new Namespace(BUCKET_TYPE_DEFAULT, MFN_KEYSPACES);
            StoreBucketProperties props = new StoreBucketProperties.Builder(bucket).withNVal(NUM_NODES).build();
            client.execute(props);
            
            this.initiateBucketToTypeMapping();
        } catch (Exception e) {
            LOGGER.error("connect() failed.", e);
        }
	}
	
	private void initiateBucketToTypeMapping () {
	    List<AbstractMap.SimpleEntry<String, Integer>> keyspaces = this.listKeyspaces(0, Integer.MAX_VALUE);
	    for (AbstractMap.SimpleEntry<String, Integer> keyspaceEntry: keyspaces) {
	        String keyspace = keyspaceEntry.getKey();
	        List<AbstractMap.SimpleEntry<String, String>> tables = this.listTables(keyspace, BUCKET_TYPE_ALL, 0, Integer.MAX_VALUE);
	        for (AbstractMap.SimpleEntry<String, String> tableEntry: tables) {
	            String table = tableEntry.getKey();
	            String tableType = tableEntry.getValue();
	            BUCKET_TO_TYPE.put(keyspace + ";" + table, tableType);
	        }
	    }
        LOGGER.info("initiateBucketToTypeMapping() done.");
	}
		
	public void close() {
		if (client != null) {
			client.shutdown();
		}
		LOGGER.info("Riak client shutdown.");
	}
	
	private boolean detectInvalidName (String str) {
		if (str == null) {
			return false;
		}
		
		if (str.contains(" ") || str.contains(".") || str.contains(";")) {	// don't change!
			return true;
		}
		
		return false;
	}
	
	public boolean createKeyspace (String keyspace, Metadata metadata) {
	    if (this.detectInvalidName(keyspace) || ! metadata.isSetReplicationFactor()) {
	        LOGGER.warn("createKeyspace() invalid parameters.  Keyspace: " + keyspace + "  Metadata: " + metadata);
	        return false;
	    }
	    
	    int replicationFactor = metadata.getReplicationFactor();
		if (replicationFactor < 1) {
		    LOGGER.warn("createKeyspace() invalid parameters.  Keyspace: " + keyspace + "  Metadata: " + metadata);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			StoreBucketProperties props = new StoreBucketProperties.Builder(bucket).withNVal(NUM_NODES).build();
			client.execute(props);
			LOGGER.info("createKeyspace() Keyspace: " + keyspace + "  Metadata: replication factor: " + Integer.toString(replicationFactor));
			return this.insertRow(MFN_KEYSPACES, null, keyspace, ByteBuffer.allocate(Integer.BYTES).putInt(replicationFactor));
		} catch (Exception e) {
		    LOGGER.error("createKeyspace() failed.  Keyspace: " + keyspace + "  Metadata: " + metadata, e);
			return false;
		}
	}
	
	public boolean dropKeyspace (String keyspace) {
		if (this.detectInvalidName(keyspace)) {
		    LOGGER.warn("dropKeyspace() invalid parameters.  Keyspace: " + keyspace);
			return false;
		}
		
		try {
			if (! this.deleteRow(MFN_KEYSPACES, null, keyspace)) {
			    LOGGER.error("dropKeyspace() failed.  Keyspace: " + keyspace);
				return false;
			}
			
			List<String> tables = this.selectAllKeysWithType(keyspace, null, BUCKET_TYPE_DEFAULT);
			for (String table: tables) {
				this.dropTableWithoutType(keyspace, table);
			}
			return true;
		} catch (Exception e) {
		    LOGGER.error("dropKeyspace() failed.  Keyspace: " + keyspace, e);
			return false;
		}
	}
	
	public int getReplicationFactor (String keyspace) {
		if (this.detectInvalidName(keyspace)) {
		    LOGGER.warn("getReplicationFactor() invalid parameters.  Keyspace: " + keyspace);
			return 0;
		}
		
		try {
			AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(MFN_KEYSPACES, null, keyspace);
			if (row.getKey().compareTo(keyspace) != 0) {
			    LOGGER.error("getReplicationFactor() failed.  Keyspace: " + keyspace);
				return 0;
			}
			return row.getValue().getInt();
		} catch (Exception e) {
		    LOGGER.error("getReplicationFactor() failed.  Keyspace: " + keyspace, e);
			return 0;
		}
	}
	
    public List<AbstractMap.SimpleEntry<String, Integer>> listKeyspaces (int start, int count) {
        if (start < 0 || count < 1) {
            LOGGER.warn("listKeyspaces() invalid parameters.  Start: " + start + "  Count: " + count);
            return NO_KEYSPACES;
        }
        
        try {
            List<String> names = this.selectAllKeysWithType(MFN_KEYSPACES, null, BUCKET_TYPE_DEFAULT);
            if (names.size() <= 0) {
                return NO_KEYSPACES;
            }
            Collections.sort(names);
            
            List<AbstractMap.SimpleEntry<String, Integer>> keyspaces = new ArrayList<AbstractMap.SimpleEntry<String, Integer>>();
            
            for (String name: names) {
                AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(MFN_KEYSPACES, null, name);
                if (row.getKey().compareTo(name) != 0) {
                    continue;
                }
                int replicationFactor = row.getValue().getInt();
                
                if ((--start) >= 0) {
                    continue;
                }
                
                keyspaces.add(new AbstractMap.SimpleEntry<String, Integer>(name, replicationFactor));
                
                if ((--count) <= 0) {
                    break;
                }
            }
            return keyspaces;
        } catch (Exception e) {
            LOGGER.error("listKeyspaces() failed.  Start: " + start + "  Count: " + count, e);
            return NO_KEYSPACES;
        }
    }
    
	public List<AbstractMap.SimpleEntry<String, String>> listTables (String keyspace, String tableType, int start, int count) {
		if (this.detectInvalidName(keyspace) || ! ALL_BUCKET_TYPES.contains(tableType) || start < 0 || count < 1) {
		    LOGGER.warn("listTables() invalid parameters.  Keyspace: " + keyspace + "  TableType: " + tableType + "  Start: " + start + "  Count: " + count);
			return NO_TABLES;
		}
		
		try {
			List<String> names = this.selectAllKeysWithType(keyspace, null, BUCKET_TYPE_DEFAULT);
			if (names.size() <= 0) {
				return NO_TABLES;
			}
			Collections.sort(names);
			
			List<AbstractMap.SimpleEntry<String, String>> tables = new ArrayList<AbstractMap.SimpleEntry<String, String>>();
			
			for (String name: names) {
				AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(keyspace, null, name);
				if (row.getKey().compareTo(name) != 0) {
					continue;
				}
				String type = new String(row.getValue().array(), StandardCharsets.UTF_8);
				
				if (tableType.compareTo(BUCKET_TYPE_ALL) != 0 && tableType.compareTo(type) != 0) {
					continue;
				}
				
				if ((--start) >= 0) {
					continue;
				}
				
				tables.add(new AbstractMap.SimpleEntry<String, String>(name, type));
				
				if ((--count) <= 0) {
					break;
				}
			}
			return tables;
		} catch (Exception e) {
		    LOGGER.error("listTables() failed.  Keyspace: " + keyspace + "  TableType: " + tableType + "  Start: " + start + "  Count: " + count, e);
			return NO_TABLES;
		}
	}
	
	public boolean createTable (String keyspace, String table, Metadata metadata) {
	    if (! metadata.isSetTableType()) {
	        LOGGER.warn("createTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Metadata: " + metadata);
	        return false;
		}
		
	    String tableType = metadata.getTableType();
	    if (! KV_BUCKET_TYPES.contains(tableType)) {
	        LOGGER.warn("createTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Metadata: " + metadata);
	        return false;
	    }
	    
        return this.createTableWithType(keyspace, table, tableType);
	}
	
	public boolean createCounterTable (String keyspace, String table, Metadata metadata) {
        if (! metadata.isSetTableType()) {
            LOGGER.warn("createCounterTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Metadata: " + metadata);
            return false;
        }
        
        String tableType = metadata.getTableType();
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("createCounterTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Metadata: " + metadata);
            return false;
        }
	    
		return this.createTableWithType(keyspace, table, tableType);
	}
	
	public boolean createSetTable (String keyspace, String table) {
		return this.createTableWithType(keyspace, table, BUCKET_TYPE_SETS);
	}
	
	public boolean createMapTable (String keyspace, String table) {
		return this.createTableWithType(keyspace, table, BUCKET_TYPE_MAPS);
	}
	
	private boolean createTableWithType (String keyspace, String table, String tableType) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("createTableWithType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
			return false;
		}
		
		try {
			AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(MFN_KEYSPACES, null, keyspace);
			if (row.getKey().compareTo(keyspace) != 0) {
			    LOGGER.error("createTableWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
				return false;
			}
			int replicationFactor = row.getValue().getInt();
			
			if (CONSISTENCY_BUCKET_TYPES.contains(tableType)) {
			    tableType = BUCKET_TYPE_DEFAULT;
			}
			
			Namespace bucket = new Namespace(tableType, keyspace + ";" + table);
			StoreBucketProperties props = new StoreBucketProperties.Builder(bucket).withNVal(replicationFactor).withW(replicationFactor).build();
			client.execute(props);
			LOGGER.info("createTableWithType() Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
			boolean success = this.insertRow(keyspace, null, table, ByteBuffer.wrap(tableType.getBytes(StandardCharsets.UTF_8)));
			if (success) {
			    BUCKET_TO_TYPE.put(keyspace + ";" + table, tableType);
			    notifyOthersDatalayerServers("put", keyspace + ";" + table, tableType);
			}
			return success;
		} catch (Exception e) {
		    LOGGER.error("createTableWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType, e);
			return false;
		}
	}
	
	public boolean dropTable (String keyspace, String table) {
	    String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
	    if (! KV_BUCKET_TYPES.contains(tableType)) {
	        LOGGER.warn("dropTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
	        return false;
	    }
	    
        return this.dropTableWithType(keyspace, table, tableType);
	}

	public boolean dropCounterTable (String keyspace, String table) {
        String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("dropCounterTable() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
            return false;
        }

	    return this.dropTableWithType(keyspace, table, tableType);
	}

	public boolean dropSetTable (String keyspace, String table) {
		return this.dropTableWithType(keyspace, table, BUCKET_TYPE_SETS);
	}

	public boolean dropMapTable (String keyspace, String table) {
		return this.dropTableWithType(keyspace, table, BUCKET_TYPE_MAPS);
	}

	private boolean dropTableWithType (String keyspace, String table, String tableType) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("dropTableWithType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
			return false;
		}
		
		try {
			AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(keyspace, null, table);
			if (table.compareTo(row.getKey()) != 0 || tableType.compareTo(new String(row.getValue().array(), StandardCharsets.UTF_8)) != 0) {
			    LOGGER.error("dropTableWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
				return false;
			}
			
			if (! this.deleteRow(keyspace, null, table)) {
			    LOGGER.error("dropTableWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
				return false;
			}
			
			BUCKET_TO_TYPE.remove(keyspace + ";" + table);
			notifyOthersDatalayerServers("remove", keyspace + ";" + table, "");
			
			List<String> keys = this.selectAllKeysWithType(keyspace, table, tableType);
			for (String key: keys) {
				this.deleteRowWithType(keyspace, table, key, tableType);
			}
			return true;
		} catch (Exception e) {
		    LOGGER.error("dropTableWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType, e);
			return false;
		}
	}
	
	private boolean dropTableWithoutType (String keyspace, String table) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("dropTableWithoutType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			AbstractMap.SimpleEntry<String, ByteBuffer> row = this.selectRow(keyspace, null, table);
			if (table.compareTo(row.getKey()) != 0) {
			    LOGGER.error("dropTableWithoutType() failed.  Keyspace: " + keyspace + "  Table: " + table);
				return false;
			}
			String tableType = new String(row.getValue().array(), StandardCharsets.UTF_8);
			
			if (! this.deleteRow(keyspace, null, table)) {
			    LOGGER.error("dropTableWithoutType() failed.  Keyspace: " + keyspace + "  Table: " + table);
				return false;
			}
			
			BUCKET_TO_TYPE.remove(keyspace + ";" + table);
			notifyOthersDatalayerServers("remove", keyspace + ";" + table, "");
			
			List<String> keys = this.selectAllKeysWithType(keyspace, table, tableType);
			for (String key: keys) {
				this.deleteRowWithType(keyspace, table, key, tableType);
			}
			return true;
		} catch (Exception e) {
		    LOGGER.error("dropTableWithoutType() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}

	public boolean insertRow (String keyspace, String table, String key, ByteBuffer value) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			LOGGER.warn("insertRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}

        String tableType = null;
        if (table == null) {
            tableType = BUCKET_TYPE_DEFAULT;
        } else {
            tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        }
		
		if (! KV_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("insertRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
		    return false;
		}

		try {
            if (value.array() == null || value.array().length <= 0) {
                value = ByteBuffer.wrap(new byte[] {0});
            }

			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}

			Location location = new Location(bucket, key);
			RiakObject object = new RiakObject().setContentType(Constants.CTYPE_OCTET_STREAM).setValue(BinaryValue.unsafeCreate(value.array()));
			StoreValue store = new StoreValue.Builder(object).withLocation(location).build();
			client.execute(store);
			return true;
		} catch (Exception e) {
			LOGGER.error("insertRow() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public AbstractMap.SimpleEntry<String, ByteBuffer> selectRow (String keyspace, String table, String key) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
			LOGGER.warn("selectRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_ROW;
		}

        String tableType = null;
        if (table == null) {
            tableType = BUCKET_TYPE_DEFAULT;
        } else {
            tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        }
        
        if (! KV_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("selectRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Key: " + key + ", tableType: " + tableType);
            return NO_ROW;
        }
		
		try {
			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}
			
			Location location = new Location(bucket, key);
			FetchValue fetch = new FetchValue.Builder(location).build();
			FetchValue.Response response = client.execute(fetch);
			
			RiakObject object = response.getValue(RiakObject.class);
			if (object == null || object.getValue() == null) {
			    return NO_ROW;
			}
			
			ByteBuffer value = ByteBuffer.wrap(object.getValue().unsafeGetValue());
			
			if (value.hasArray() && value.array().length == 1 && value.array()[0] == 0)
			{
				value = ByteBuffer.wrap(new byte[] {});
			}
			
			return new AbstractMap.SimpleEntry<String, ByteBuffer>(key, value);
		} catch (Exception e) {
			LOGGER.error("selectRow() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_ROW;
		}
	}
	
	public boolean updateRow (String keyspace, String table, String key, ByteBuffer value) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("updateRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
        String tableType = null;
        if (table == null) {
            tableType = BUCKET_TYPE_DEFAULT;
        } else {
            tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        }
        
        if (! KV_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("updateRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
            return false;
        }
        
		try {
            if (value.array() == null || value.array().length <= 0) {
                value = ByteBuffer.wrap(new byte[] {0});
            }

			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}
			
			Location location = new Location(bucket, key);
			FetchValue fetch = new FetchValue.Builder(location).withOption(FetchValue.Option.DELETED_VCLOCK, true).build();
			FetchValue.Response response = client.execute(fetch);
			
			RiakObject object = response.getValue(RiakObject.class);
			object.setValue(BinaryValue.unsafeCreate(value.array()));
			
			StoreValue store = new StoreValue.Builder(object).withLocation(location).build();
			client.execute(store);
			return true;
		} catch (Exception e) {
            LOGGER.error("updateRow() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}

	public boolean deleteRow (String keyspace, String table, String key) {
        String tableType = null;
        if (table == null) {
            tableType = BUCKET_TYPE_DEFAULT;
        } else {
            tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        }
        
	    if (! KV_BUCKET_TYPES.contains(tableType)) {
	        LOGGER.warn("deleteRow() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
	        return false;
	    }
	    
		return this.deleteRowWithType(keyspace, table, key, tableType);
	}
	
	private boolean deleteRowWithType (String keyspace, String table, String key, String tableType) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("deleteRowWithType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
			return false;
		}
		
		try {
			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}
			
			Location location = new Location(bucket, key);
			DeleteValue delete = new DeleteValue.Builder(location).build();
			client.execute(delete);
			return true;
		} catch (Exception e) {
            LOGGER.error("deleteRowWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType, e);
			return false;
		}
	}

	public List<String> selectKeys (String keyspace, String table, int start, int count) {
        String tableType = null;
        if (table == null) {
            tableType = BUCKET_TYPE_DEFAULT;
        } else {
            tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        }
        
	    if (! KV_BUCKET_TYPES.contains(tableType)) {
	        LOGGER.warn("selectKeys() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count);
	        return NO_KEYS;
	    }
	    
		return this.selectKeysWithType(keyspace, table, start, count, tableType);
	}
	
	private List<String> selectKeysWithType (String keyspace, String table, int start, int count, String tableType) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table) || start < 0 || count < 1) {
		    LOGGER.warn("selectKeysWithType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  TableType: " + tableType);
			return NO_KEYS;
		}
		
		try {
			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}
			
			ListKeys list = new ListKeys.Builder(bucket).build();
			ListKeys.Response response = client.execute(list);
			
			List<String> keys = new ArrayList<String>();
			for (Location location: response) {
				keys.add(location.getKeyAsString());
			}
			
			int size = keys.size();
			if (start >= size) {
				return NO_KEYS;
			}
			int end = (start + count > start && start + count <= size)? (start + count): size;
			
			Collections.sort(keys);
			return keys.subList(start, end);
		} catch (Exception e) {
		    LOGGER.error("selectKeysWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  TableType: " + tableType, e);
			return NO_KEYS;
		}
	}
	
	private List<String> selectAllKeysWithType (String keyspace, String table, String tableType) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("selectAllKeysWithType() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
			return NO_KEYS;
		}
		
		try {
			Namespace bucket = null;
			if (table == null) {
				bucket = new Namespace(BUCKET_TYPE_DEFAULT, keyspace);
			} else {
				bucket = new Namespace(tableType, keyspace + ";" + table);
			}
			
			ListKeys list = new ListKeys.Builder(bucket).build();
			ListKeys.Response response = client.execute(list);
			
			List<String> keys = new ArrayList<String>();
			for (Location location: response) {
				keys.add(location.getKeyAsString());
			}
			return keys;
		} catch (Exception e) {
		    LOGGER.error("selectAllKeysWithType() failed.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType, e);
			return NO_KEYS;
		}
	}
	
	public boolean createCounter (String keyspace, String table, String counterName, long initialValue) {
		AbstractMap.SimpleEntry<String, Long> counter = this.incrementCounter(keyspace, table, counterName, initialValue);
		if (counter.getKey().compareTo(counterName) == 0) {
		    if (counter.getValue() == initialValue) {
		        return true;
		    } else {
		        this.decrementCounter(keyspace, table, counterName, initialValue);
		    }
		}
		LOGGER.warn("createCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
		return false;
	}
	
	public AbstractMap.SimpleEntry<String, Long> getCounter (String keyspace, String table, String counterName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("getCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_COUNTER;
		}
		
		String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("getCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
            return NO_COUNTER;
        }
		
		try {
			Namespace bucket = new Namespace(tableType, keyspace + ";" + table);
			Location location = new Location(bucket, counterName);
			
			FetchCounter fetch = new FetchCounter.Builder(location).build();
			FetchCounter.Response response = client.execute(fetch);
			RiakCounter counter = response.getDatatype();
			Long counterValue = counter.view();
			return new AbstractMap.SimpleEntry<String, Long>(counterName, counterValue);
		} catch (Exception e) {
		    LOGGER.error("getCounter() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_COUNTER;
		}
	}
	
	public AbstractMap.SimpleEntry<String, Long> incrementCounter (String keyspace, String table, String counterName, long increment) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("incrementCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_COUNTER;
		}
		
        String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("incrementCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
            return NO_COUNTER;
        }
        
		try {
			Namespace bucket = new Namespace(tableType, keyspace + ";" + table);
			Location location = new Location(bucket, counterName);
			
			CounterUpdate delta = new CounterUpdate(increment);
			UpdateCounter update = new UpdateCounter.Builder(location, delta).withReturnDatatype(true).build();
			UpdateCounter.Response response = client.execute(update);
			RiakCounter counter = response.getDatatype();
			Long counterValue = counter.view();
			return new AbstractMap.SimpleEntry<String, Long>(counterName, counterValue);
		} catch (Exception e) {
		    LOGGER.error("incrementCounter() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_COUNTER;
		}
	}
	
	public AbstractMap.SimpleEntry<String, Long> decrementCounter (String keyspace, String table, String counterName, long decrement) {
	    AbstractMap.SimpleEntry<String, Long> counter = this.incrementCounter(keyspace, table, counterName, -decrement);
	    if (counter.getKey().compareTo(counterName) == 0) {
	        return counter;
	    }
	    LOGGER.warn("decrementCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
	    return NO_COUNTER;
	}
	
	public boolean deleteCounter (String keyspace, String table, String counterName) {
        String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("deleteCounter() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  TableType: " + tableType);
            return false;
        }
        
		return this.deleteRowWithType(keyspace, table, counterName, tableType);
	}
	
	public List<String> selectCounters (String keyspace, String table, int start, int count) {
        String tableType = BUCKET_TO_TYPE.get(keyspace + ";" + table);
        if (! COUNTER_BUCKET_TYPES.contains(tableType)) {
            LOGGER.warn("selectCounters() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table + "  Start: " + start + "  Count: " + count + "  TableType: " + tableType);
            return NO_KEYS;
        }
        
		return this.selectKeysWithType(keyspace, table, start, count, tableType);
	}
	
	public boolean createSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("createSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			new Location(new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table), setName);
			return true;
		} catch (Exception e) {
		    LOGGER.error("createSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public AbstractMap.SimpleEntry<String, Set<String>> retrieveSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("retrieveSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_SET;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table);
			Location location = new Location(bucket, setName);
			
			FetchSet fetch = new FetchSet.Builder(location).build();
			FetchSet.Response response = client.execute(fetch);
			RiakSet rSet = response.getDatatype();
			Set<BinaryValue> binarySet = rSet.view();
			
			Set<String> set = new HashSet<String>(binarySet.size());
			for (BinaryValue item: binarySet) {
				set.add(item.toString());
			}
			return new AbstractMap.SimpleEntry<String, Set<String>>(setName, set);
		} catch (Exception e) {
		    LOGGER.error("retrieveSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_SET;
		}
	}
	
	public boolean addItemToSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("addItemToSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table);
			Location location = new Location(bucket, setName);
			
			SetUpdate item = new SetUpdate().add(setItem);
			UpdateSet update = new UpdateSet.Builder(location, item).build();
			client.execute(update);
			return true;
		} catch (Exception e) {
		    LOGGER.error("addItemToSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public boolean removeItemFromSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("removeItemFromSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table);
			Location location = new Location(bucket, setName);
			
			FetchSet fetch = new FetchSet.Builder(location).build();
			FetchSet.Response response = client.execute(fetch);
			Context context = response.getContext();
			
			SetUpdate item = new SetUpdate().remove(setItem);
			UpdateSet update = new UpdateSet.Builder(location, item).withContext(context).build();
			client.execute(update);
			return true;
		} catch (Exception e) {
		    LOGGER.error("removeItemFromSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public boolean containsItemInSet (String keyspace, String table, String setName, String setItem) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("containsItemInSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table);
			Location location = new Location(bucket, setName);
			
			FetchSet fetch = new FetchSet.Builder(location).build();
			FetchSet.Response response = client.execute(fetch);
			RiakSet rSet = response.getDatatype();
			Set<BinaryValue> binarySet = rSet.view();
			return binarySet.contains(BinaryValue.create(setItem));
		} catch (Exception e) {
		    LOGGER.error("containsItemInSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public boolean clearSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("clearSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			AbstractMap.SimpleEntry<String, Set<String>> set = this.retrieveSet(keyspace, table, setName);
			if (set.getKey().compareTo(setName) != 0) {
			    LOGGER.error("clearSet() failed.  Keyspace: " + keyspace + "  Table: " + table);
				return false;
			}
			
			Set<String> items = set.getValue();
			for (String item: items) {
				this.removeItemFromSet(keyspace, table, setName, item);
			}
			return true;
		} catch (Exception e) {
		    LOGGER.error("clearSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public int getSizeOfSet (String keyspace, String table, String setName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("getSizeOfSet() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return 0;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_SETS, keyspace + ";" + table);
			Location location = new Location(bucket, setName);
			
			FetchSet fetch = new FetchSet.Builder(location).build();
			FetchSet.Response response = client.execute(fetch);
			RiakSet rSet = response.getDatatype();
			Set<BinaryValue> binarySet = rSet.view();
			return binarySet.size();
		} catch (Exception e) {
		    LOGGER.error("getSizeOfSet() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return 0;
		}
	}
	
	public boolean deleteSet (String keyspace, String table, String setName) {
		return this.deleteRowWithType(keyspace, table, setName, BUCKET_TYPE_SETS);
	}
	
	public List<String> selectSets (String keyspace, String table, int start, int count) {
		return this.selectKeysWithType(keyspace, table, start, count, BUCKET_TYPE_SETS);
	}
	
	public boolean createMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("createMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			new Location(new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table), mapName);
			return true;
		} catch (Exception e) {
		    LOGGER.error("createMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public AbstractMap.SimpleEntry<String, Set<String>> retrieveKeysetFromMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("retrieveKeysetFromMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_SET;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			RiakMap rMap = response.getDatatype();
			Map<BinaryValue, List<RiakDatatype>> entries = rMap.view();
			
			Set<String> set = new HashSet<String>(entries.size());
			for (BinaryValue entryKey: entries.keySet()) {
				set.add(entryKey.toString());
			}
			return new AbstractMap.SimpleEntry<String, Set<String>>(mapName, set);
		} catch (Exception e) {
		    LOGGER.error("retrieveKeysetFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_SET;
		}
	}
	
	public AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>> retrieveAllEntriesFromMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("retrieveAllEntriesFromMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_MAP;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			RiakMap rMap = response.getDatatype();
			Map<BinaryValue, List<RiakDatatype>> entries = rMap.view();
			
			Map<String, ByteBuffer> map = new HashMap<String, ByteBuffer>(entries.size());
			for (Map.Entry<BinaryValue, List<RiakDatatype>> entry: entries.entrySet()) {
				String entryKey = entry.getKey().toString();
				RiakRegister rRegister = rMap.getRegister(entryKey);
				ByteBuffer entryValue = ByteBuffer.wrap(rRegister.view().unsafeGetValue());
				map.put(entryKey, entryValue);
			}
			return new AbstractMap.SimpleEntry<String, Map<String, ByteBuffer>>(mapName, map);
		} catch (Exception e) {
		    LOGGER.error("retrieveAllEntriesFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_MAP;
		}
	}
	
	public boolean putEntryToMap (String keyspace, String table, String mapName, String entryKey, ByteBuffer entryValue) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("putEntryToMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			RegisterUpdate register = new RegisterUpdate(BinaryValue.unsafeCreate(entryValue.array()));
			MapUpdate entry = new MapUpdate().update(entryKey, register);
			UpdateMap update = new UpdateMap.Builder(location, entry).build();
			client.execute(update);
			return true;
		} catch (Exception e) {
		    LOGGER.error("putEntryToMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public AbstractMap.SimpleEntry<String, ByteBuffer> getEntryFromMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("getEntryFromMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return NO_ROW;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			RiakMap rMap = response.getDatatype();
			RiakRegister rRegister = rMap.getRegister(entryKey);
			ByteBuffer entryValue = ByteBuffer.wrap(rRegister.view().unsafeGetValue());
			return new AbstractMap.SimpleEntry<String, ByteBuffer>(entryKey, entryValue);
		} catch (Exception e) {
		    LOGGER.error("getEntryFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return NO_ROW;
		}
	}
	
	public boolean removeEntryFromMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("removeEntryFromMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			Context context = response.getContext();
			
			MapUpdate entry = new MapUpdate().removeRegister(entryKey);
			UpdateMap update = new UpdateMap.Builder(location, entry).withContext(context).build();
			client.execute(update);
			return true;
		} catch (Exception e) {
		    LOGGER.error("removeEntryFromMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public boolean containsKeyInMap (String keyspace, String table, String mapName, String entryKey) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("containsKeyInMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			RiakMap rMap = response.getDatatype();
			Map<BinaryValue, List<RiakDatatype>> entries = rMap.view();
			return entries.containsKey(BinaryValue.create(entryKey));
		} catch (Exception e) {
		    LOGGER.error("containsKeyInMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public boolean clearMap(String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("clearMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return false;
		}
		
		try {
			AbstractMap.SimpleEntry<String, Set<String>> keyset = this.retrieveKeysetFromMap(keyspace, table, mapName);
			if (keyset.getKey().compareTo(mapName) != 0) {
			    LOGGER.error("clearMap() failed.  Keyspace: " + keyspace + "  Table: " + table);
				return false;
			}
			
			Set<String> keys = keyset.getValue();
			for (String key: keys) {
				this.removeEntryFromMap(keyspace, table, mapName, key);
			}
			return true;
		} catch (Exception e) {
		    LOGGER.error("clearMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return false;
		}
	}
	
	public int getSizeOfMap (String keyspace, String table, String mapName) {
		if (this.detectInvalidName(keyspace) || this.detectInvalidName(table)) {
		    LOGGER.warn("getSizeOfMap() invalid parameters.  Keyspace: " + keyspace + "  Table: " + table);
			return 0;
		}
		
		try {
			Namespace bucket = new Namespace(BUCKET_TYPE_MAPS, keyspace + ";" + table);
			Location location = new Location(bucket, mapName);
			
			FetchMap fetch = new FetchMap.Builder(location).build();
			FetchMap.Response response = client.execute(fetch);
			RiakMap rMap = response.getDatatype();
			Map<BinaryValue, List<RiakDatatype>> entries = rMap.view();
			return entries.size();
		} catch (Exception e) {
		    LOGGER.error("getSizeOfMap() failed.  Keyspace: " + keyspace + "  Table: " + table, e);
			return 0;
		}
	}
	
	public boolean deleteMap (String keyspace, String table, String mapName) {
		return this.deleteRowWithType(keyspace, table, mapName, BUCKET_TYPE_MAPS);
	}
	
	public List<String> selectMaps (String keyspace, String table, int start, int count) {
		return this.selectKeysWithType(keyspace, table, start, count, BUCKET_TYPE_MAPS);
	}

	private boolean notifyOthersDatalayerServers(String action, String table, String tableType) {
		//LOGGER.info("notifyOthersDatalayerServers: action: " + action + ", table: " + table + ", type: " + tableType);
		for (Map.Entry<String, Integer> entry : allDatalayerNodes.entrySet()) {
			String serverIP = entry.getKey();
			Integer serverPort = entry.getValue();
			LOGGER.info("notifyOthersDatalayerServers: connecting to: " + serverIP + ":" + serverPort.toString());
			TTransport transport = new TFramedTransport(new TSocket(serverIP, Integer.valueOf(serverPort), 10000), Integer.MAX_VALUE);
			TProtocol protocol = new TCompactProtocol(transport);
			DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
			boolean value = false;
			try {
				transport.open();
				//LOGGER.info("[notifyOthersDatalayerServers] connected");
				value = datalayer.updateTableTypeCache(action, table, tableType);
				//LOGGER.info("[notifyOthersDatalayerServers] cache update message sent");
				if (value == false) {
					return false;
				}

			} catch (TException e) {
				LOGGER.error("[notifyOthersDatalayerServers] " + e.getMessage());
			} finally {
				if (transport != null) {
					transport.close();
				}
			}
		}
		return true;
	}

	public boolean updateTableTypeCache(String action, String table, String tableType) {
		switch (action) {
			case "put":
				BUCKET_TO_TYPE.put(table, tableType);
				LOGGER.info("updateTableTypeCache: action: put, table: " + table + ", type: " + tableType);
				return true;
			case "remove":
				BUCKET_TO_TYPE.remove(table);
				LOGGER.info("updateTableTypeCache: action: remove, table: " + table + ", type: " + tableType);
				return true;
			default:
				return false;
			}
	}
}
