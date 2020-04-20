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

import java.io.FileInputStream;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Map;
import java.util.Properties;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class MainQueueService
{
    private static final Logger LOGGER = LogManager.getLogger(QueueService.class);

    public static void usage() {
		System.err.println("Usage: please provide configuration options either \n"
				+ " in a properties file as first argument\n"
				+ " or as environment variables\n"
				+ " or as Java system properties\n");
		String hostname = "<undetectable>";
		try {
			InetAddress.getLocalHost().getHostName();
		} catch(UnknownHostException e) {
			LOGGER.warn("Hostname can't be detected");
		}
		System.err.println("OPTIONS:\n"
				+ " - hostname (HOSTNAME)\t<fqdn>\t(default: "+hostname+"\n");
	}

    public static void main(String[] args)
    {
		Properties config = new Properties();
		if (args.length == 1) {
			try {
				config.load(new FileInputStream(args[0]));
			} catch (Exception e) {
				System.err.println("Error loading configuration from properties file: "+args[0]);
				MainQueueService.usage();
				return;
			}
		} else {
			// Copy properties from env or system props
			Map<String,String> env = System.getenv();
			Properties sys = System.getProperties();
			for(String key : new String[]{"hostname", "portNumber"}) {
				String envkey = key.replace('.', '_').toUpperCase();
				if(env.containsKey(envkey))
					config.put(key,env.get(envkey));
				else if(sys.containsKey(key))
					config.put(key, sys.get(key));
			}
		}
		InetAddress addr;
		try {
			if(!config.containsKey("hostname")) {
				addr = InetAddress.getLocalHost();
			} else {
				addr = InetAddress.getByName(config.getProperty("hostname"));
			}
			LOGGER.debug(addr.getHostName() + " " + addr.getHostAddress());
			config.put("hostname", addr.getHostName());
		} catch (Exception e) {
			LOGGER.error(e.getMessage(), e);
			System.exit(1);
		}

		// default port number
		int portNumber = 4999;
		if (!config.containsKey("portNumber"))
		{
			config.put("portNumber", "" + portNumber);
		}

		final QueueService qs = new QueueService(config);
        
        Runtime.getRuntime().addShutdownHook(new Thread() {
             @Override
             public void run() {
                LOGGER.info("Shutting down queue service...");
                qs.shutdown();
             }
          });
        
    }
}
