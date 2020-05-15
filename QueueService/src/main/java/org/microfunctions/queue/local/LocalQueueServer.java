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
package org.microfunctions.queue.local;

import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.List;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.thrift.TException;
import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.server.TServer;
import org.apache.thrift.server.TThreadPoolServer;
import org.apache.thrift.server.TThreadedSelectorServer;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TServerSocket;
import org.apache.thrift.transport.TServerTransport;
import org.apache.thrift.transport.TTransportException;
import org.microfunctions.queue.local.LocalQueueService.Iface;

public class LocalQueueServer implements Iface, Runnable {
    
    public static final int DEFAULT_MAX_WORKER_THREADS = Integer.MAX_VALUE;
    public static final int DEFAULT_CLIENT_TIMEOUT = 0;
    public static final int DEFAULT_MAX_FRAME_LENGTH = Integer.MAX_VALUE;
    
    private static Logger LOGGER = LogManager.getLogger(LocalQueueServer.class);
    
    private TServer server = null;
    private LocalQueue queue = new LocalQueue();

    private int localQueueServerPort;

    public LocalQueueServer(int lqsp)
    {
    	this.localQueueServerPort = lqsp;
    }

    @Override
    public void addTopic(String topic) throws TException {
        queue.addTopic(topic);
    }

    @Override
    public void removeTopic(String topic) throws TException {
        queue.removeTopic(topic);
    }

    @Override
    public boolean addMessage(String topic, LocalQueueMessage message) throws TException {
        return queue.addMessage(topic, message);
    }

    @Override
    public void addMessageNoack(String topic, LocalQueueMessage message) throws TException {
        queue.addMessage(topic, message);
    }

    @Override
    public LocalQueueMessage getAndRemoveMessage(String topic, long timeout) throws TException {
        return queue.getAndRemoveMessage(topic, timeout);
    }

    @Override
    public List<LocalQueueMessage> getAndRemoveMultiMessages(String topic, int maxCount, long timeout) throws TException {
        if (maxCount < 1) {
            return new ArrayList<LocalQueueMessage>(0);
        }
        
        LocalQueueMessage message = queue.getAndRemoveMessage(topic, timeout);
        if (message.getIndex() == LocalQueue.NO_MESSAGE_INDEX) {
            return new ArrayList<LocalQueueMessage>(0);
        }
        
        List<LocalQueueMessage> messages = new ArrayList<LocalQueueMessage>();
        messages.add(message);
        
        for (int i = 1; i < maxCount; ++i) {
            LocalQueueMessage message1 = queue.getAndRemoveMessage(topic, 0);
            if (message1.getIndex() == LocalQueue.NO_MESSAGE_INDEX) {
                break;
            }
            
            messages.add(message1);
        }
        
        return messages;
    }
    
    @Override
    public LocalQueueMessage getMessage(String topic, long timeout) throws TException {
        return queue.getMessage(topic, timeout);
    }

    @Override
    public long totalMemory() throws TException {
        return Runtime.getRuntime().maxMemory();
    }

    @Override
    public long freeMemory() throws TException {
        return Runtime.getRuntime().maxMemory() - Runtime.getRuntime().totalMemory() + Runtime.getRuntime().freeMemory();
    }
    
    public void start (InetSocketAddress bindAddr, int maxWorkerThreads, int clientTimeout) throws TTransportException {
        TServerTransport transport = new TServerSocket(bindAddr, clientTimeout);
        TThreadPoolServer.Args args = new TThreadPoolServer.Args(transport)
                .transportFactory(new TFramedTransport.Factory(DEFAULT_MAX_FRAME_LENGTH))
                .protocolFactory(new TCompactProtocol.Factory())
                .processor(new LocalQueueService.Processor<Iface>(this))
                .maxWorkerThreads(maxWorkerThreads);
        server = new TThreadPoolServer(args);
        
        LOGGER.info("Starting local queue...");
        server.serve();
    }
    
    public void start (InetSocketAddress bindAddr, int maxWorkerThreads) throws TTransportException {
        this.start(bindAddr, maxWorkerThreads, DEFAULT_CLIENT_TIMEOUT);
    }
    
    public void start (InetSocketAddress bindAddr) throws TTransportException {
        this.start(bindAddr, DEFAULT_MAX_WORKER_THREADS, DEFAULT_CLIENT_TIMEOUT);
    }
    
    public void stop () {
        if (server != null) {
            server.stop();
        }
    }
    
    protected void finalize () throws Throwable {
        try {
            this.stop();
        } finally {
            super.finalize();
        }
    }
    
    public void run()
    {
		try
		{
			InetSocketAddress bindAddr = new InetSocketAddress("0.0.0.0", this.localQueueServerPort);
            this.start(bindAddr);
        }
        catch (TTransportException tte)
        {
            LOGGER.error(tte.getMessage(), tte);
        }
    	
		this.stop();

        LOGGER.info("Stopped local queue.");
    }
}

