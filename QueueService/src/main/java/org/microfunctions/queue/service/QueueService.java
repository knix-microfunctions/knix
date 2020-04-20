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
package org.microfunctions.queue.service;

import java.util.Properties;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.microfunctions.queue.local.LocalQueueRunner;

public class QueueService
{
    private String hostname;
    private String hostAddress;
    private int portNumber;
    
    private Thread localQueueThread;
    private LocalQueueRunner localQueueRunner;
    
    private static final Logger LOGGER = LogManager.getLogger(QueueService.class);
    
    public QueueService(Properties config)
    {
        this.hostname = config.get("hostname").toString();
        this.portNumber = Integer.parseInt(config.get("portNumber").toString());
        LOGGER.info("Using config:");
        LOGGER.info("hostname = " + this.hostname);
        LOGGER.info("port number = " + this.portNumber);

        this.localQueueRunner = new LocalQueueRunner(this.portNumber);
        this.localQueueThread = new Thread(this.localQueueRunner);
        this.localQueueThread.start();

    }

    public void shutdown()
    {
        this.localQueueRunner.shutdown();
    }

    public String getHostname()
    {
        return hostname;
    }

    public LocalQueueRunner getLocalQueueRunner()
    {
        return localQueueRunner;
    }

    public String getHostAddress()
    {
        return hostAddress;
    }

}

