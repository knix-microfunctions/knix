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
package org.microfunctions.javaworker.handler;

import java.io.File;
import java.lang.reflect.Method;
import java.net.Socket;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.microfunctions.mfnapi.MicroFunctionsAPI;
import org.newsclub.net.unix.AFUNIXServerSocket;
import org.newsclub.net.unix.AFUNIXSocketAddress;

public class RequestServer implements Runnable
{
    private static final Logger LOGGER = LogManager.getLogger(RequestServer.class);

	private String functionPath;
	private String functionName;
	private String serverSocketFilename;
	
    private Class<?> functionClass;
    private Method functionMethod;

    private ThreadPoolExecutor threadPoolExecutor;
    
    boolean isRunning = false;

	public RequestServer(HashMap<String, String> argsmap)
	{
        LOGGER.debug("Initializing Java request server: " + argsmap.toString());

		this.functionPath = argsmap.get("functionPath");
		this.functionName = argsmap.get("functionName");
		this.serverSocketFilename = argsmap.get("serverSocketFilename");
		
		// get user code/libs and load them
		// jars have been unzipped into a folder, so load all .class files as well as the function code
        try 
        {
        	//ClassLoader classLoader = JavaWorkerMain.class.getClassLoader();
            File path = new File(this.functionPath);
            URL url = path.toURI().toURL();
            URL[] urls = new URL[] {url};
            URLClassLoader classLoader = new URLClassLoader(urls);
            
            int classNameStartIndex = this.functionPath.length();
            if (!this.functionPath.endsWith("/"))
            {
                classNameStartIndex += 1;
            }
            ArrayList<String> classNameList = this.getClassNamesFromFolder(this.functionPath, classNameStartIndex);
            int size = classNameList.size();
            for (int i = 0; i < size; i++)
            {
                String className = classNameList.get(i);
                LOGGER.debug("Loading class: " + className);
                
                if (this.functionName.equalsIgnoreCase(className))
                {
                    LOGGER.debug("Found user class: " + className);
                    functionClass = classLoader.loadClass(className);
                    //function = functionClass.newInstance();
                    functionMethod = functionClass.getDeclaredMethod("handle", Object.class, MicroFunctionsAPI.class);
                }
                else
                {
                    classLoader.loadClass(className);
                }
            }

            classLoader.close();
        } 
        catch (Exception e) 
        {
            LOGGER.error("Problem in loading user code (Exception): " + e);
            System.exit(1);
        }
        catch (Error e)
        {
            LOGGER.error("Problem in loading user code (Error): " + e);
            System.exit(1);
        }
        
		// create a thread pool
        // https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/ThreadPoolExecutor.html
/*        Queuing
        Any BlockingQueue may be used to transfer and hold submitted tasks. The use of this queue interacts 
        with pool sizing:

            1. If fewer than corePoolSize threads are running, the Executor always prefers adding a new thread 
            rather than queuing.
            2. If corePoolSize or more threads are running, the Executor always prefers queuing a request rather 
            than adding a new thread.
            3. If a request cannot be queued, a new thread is created unless this would exceed maximumPoolSize, 
            in which case, the task will be rejected.

        There are three general strategies for queuing:

            1. Direct handoffs. A good default choice for a work queue is a SynchronousQueue that hands off tasks 
            to threads without otherwise holding them. Here, an attempt to queue a task will fail if no threads 
            are immediately available to run it, so a new thread will be constructed. This policy avoids lockups 
            when handling sets of requests that might have internal dependencies. Direct handoffs generally 
            require unbounded maximumPoolSizes to avoid rejection of new submitted tasks. This in turn admits 
            the possibility of unbounded thread growth when commands continue to arrive on average faster than 
            they can be processed.
            2. Unbounded queues. Using an unbounded queue (for example a LinkedBlockingQueue without a predefined 
            capacity) will cause new tasks to wait in the queue when all corePoolSize threads are busy. Thus, no 
            more than corePoolSize threads will ever be created. (And the value of the maximumPoolSize therefore 
            doesn't have any effect.) This may be appropriate when each task is completely independent of others, 
            so tasks cannot affect each others execution; for example, in a web page server. While this style of 
            queuing can be useful in smoothing out transient bursts of requests, it admits the possibility of 
            unbounded work queue growth when commands continue to arrive on average faster than they can be processed.
            3. Bounded queues. A bounded queue (for example, an ArrayBlockingQueue) helps prevent resource exhaustion 
            when used with finite maximumPoolSizes, but can be more difficult to tune and control. Queue sizes and 
            maximum pool sizes may be traded off for each other: Using large queues and small pools minimizes CPU 
            usage, OS resources, and context-switching overhead, but can lead to artificially low throughput. If 
            tasks frequently block (for example if they are I/O bound), a system may be able to schedule time for 
            more threads than you otherwise allow. Use of small queues generally requires larger pool sizes, which 
            keeps CPUs busier but may encounter unacceptable scheduling overhead, which also decreases throughput.
*/

        // _XXX_: use Integer.MAX_VALUE as corePoolSize, so that each request gets a new thread
        // but allow them to be reaped, so that we can reduce resource usage in case there are no requests
        // and if there are requests and we have some idle threads, reuse them
        // this strategy should be better than 
        // 1) a fixed thread pool, because we can reduce the threads to 0 via allowing idle threads to be reaped, 
        // 2) creating a new thread from scratch for each request, because we can reuse already created idle threads
        // TODO: There may be a better strategy with a smaller max num threads, 
        // but need RejectedExecutionHandler to handle rejected task exceeding capacity.
        // or using a different queue type instead of 'direct handoff'
        this.threadPoolExecutor = new ThreadPoolExecutor(Integer.MAX_VALUE, Integer.MAX_VALUE, 300L, TimeUnit.SECONDS, new SynchronousQueue<Runnable>());
        this.threadPoolExecutor.allowCoreThreadTimeOut(true);

	}
	
