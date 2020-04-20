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
package org.microfunctions.http_frontend;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.thrift.TException;
import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.protocol.TProtocol;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TSocket;
import org.apache.thrift.transport.TTransport;
import org.json.JSONArray;
import org.microfunctions.data_layer.DataLayerService;
import org.microfunctions.data_layer.KeyValuePair;

public class StorageOperations
{
	private static final Logger logger = LogManager.getLogger(StorageOperations.class);
    private static final int DATALAYER_MAX_MESSAGE_LENGTH = Integer.MAX_VALUE;
    //private static final int LOCALITY = DatalayerServer.RIAK_DATALAYER;
    private static final int LOCALITY = 1;

    public static String getData (String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs, 
            String keyspace, String table, String key)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        String value = null;
        try {
            transport.open();
            value = new String(datalayer.selectRow(keyspace, table, key, LOCALITY).getValue(), StandardCharsets.UTF_8);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return value;
    }
    
    public static boolean putData (String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String key, String value)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            success = datalayer.insertRow(keyspace, table, new KeyValuePair(key, ByteBuffer.wrap(value.getBytes(StandardCharsets.UTF_8))), LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }
    
    public static boolean deleteData (String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String key)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            success = datalayer.deleteRow(keyspace, table, key, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }
    
    public static String listKeys (String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, int start, int count)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        List<String> keys = new ArrayList<String>();
        try {
            transport.open();
            keys = datalayer.selectKeys(keyspace, table, start, count, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        JSONArray jsonKeys = new JSONArray(keys);
        return jsonKeys.toString();
    }
    
    public static boolean createMap(String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String mapName)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            success = datalayer.createMap(keyspace, table, mapName, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }
    
    public static boolean putEntryToMap(String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String mapName, String key, String value)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            KeyValuePair kvp = new KeyValuePair(key, ByteBuffer.wrap(value.getBytes(StandardCharsets.UTF_8)));
            success = datalayer.putEntryToMap(keyspace, table, mapName, kvp, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }
    
    public static boolean createSet(String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String setName)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            success = datalayer.createSet(keyspace, table, setName, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }

    public static boolean addItemToSet(String datalayerServerHost, int datalayerServerPort, int continuationTimeoutMs,
            String keyspace, String table, String setName, String setItem)
    {
        TTransport transport = new TFramedTransport(new TSocket(datalayerServerHost, datalayerServerPort, continuationTimeoutMs), DATALAYER_MAX_MESSAGE_LENGTH);
        TProtocol protocol = new TCompactProtocol(transport);
        DataLayerService.Client datalayer = new DataLayerService.Client(protocol);
        
        boolean success = false;
        try {
            transport.open();
            success = datalayer.addItemToSet(keyspace, table, setName, setItem, LOCALITY);
        } catch (TException e) {
            logger.error("[StorageOperation] " + e.getMessage(), e);
        } finally {
            if (transport != null) {
                transport.close();
            }
        }
        return success;
    }
}