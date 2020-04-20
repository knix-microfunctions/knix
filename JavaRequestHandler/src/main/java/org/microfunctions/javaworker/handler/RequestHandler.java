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

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.lang.reflect.Method;
import java.net.Socket;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.json.JSONObject;
import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class RequestHandler implements Runnable
{
    private static final Logger LOGGER = LogManager.getLogger(RequestHandler.class);

	private Socket clientSocket;
	private Class<?> functionClass;
	private Object function;
	private Method functionMethod;
	
	private String key;
	private Object event;
	private MicroFunctionsAPI context;
	
	public RequestHandler(Socket cs, Class<?> functionClass, Method functionMethod)
	{
		this.clientSocket = cs;
		this.functionClass = functionClass;
		try
		{
			this.function = this.functionClass.newInstance();
		}
		catch (Exception e)
		{
			LOGGER.error(e);
		}
		this.functionMethod = functionMethod;
	}
			
	public void run()
	{
		// get key, event and APIServerSocketFilename from the clientSocket
        boolean hasError = false;
        String errorType = "";
        StringBuilder errorTrace = new StringBuilder();

        LOGGER.debug("Attempting to get request parameters...");

        DataInputStream din = null;
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        String serializedData = "";
		try
		{
			din = new DataInputStream(new BufferedInputStream(this.clientSocket.getInputStream()));
			
			// read the input fully and deserialize it
			byte[] buffer = new byte[4096];
			int n = 0;
			while ((n = din.read(buffer)) > -1)
			{
				baos.write(buffer, 0, n);
			}
            serializedData = baos.toString();
		}
		catch (Exception e)
		{
		    LOGGER.error("Error in reading event input data.");
			hasError = true;
			errorType = "Error in reading event input data.";
		}
		
		if (!hasError)
		{
            LOGGER.debug("New request: " + serializedData.substring(0, Math.min(256, serializedData.length())));
    		// establish API socket connection with given information, then call user code
    		try
    		{
    			JSONObject obj = new JSONObject(serializedData);
    			this.key = obj.getString("key");
    			this.event = obj.get("event");
    			String APIServerSocketFilename = obj.getString("APIServerSocketFilename");
    			// create an 'API object' that is a wrapper with a Unix domain socket connected to the API server
    			this.context = new MicroFunctionsAPI(APIServerSocketFilename);
    			if (this.context.hasError())
    			{
    			    hasError = true;
    			    errorType = "Error in creating API object.";
    			}
    		}
    		catch (Exception e)
    		{
    		    LOGGER.error("Error in parsing event input data: " + serializedData + " " + e);
    			hasError = true;
    			errorType = "Error in parsing event input data.";
    		}
		}

        Object functionResult = null;
		if (!hasError)
		{
            try
            {
                functionResult = this.functionMethod.invoke(this.function, this.event, this.context);
                LOGGER.debug("[ExecutionId] [" + this.key + "]"
                        + " [Result] [" + functionResult.toString().substring(0, Math.min(256, functionResult.toString().length())) + "]");
            }
            catch (Exception e)
            {
                Throwable cause = e.getCause();
                StackTraceElement[] stelist = cause.getStackTrace();
                for (int i = 0; i < stelist.length; i++)
                {
                    errorTrace.append(stelist[i] + "\n");
                }
                hasError = true;
                errorType = cause.getMessage();
                if (errorType == null)
                {
                    errorType = cause.toString();
                }
                LOGGER.error("Problem in user code (Exception): " + errorType);
            }
            catch (Error e)
            {
                Throwable cause = e.getCause();
                StackTraceElement[] stelist = cause.getStackTrace();
                for (int i = 0; i < stelist.length; i++)
                {
                    errorTrace.append(stelist[i] + "\n");
                }
                hasError = true;
                errorType = cause.getMessage();
                if (errorType == null)
                {
                    errorType = cause.toString();
                }
                LOGGER.error("Problem in user code (Error): " + errorType);
            }
		}
        
        // serialize output and send out to API server for post-processing
        FunctionExecutionResult fer = new FunctionExecutionResult(this.key, functionResult, hasError, errorType, errorTrace);
        
        DataOutputStream out = null;
        try
        {
        	out = new DataOutputStream(this.clientSocket.getOutputStream());
        	
        	out.write(fer.toString().getBytes());
        	out.flush();
        	out.close();
        	this.clientSocket.close();
        	LOGGER.debug("Successfully sent result: [" + this.key + "]");
        }
        catch (Exception e)
        {
            errorTrace = new StringBuilder();
            StackTraceElement[] stelist = e.getStackTrace();
            for (int i = 0; i < stelist.length; i++)
            {
                errorTrace.append(stelist[i] + "\n");
            }
            LOGGER.error("Error in sending function result: " + key + " " + errorTrace.toString());
        }
        
        // close the API server connection
        context.close();
        
	}
}

