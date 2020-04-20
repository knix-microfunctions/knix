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

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.thrift.transport.TTransportException;

public class LocalQueueRunner implements Runnable
{
    private LocalQueueServer server;
    private int localQueueServerPort;
    
    private InetSocketAddress bindAddr;

    private static Logger LOGGER = LogManager.getLogger(LocalQueueRunner.class);
    
    public LocalQueueRunner(int lqsp)
    {
        this.localQueueServerPort = lqsp;

        this.server = new LocalQueueServer();
    
    }
    
    public void run()
    {
		try
		{
			this.bindAddr = new InetSocketAddress("0.0.0.0", this.localQueueServerPort);
            this.server.start(bindAddr);
        }
        catch (TTransportException tte)
        {
            LOGGER.error(tte.getMessage(), tte);
        }
    	
        if (this.server != null)
        {
            this.server.stop();
        }

        LOGGER.info("Stopped local queue.");
    }
    
    public void shutdown()
    {
        if (this.server != null)
        {
            this.server.stop();
            this.server = null;
        }
    }
}
