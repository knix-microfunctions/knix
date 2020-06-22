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

import java.io.FileInputStream;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.eclipse.jetty.server.Connector;
import org.eclipse.jetty.server.Handler;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.server.handler.ContextHandlerCollection;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.eclipse.jetty.util.thread.QueuedThreadPool;

public class HttpFrontendServer {
	
	private static final Logger logger = LogManager.getLogger(HttpFrontendServer.class);
	
	private Server jettyServer = null;
	private int maxServerThreads = Math.max(50, Math.min(500, 2 * Runtime.getRuntime().availableProcessors()));
	
	public HttpFrontendServer(String httpHost, int httpPort, int httpTimeoutMs,
			String datalayerServerHost, int datalayerServerPort) {
		
		this.jettyServer = new Server(new QueuedThreadPool(maxServerThreads));
		
		ServerConnector httpConnector = new ServerConnector(jettyServer);
		httpConnector.setHost(httpHost);
		httpConnector.setPort(httpPort);
		httpConnector.setIdleTimeout(httpTimeoutMs);
		
		jettyServer.setConnectors(new Connector[] {httpConnector});

		ServletContextHandler httpContextHandler = new ServletContextHandler();
		httpContextHandler.setMaxFormContentSize(Integer.MAX_VALUE);
		httpContextHandler.setMaxFormKeys(Integer.MAX_VALUE);
		httpContextHandler.setContextPath("/");
		httpContextHandler.addServlet(new ServletHolder(new HttpStorageServlet(datalayerServerHost, datalayerServerPort, httpTimeoutMs)), "/storage/*");
		
		ContextHandlerCollection contextHandlers = new ContextHandlerCollection();
		contextHandlers.setHandlers(new Handler[] {httpContextHandler});
		jettyServer.setHandler(contextHandlers);
	}
	
	public void run() {
		try {
			logger.info("Frontend server is starting.");
			jettyServer.start();
			logger.info("Frontend server has started.");
			jettyServer.join();
		} catch (Exception e) {
		    logger.error(e);
		} finally {
			jettyServer.destroy();
		}
	}

	public static void usage(List<String[]> params) {
		System.err.println("You must specify the following " + params.size() + " parameters, either as command line arguments, as system properties, capitalized environment variables or in a java properties file passed as sole command line argument:");
		for (int i = 0; i < params.size(); ++i) {
			System.err.println(Integer.toString(i + 1) + ") " + params.get(i)[0]);
		}
	}
	
	public static void main(String[] args) {
		List<String[]> params = new ArrayList<String[]>();
		params.add(new String[]{"http_host", "0.0.0.0"});
		params.add(new String[]{"http_port", "51000"});
		params.add(new String[]{"http_timeout_ms", "30000"});
		params.add(new String[]{"mfn_datalayer", ""});
		params.add(new String[]{"mfn_datalayer_port", "4998"});
		
		Properties config = new Properties();
		for(String[] entry : params) {
			config.put(entry[0], entry[1]);
		}

		if (args.length == 1) {
			try {
				config.load(new FileInputStream(args[0]));
			} catch (Exception e) {
				System.err.println("Error loading configuration from properties file: " + args[0]);
				HttpFrontendServer.usage(params);
				return;
			}
		} else if (args.length == config.size()) {
			int i = 0;
			for(String[] param : params) {
				config.put(param[0], args[i++]);
			}
		} else if (args.length > 0) {
			HttpFrontendServer.usage(params);
			return;
		} else {
			// Copy properties from env or system props
			Map<String, String> env = System.getenv();
			Properties sys = System.getProperties();
			for(Object key : config.keySet()) {
				String envkey = key.toString().replace('.', '_').toUpperCase();
				if (env.containsKey(envkey))
					config.put(key, env.get(envkey));
				else if (sys.containsKey(key))
					config.put(key, sys.get(key));
			}
		}
		
		if (config.get("mfn_datalayer").toString().isEmpty()) {
			try {
				InetAddress la = InetAddress.getLocalHost();
				config.put("mfn_datalayer", la.getHostAddress());
			} catch (UnknownHostException e) {
				e.printStackTrace();
			}
		} else {
			try {
				while (true) {
					String mfnDatalayer = config.get("mfn_datalayer").toString();
					try {
						InetAddress la = InetAddress.getByName(mfnDatalayer);
						//config.put("mfn_datalayer", la.getHostAddress()); <- don't resolve but use the FQDN instead, just wait until it becomes resolvable
						break;
					} catch (UnknownHostException e) {
						System.err.println("Error resolving " + mfnDatalayer + ", waiting another 5s");
						//e.printStackTrace();
					}
					Thread.sleep(5000);
				}
			} catch (InterruptedException e) {
				System.err.println("Interrupted trying to resolve datalayer host");
			}
		}

		HttpFrontendServer.logger.info("Using configuration:");
		for (String[] param : params) {
			String key = param[0];
			HttpFrontendServer.logger.info("\t" + key + " = " + config.get(key).toString());
		}
		
		new HttpFrontendServer(
				config.get("http_host").toString(), 
				Integer.parseInt(config.get("http_port").toString()), 
				Integer.parseInt(config.get("http_timeout_ms").toString()),
				config.get("mfn_datalayer").toString(),
				Integer.parseInt(config.get("mfn_datalayer_port").toString())
			).run();
	}
}