    private ArrayList<String> getClassNamesFromFolder(String jarFolderPath, int classNameStartIndex)
    {
        ArrayList<String> classNameList = new ArrayList<String>();
         try
         {
             File file = new File(jarFolderPath);
             File[] list = file.listFiles();
             for (int i = 0; i < list.length; i++)
             {
                 File f = list[i];
                 String name = f.getName();
                 if (f.isFile() && name.endsWith(".class"))
                 {
                     name = f.getAbsolutePath().substring(classNameStartIndex).replaceAll(".class", "").replaceAll("/", ".");
                     classNameList.add(name);
                 }
                 else if (f.isDirectory())
                 {
                     classNameList.addAll(getClassNamesFromFolder(f.getPath(), classNameStartIndex));
                 }
             }
         }
         catch (Exception e)
         {
             e.printStackTrace();
         }
         return classNameList;
    }

    private void createThreadAndHandleMessage(Socket socket)
    {
    	//RequestHandler rh = new RequestHandler(socket, this.functionClass, this.function, this.functionMethod);
    	RequestHandler rh = new RequestHandler(socket, this.functionClass, this.functionMethod);
        // _XXX_: what if this task gets rejected? see comments in the constructor for discussion.
        this.threadPoolExecutor.execute(rh);
    }
    
    public void run()
    {
        // start a Unix domain socket server to listen for requests
        this.isRunning = true;
        
        AFUNIXServerSocket requestServerSocket = null;
        try
        {
            LOGGER.info("Waiting for requests on: " + this.serverSocketFilename);
            final File socketFile = new File(this.serverSocketFilename);
        	
        	requestServerSocket = AFUNIXServerSocket.newInstance();
        	requestServerSocket.bind(new AFUNIXSocketAddress(socketFile));
        	
            while (this.isRunning)
            {
            	Socket socket = requestServerSocket.accept();
            	this.createThreadAndHandleMessage(socket);
            	
            }
        }
        catch (Exception e)
        {
            LOGGER.error("Error in listening for requests: " + this.serverSocketFilename + " " + e);
        	System.exit(1);
        }
        
    }
    
    public void shutdown()
    {
        this.isRunning = false;
        this.threadPoolExecutor.shutdown();
        try
        {
            this.threadPoolExecutor.awaitTermination(300, TimeUnit.SECONDS);
        }
        catch (InterruptedException ie)
        {
            
        }
    }
}
