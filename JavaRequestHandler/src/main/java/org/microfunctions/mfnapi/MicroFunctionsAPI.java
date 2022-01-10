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
package org.microfunctions.mfnapi;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.thrift.protocol.TCompactProtocol;
import org.apache.thrift.protocol.TProtocol;
import org.apache.thrift.transport.TFramedTransport;
import org.apache.thrift.transport.TSocket;
import org.apache.thrift.transport.TTransport;
import org.apache.thrift.transport.TTransportException;
import org.newsclub.net.unix.AFUNIXSocket;
import org.newsclub.net.unix.AFUNIXSocketAddress;

import org.json.JSONObject;

class LambdaCognitoIdentity
{
	String cognitoIdentityId;
	String cognitoIdentityPoolId;
}

class LambdaClientContextMobileClient
{
	String installationId;
	String appTitle;
	String appVersionName;
	String appVersionCode;
	String appPackageName;
}

class LambdaClientContext
{
	LambdaClientContextMobileClient client = new LambdaClientContextMobileClient();
	HashMap<String, Object> custom = new HashMap<String, Object>();
	HashMap<String, Object> env = new HashMap<String, Object>();
}

public class MicroFunctionsAPI
{
    private static final Logger LOGGER = LogManager.getLogger(MicroFunctionsAPI.class);

	private String APISocketFilename;
	private AFUNIXSocket APISocket = null;
	private TTransport transport = null;
	private MicroFunctionsAPIService.Client mfnapiClient = null;
	
	// Context object properties
	private String functionName;
	private int functionVersion;
	private String invokedFunctionArn;
	private int memoryLimitInMB;
	private String awsRequestId;
	private String logGroupName;
	private String logStreamName;
	
	private LambdaCognitoIdentity identity;
	private LambdaClientContext clientContext;
	
	private Logger logger = this.LOGGER;

	private boolean hasError;
	
	private boolean connected = false;
	private boolean contextInited = false;
	
	public MicroFunctionsAPI(String APISocketFilename)
	{
		this.APISocketFilename = APISocketFilename;
		this.hasError = false;

        LOGGER.debug("API server at: " + this.APISocketFilename);
        
	}
	
	private void initConnection()
	{
		if (this.connected)
		{
			return;
		}
		
        final File APISocketFile = new File(this.APISocketFilename);

        try
        {
            this.APISocket = AFUNIXSocket.newInstance();
        }
        catch (IOException ioe)
        {
            LOGGER.error("Could not open socket: " + ioe);
            this.hasError = true;
        }
        catch (Exception e)
        {
            LOGGER.error("Problem in socket creation: " + e);
            this.hasError = true;
        }

        boolean connected = false;
        while (!connected && !this.hasError)
        {
            try
            {
                this.APISocket.connect(new AFUNIXSocketAddress(APISocketFile));
                connected = true;
            }
            catch (IOException ioe)
            {
                LOGGER.error("Could not connect to API server; it's probably not ready yet.");
            }
            catch (Exception e)
            {
                LOGGER.error("Could not connect to API server: " + this.APISocketFilename);
                this.hasError = true;
            }
            
            try
            {
                Thread.sleep(500);
            }
            catch(Exception e)
            {
            }
        }

        if (!this.hasError)
        {
            LOGGER.debug("Connected to API server: "+ this.APISocketFilename);
    
            try
            {
                int maxMessageLength = Integer.MAX_VALUE;
                this.transport = new TFramedTransport(new TSocket(APISocket), maxMessageLength);
                TProtocol protocol = new TCompactProtocol(transport);
                this.mfnapiClient = new MicroFunctionsAPIService.Client(protocol);
                this.connected = true;
            }
            catch (TTransportException tte)
            {
                this.hasError = true;
                LOGGER.error("Error in initializing API connection: " + this.APISocketFilename + " " + tte);
            }
        }        
	}
	
	private void initContextObjectProperties()
	{
		if (this.contextInited)
		{
			return;
		}

		this.initConnection();

        // obtain the context object properties
		JSONObject jobj = null;
        if (!this.hasError)
        {
        	LOGGER.debug("Obtaining the context object properties...");
        	try
        	{
        		String objectPropertiesStr = this.mfnapiClient.get_context_object_properties();
        		jobj = new JSONObject(objectPropertiesStr);
        	}
        	catch (Exception te)
        	{
        		this.hasError = true;
        		LOGGER.error("Error obtaining the context object properties: " + this.APISocketFilename + " " + te);
        	}
        }

        if (!this.hasError)
        {
			// parse the object and initialize the parameters in Java
			this.functionName = jobj.getString("function_name");
			this.functionVersion = jobj.getInt("function_version");
			this.invokedFunctionArn = jobj.getString("invoked_function_arn");
			this.memoryLimitInMB = jobj.getInt("memory_limit_in_mb");
			this.awsRequestId = jobj.getString("aws_request_id");
			this.logGroupName = jobj.getString("log_group_name");
			this.logStreamName = jobj.getString("log_stream_name");
			
			this.identity = new LambdaCognitoIdentity();
			JSONObject jobjIdentity = jobj.getJSONObject("identity");
			this.identity.cognitoIdentityId = jobjIdentity.getString("cognito_identity_id");
			this.identity.cognitoIdentityPoolId = jobjIdentity.getString("cognito_identity_pool_id");
			
			this.clientContext = new LambdaClientContext();
			JSONObject jobjClientContext = jobj.getJSONObject("client_context");
			JSONObject jobjClient = jobjClientContext.getJSONObject("client");
			this.clientContext.client.installationId = jobjClient.getString("installation_id");
			this.clientContext.client.appTitle = jobjClient.getString("app_title");
			this.clientContext.client.appVersionName = jobjClient.getString("app_version_name");
			this.clientContext.client.appVersionCode = jobjClient.getString("app_version_code");
			this.clientContext.client.appPackageName = jobjClient.getString("app_package_name");
			
			JSONObject custom = jobjClientContext.getJSONObject("custom");
			for (String key: custom.keySet())
			{
				this.clientContext.custom.put(key, custom.get(key));
			}
			
			JSONObject env = jobjClientContext.getJSONObject("env");
			for (String key: env.keySet())
			{
				this.clientContext.env.put(key, env.get(key));
			}
			
			this.contextInited = true;
        }
	}
	
	public boolean hasError()
	{
	    return this.hasError;
	}
	
	public void close()
	{
		try
		{
		    if (this.transport != null)
		    {
		        this.transport.close();
	            //this.APISocket.close();
		        this.transport = null;
		    }
		}
		catch (Exception e)
		{
			LOGGER.error("Error in closing API server connection: " + e);
		}
	}
	/*
    Not needed and thus not implemented because the management service is written in Python.
    def get_privileged_data_layer_client(self, suid=None, sid=None, init_tables=False, drop_keyspace=False):
    
    */
	
	/**
	 * Update the metadata that can be passed to other function instances and other components (e.g., recovery manager (not yet implemented)).
	 * 
	 * @param metadataName the key of the metadata to update
	 * @param metadataValue the value of the metadata
	 * 
	**/
    public void updateMetadata(String metadataName, String metadataValue)
	{
	    this.updateMetadata(metadataName, metadataValue, false);
	}
	
	/**
	 * Update the metadata that can be passed to other function instances and other components (e.g., recovery manager (not yet implemented)).
	 * 
	 * @param metadataName the key of the metadata to update
	 * @param metadataValue the value of the metadata
	 * @param isPrivilegedMetadata whether the metadata is privileged belonging to the management service
	**/
	public void updateMetadata(String metadataName, String metadataValue, boolean isPrivilegedMetadata)
	{
		this.initConnection();
	    
		try
	    {
	        this.mfnapiClient.update_metadata(metadataName, metadataValue, isPrivilegedMetadata);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (updateMetadata): " + e);
	    }
	}
	
	/**
	 * Send a message to all long-running session function instances in this session.
	 * 
	 * @param message the message to be sent.
	 * 
	 * <b>Note:</b> The usage of this method is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 */
	public void sendToAllRunningFunctionsInSession(Object message)
	{
	    this.sendToAllRunningFunctionsInSession(message, false);
	}
	
	/**
	 * Send a message to all long-running session function instances in this session.
	 * 
	 * @param message the message to be sent; can be HashMap, ArrayList, String, int, float or null.
	 * @param sendNow whether the message should be sent immediately or at the end of current function's execution; default: False.
	 * 
	 * <b>Note:</b> The usage of this method is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 */
	public void sendToAllRunningFunctionsInSession(Object message, boolean sendNow)
	{
		this.initConnection();
        
		FunctionAPIMessage fam = new FunctionAPIMessage(message);
        String encodedMessage = fam.toString();
	    try
	    {
	        this.mfnapiClient.send_to_all_running_functions_in_session(encodedMessage, sendNow);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (sendToAllRunningFunctionsInSession): " + e);
	    }
	}

	/**
	 * Send a message to all long-running session function instances identified with their function name in this session.
	 * There can be multiple instances with the same function name, which will all receive the message.
	 * The function name refers to the function name;
	 * it is not to be confused with the 'alias' that may have been assigned to each long-running, session function instance.
	 * 
	 * @param name the function name of the running long-running session function instance(s).
	 * @param message the message to be sent.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 */
	public void sendToAllRunningFunctionsInSessionWithFunctionName(String name, Object message)
	{
	    this.sendToAllRunningFunctionsInSessionWithFunctionName(name, message, false);
	}

	/**
	 * Send a message to all long-running session function instances identified with their function name in this session.
	 * There can be multiple instances with the same function name, which will all receive the message.
	 * The function name refers to the function name;
	 * it is not to be confused with the 'alias' that may have been assigned to each long-running, session function instance.
	 * 
	 * @param name the function name of the running long-running session function instance(s).
	 * @param message the message to be sent.
	 * @param sendNow whether the message should be sent immediately or at the end of current function's execution; default: False.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 */
	public void sendToAllRunningFunctionsInSessionWithFunctionName(String name, Object message, boolean sendNow)
	{
		this.initConnection();
        
		FunctionAPIMessage fam = new FunctionAPIMessage(message);
        String encodedMessage = fam.toString();
	    try
	    {
	        this.mfnapiClient.send_to_all_running_functions_in_session_with_function_name(name, encodedMessage, sendNow);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (sendToAllRunningFunctionsInSessionWithFunctionName): " + e);
	    }
	}
	
    /**
     * Send a message to a long-running session function instance identified with its alias in this session.
     * The alias would have to be assigned before calling this function.
     * The alias can belong to only a single long-running, session function instance.
     * 
     * @param alias the alias of the running long-running session function instance that is the destination of the message.
     * @param message the message to be sent.
     * 
     * <b>Note:</b>
     * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
     * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
     */
    public void sendToRunningFunctionInSessionWithAlias(String alias, Object message)
    {
        this.sendToRunningFunctionInSessionWithAlias(alias, message, false);
    }

    /**
     * Send a message to a long-running session function instance identified with its alias in this session.
     * The alias would have to be assigned before calling this function.
     * The alias can belong to only a single long-running, session function instance.
     * 
     * @param alias the alias of the running long-running session function instance that is the destination of the message.
     * @param message the message to be sent.
     * @param sendNow whether the message should be sent immediately or at the end of current function's execution.
     * 
     * <b>Note:</b>
     * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
     * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
     */
    public void sendToRunningFunctionInSessionWithAlias(String alias, Object message, boolean sendNow)
    {
		this.initConnection();
        
		FunctionAPIMessage fam = new FunctionAPIMessage(message);
        String encodedMessage = fam.toString();
        try
        {
            this.mfnapiClient.send_to_running_function_in_session_with_alias(alias, encodedMessage, sendNow);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (sendToRunningFunctionInSessionWithAlias): " + e);
        }
    }

    /**
     * Send a message to a long-running session function instance identified with its id in this session.
     * 
     * @param sessionFunctionId the running long-running session function instance's id.
     * @param message the message to be sent
     * 
     * <b>Note:</b>
     * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
     * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
     */
    public void sendToRunningFunctionInSession(String sessionFunctionId, Object message)
	{
	    this.sendToRunningFunctionInSession(sessionFunctionId, message, false);
	}
	
    /**
     * Send a message to a long-running session function instance identified with its id in this session.
     * 
     * @param sessionFunctionId the running long-running session function instance's id.
     * @param message the message to be sent
     * @param sendNow whether the message should be sent immediately or at the end of current function's execution.
     * 
     * <b>Note:</b>
     * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
     * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
     */
	public void sendToRunningFunctionInSession(String sessionFunctionId, Object message, boolean sendNow)
	{
		this.initConnection();

		FunctionAPIMessage fam = new FunctionAPIMessage(message);
        String encodedMessage = fam.toString();
	    try
	    {
	        this.mfnapiClient.send_to_running_function_in_session(sessionFunctionId, encodedMessage, sendNow);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (sendToRunningFunctionInSession): " + e);
	    }
	}
	
	/**
	 * Retrieve the list of update messages sent to a session function instance.
	 * The list contains messages that were sent and delivered since the last time the session function instance has retrieved it.
	 * These messages are retrieved via a local queue. There can be more than one message.
	 * By default, it returns only one message and does not block until that message is available.
	 * 
	 * @return list of messages that were sent to the session function instance.
	 * 
	 * <b>Warns:</b>
	 * When the calling function is not a session function.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 * 
	 */
	public List<String> getSessionUpdateMessages()
	{
		return this.getSessionUpdateMessages(1, false);
	}
	
	/**
	 * Retrieve the list of update messages sent to a session function instance.
	 * The list contains messages that were sent and delivered since the last time the session function instance has retrieved it.
	 * These messages are retrieved via a local queue. There can be more than one message.
	 * The optional count argument specifies how many messages should be retrieved.
	 * If there are fewer messages than the requested count, all messages will be retrieved and returned.
	 * 
	 * @param count the number of messages to retrieve
	 * 
	 * @return list of messages that were sent to the session function instance.
	 * 
	 * <b>Warns:</b>
	 * When the calling function is not a session function.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 * 
	 */
	public List<String> getSessionUpdateMessages(int count)
	{
	    return this.getSessionUpdateMessages(count, false);
	}

	/**
	 * Retrieve the list of update messages sent to a session function instance.
	 * The list contains messages that were sent and delivered since the last time the session function instance has retrieved it.
	 * These messages are retrieved via a local queue. There can be more than one message.
	 * 
	 * @param block whether it should block until a message has been received.
	 * 
	 * @return list of messages that were sent to the session function instance.
	 * 
	 * <b>Warns:</b>
	 * When the calling function is not a session function.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 * 
	 */
	public List<String> getSessionUpdateMessages(boolean block)
	{
	    return this.getSessionUpdateMessages(1, block);
	}
	
	/**
	 * Retrieve the list of update messages sent to a session function instance.
	 * The list contains messages that were sent and delivered since the last time the session function instance has retrieved it.
	 * These messages are retrieved via a local queue. There can be more than one message.
	 * The optional count argument specifies how many messages should be retrieved.
	 * If there are fewer messages than the requested count, all messages will be retrieved and returned.
	 * 
	 * @param count the number of messages to retrieve
     * @param block whether it should block until count number of messages have been received
	 * 
	 * @return list of messages that were sent to the session function instance.
	 * 
	 * <b>Warns:</b>
	 * When the calling function is not a session function.
	 * 
	 * <b>Note:</b>
	 * The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
	 * Using a KNIX-specific feature might make the workflow description incompatible with other platforms.
	 * 
	 */
	public List<String> getSessionUpdateMessages(int count, boolean block)
	{
		this.initConnection();

		List<String> msglist = null;
	    try
	    {
	        List<String> msglist2 = this.mfnapiClient.get_session_update_messages(count, block);
	        msglist = new ArrayList<String>();
	        int size = msglist2.size();
	        for (int i = 0; i < size; i++)
	        {
	        	FunctionAPIMessage fam = new FunctionAPIMessage((String) msglist2.get(i));
	        	msglist.add((String) fam.getValue());
	        }
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionUpdateMessages): " + e);
	    }
	    return msglist;
	}

	public void createCounter(String countername, long count)
	{
	    this.createCounter(countername, count, false, false);
	}
	
	public void createCounter(String countername, long count, boolean isPrivate)
	{
	    this.createCounter(countername, count, isPrivate, false);
	}
	
	public void createCounter(String countername, long count, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

		try
	    {
	        this.mfnapiClient.createCounter(countername, count, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (createCounter): " + e);
	    }
	}
	
	public long getCounterValue(String countername)
	{
	    return this.getCounterValue(countername, false);
	}
	
	public long getCounterValue(String countername, boolean isPrivate)
	{
		this.initConnection();

	    long count = 0l;
	    try
	    {
	        count = this.mfnapiClient.getCounterValue(countername, isPrivate);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getCounterValue): " + e);
	    }
	    return count;
	}
	
	public boolean incrementCounter(String countername, long increment)
	{
	    return this.incrementCounter(countername, increment, false, false);
	}
	
	public boolean incrementCounter(String countername, long increment, boolean isPrivate)
	{
	    return this.incrementCounter(countername, increment, isPrivate, false);
	}
	
	public boolean incrementCounter(String countername, long increment, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

        boolean status = false;
	    try
	    {
	        status = this.mfnapiClient.incrementCounter(countername, increment, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (incrementCounter): " + e);
	    }
	    return status;
	}
	
	public boolean decrementCounter(String countername, long decrement)
	{
	    return this.decrementCounter(countername, decrement, false, false);
	}

	public boolean decrementCounter(String countername, long decrement, boolean isPrivate)
	{
	    return this.decrementCounter(countername, decrement, isPrivate, false);
	}

	public boolean decrementCounter(String countername, long decrement, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

        boolean status = false;
	    try
	    {
	        status = this.mfnapiClient.decrementCounter(countername, decrement, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (decrementCounter): " + e);
	    }
	    return status;
	}

    public void deleteCounter(String countername)
    {
        this.deleteCounter(countername, false, false);
    }
    
    public void deleteCounter(String countername, boolean isPrivate)
    {
        this.deleteCounter(countername, isPrivate, false);
    }
    
    public void deleteCounter(String countername, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();

        try
        {
            this.mfnapiClient.deleteCounter(countername, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (deleteCounter): " + e);
        }
    }
    
    public List<String> getCounterNames()
    {
        return this.getCounterNames(0, 2147483647, false);
    }
    
    public List<String> getCounterNames(boolean isPrivate)
    {
        return this.getCounterNames(0, 2147483647, isPrivate);
    }
    
    public List<String> getCounterNames(int startIndex)
    {
        return this.getCounterNames(startIndex, 2147483647, false);
    }
    
    public List<String> getCounterNames(int startIndex, int endIndex)
    {
        return this.getCounterNames(startIndex, endIndex, false);
    }
    
    public List<String> getCounterNames(int startIndex, int endIndex, boolean isPrivate)
    {
		this.initConnection();

        List<String> names = null;
        try
        {
            names = this.mfnapiClient.getCounterNames(startIndex, endIndex, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getCounterNames): " + e);
        }
        return names;
    }

    public void createSet(String setname)
	{
	    this.createSet(setname, false, false);
	}

	public void createSet(String setname, boolean isPrivate)
	{
	    this.createSet(setname, isPrivate, false);
	}

	public void createSet(String setname, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.createSet(setname, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (createSet): " + e);
	    }
	}
	
	public void addSetEntry(String setname, String item)
	{
	    this.addSetEntry(setname, item, false, false);
	}
	
	public void addSetEntry(String setname, String item, boolean isPrivate)
	{
	    this.addSetEntry(setname, item, isPrivate, false);
	}
	
	public void addSetEntry(String setname, String item, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.addSetEntry(setname, item, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (addSetEntry): " + e);
	    }
	}
	
	public void removeSetEntry(String setname, String item)
	{
	    this.removeSetEntry(setname, item, false, false);
	}
	
	public void removeSetEntry(String setname, String item, boolean isPrivate)
	{
	    this.removeSetEntry(setname, item, isPrivate, false);
	}
	
	public void removeSetEntry(String setname, String item, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.removeSetEntry(setname, item, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (removeSetEntry): " + e);
	    }
	}
	
	public boolean containsSetItem(String setname, String item)
	{
	    return this.containsSetItem(setname, item, false);
	}
	
	public boolean containsSetItem(String setname, String item, boolean isPrivate)
	{
		this.initConnection();

	    boolean res = false;
	    try
	    {
	        res = this.mfnapiClient.containsSetItem(setname, item, isPrivate);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (containsSetItem): " + e);
	    }
	    return res;
	}
	
	public Set<String> retrieveSet(String setname)
	{
	    return this.retrieveSet(setname, false);
	}
	
	public Set<String> retrieveSet(String setname, boolean isPrivate)
	{
		this.initConnection();

	    Set<String> set = null;
	    try
	    {
	        set = this.mfnapiClient.retrieveSet(setname, isPrivate);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (retrieveSet): " + e);
	    }
	    return set;
	}
	
	public void clearSet(String setname)
	{
	    this.clearSet(setname, false, false);
	}
	
	public void clearSet(String setname, boolean isPrivate)
	{
	    this.clearSet(setname, isPrivate, false);
	}
	
	public void clearSet(String setname, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.clearSet(setname, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (clearSet): " + e);
	    }
	}
	
	public void deleteSet(String setname)
	{
	    this.deleteSet(setname, false, false);
	}

	public void deleteSet(String setname, boolean isPrivate)
	{
	    this.deleteSet(setname, isPrivate, false);
	}
	
	public void deleteSet(String setname, boolean isPrivate, boolean isQueued)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.deleteSet(setname, isPrivate, isQueued);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (deleteSet): " + e);
	    }
	}
	
    public List<String> getSetNames()
    {
        return this.getSetNames(0, 2147483647, false);
    }
    
    public List<String> getSetNames(boolean isPrivate)
    {
        return this.getSetNames(0, 2147483647, isPrivate);
    }
    
    public List<String> getSetNames(int startIndex)
    {
        return this.getSetNames(startIndex, 2147483647, false);
    }
    
    public List<String> getSetNames(int startIndex, int endIndex)
    {
        return this.getSetNames(startIndex, endIndex, false);
    }
    
    public List<String> getSetNames(int startIndex, int endIndex, boolean isPrivate)
    {
		this.initConnection();

        List<String> names = null;
        try
        {
            names = this.mfnapiClient.getSetNames(startIndex, endIndex, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getSetNames): " + e);
        }
        return names;
    }
	
	public String ping(int num)
	{
		this.initConnection();

		try
		{
			long t_api_call = System.currentTimeMillis();
			String response1 = this.mfnapiClient.ping(num);
			t_api_call = System.currentTimeMillis() - t_api_call;
			LOGGER.debug("API ping() call duration: " + t_api_call + " ms");
			return response1;
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (ping): " + e);
		}
		return null;
	}
	
	public List<Map<String, String>> getDynamicWorkflow()
	{
		this.initConnection();

	    List<Map<String, String>> dynamicWorkflow = null;
	    try
	    {
	        dynamicWorkflow = this.mfnapiClient.get_dynamic_workflow();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getDynamicWorkflow): " + e);
	    }
	    return dynamicWorkflow;
	}
	
	public String getSessionFunctionIdWithAlias()
	{
	    return this.getSessionFunctionIdWithAlias(null);
	}
	
	public String getSessionFunctionIdWithAlias(String alias)
	{
		this.initConnection();

	    String sessionFunctionId = "";
	    try
	    {
	        sessionFunctionId = this.mfnapiClient.get_session_function_id_with_alias(alias);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionFunctionIdWithAlias): " + e);
	    }
	    return sessionFunctionId;
	}
	
	public List<String> getAllSessionFunctionIds()
	{
		this.initConnection();

	    List<String> idList = null;
	    try
	    {
	        idList = this.mfnapiClient.get_all_session_function_ids();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getAllSessionFunctionIds): " + e);
	    }
	    return idList;
	}
	
	public Map<String, String> getAllSessionFunctionAliases()
	{
		this.initConnection();

	    Map<String, String> aliasMap = null;
	    try
	    {
	        aliasMap = this.mfnapiClient.get_all_session_function_aliases();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getAllSessionFunctionAliases): " + e);
	    }
	    return aliasMap;
	}
	
	public Map<String, Map<String, String>> getAliasSummary()
	{
		this.initConnection();

	    Map<String, Map<String, String>> aliasMap = null;
	    try
	    {
	        aliasMap = this.mfnapiClient.get_alias_summary();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getAliasSummary): " + e);
	    }
	    return aliasMap;
	}
	
	public boolean isStillRunning()
	{
		this.initConnection();

	    boolean running = false;
	    try
	    {
	        running = this.mfnapiClient.is_still_running();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (isStillRunning): " + e);
	    }
	    return running;
	}
	
	public String getEventKey()
	{
		this.initConnection();

	    String key = "";
	    try
	    {
	        key = this.mfnapiClient.get_event_key();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getEventKey): " + e);
	    }
	    return key;
	}
	
	public String getInstanceId()
	{
		this.initConnection();

	    String key = "";
	    try
	    {
	        key = this.mfnapiClient.get_instance_id();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getInstanceId): " + e);
	    }
	    return key;
	}
	
	public long getRemainingTimeInMillis()
	{
		this.initConnection();

	    long t = 0l;
	    try
	    {
	        t = this.mfnapiClient.get_remaining_time_in_millis();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getRemainingTimeInMillis): " + e);
	    }
	    return t;
	}
	
	public String getSessionId()
	{
		this.initConnection();

	    String sessionId = "";
	    try
	    {
	        sessionId = this.mfnapiClient.get_session_id();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionId): " + e);
	    }
	    return sessionId;
	}
	
	public String getSessionFunctionId()
	{
		this.initConnection();

	    String sessionFunctionId = "";
	    try
	    {
	        sessionFunctionId = this.mfnapiClient.get_session_function_id();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionFunctionId): " + e);
	    }
	    return sessionFunctionId;
	}
	
	public void setSessionAlias(String alias)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.set_session_alias(alias);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (setSessionAlias): " + e);
	    }
	}
	
	public void unsetSessionAlias()
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.unset_session_alias();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (unsetSessionAlias): " + e);
	    }
	}
	
	public String getSessionAlias()
	{
		this.initConnection();

	    String alias = "";
	    try
	    {
	        alias = this.mfnapiClient.get_session_alias();
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionAlias): " + e);
	    }
	    return alias;
	}
	
	public void setSessionFunctionAlias(String alias)
	{
	    this.setSessionFunctionAlias(alias, null);
	}
	
	public void setSessionFunctionAlias(String alias, String sessionFunctionId)
	{
		this.initConnection();

	    try
	    {
	        this.mfnapiClient.set_session_function_alias(alias, sessionFunctionId);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (setSessionFunctionAlias): " + e);
	    }
	}
	
	public void unsetSessionFunctionAlias()
	{
	    this.unsetSessionFunctionAlias(null);
	}
	
	public void unsetSessionFunctionAlias(String sessionFunctionId)
	{
		this.initConnection();
	    
	    try
	    {
	        this.mfnapiClient.unset_session_function_alias(sessionFunctionId);
	    }
       catch (Exception e)
        {
            LOGGER.error("Error in API call (unsetSessionFunctionAlias): " + e);
        }
	}
	
	public String getSessionFunctionAlias()
	{
	    return this.getSessionFunctionAlias(null);
	}
	
	public String getSessionFunctionAlias(String sessionFunctionId)
	{
		this.initConnection();
	    
	    String alias = "";
	    try
	    {
	        alias = this.mfnapiClient.get_session_function_alias(sessionFunctionId);
	    }
	    catch (Exception e)
	    {
	        LOGGER.error("Error in API call (getSessionFunctionAlias): " + e);
	    }
	    return alias;
	}
	
	public void log(String text)
	{
	    this.log(text, "INFO");
	}
	
    public void log(String text, String level)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.log(text, level);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (log): " + e);
        }
    }
    
    public void addWorkflowNext(String next, Object value)
    {
		this.initConnection();
	    
        FunctionAPIMessage fam = new FunctionAPIMessage(value);
        String encodedValue = fam.toString();
        try
        {
            this.mfnapiClient.add_workflow_next(next, encodedValue);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (addWorkflowNext): " + e);
        }
    }
    
    public void addDynamicNext(String next, Object value)
    {
        this.addWorkflowNext(next, value);
    }
    
    public void sendToFunctionNow(String destination, Object value)
    {
		this.initConnection();
	    
        FunctionAPIMessage fam = new FunctionAPIMessage(value);
        String encodedValue = fam.toString();
        try
        {
            this.mfnapiClient.send_to_function_now(destination, encodedValue);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (sendToFunctionNow): " + e);
        }
    }
    
    public void addDynamicWorkflow(HashMap<String, Object> trigger)
    {
        String next = (String) trigger.get("next");
        Object value = trigger.get("value");
        this.addWorkflowNext(next, value);
    }
    
    public void addDynamicWorkflow(ArrayList<HashMap<String, Object>> triggerList)
    {
		this.initConnection();
	    
        int size = triggerList.size();
        for (int i = 0; i < size; i++)
        {
            HashMap<String, Object> trigger = triggerList.get(i);
            String next = (String) trigger.get("next");
            Object value = trigger.get("value");
            this.addWorkflowNext(next, value);
        }
    }
    
    public String get(String key)
    {
        return this.get(key, false);
    }
    
    public String get(String key, boolean isPrivate)
    {
		this.initConnection();
	    
        String response = null;
        try
        {
            response = this.mfnapiClient.get(key, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (get): " + e);
        }
        return response;
    }

    public void put(String key, String value)
    {
        this.put(key, value, false, false);
    }
    
    public void put(String key, String value, boolean isPrivate)
    {
        this.put(key, value, isPrivate, false);
    }

    public void put(String key, String value, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.put(key, value, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (put): " + e);
        }
    }

    public void delete(String key)
    {
        this.remove(key, false, false);
    }
    
    public void delete(String key, boolean isPrivate)
    {
        this.remove(key, isPrivate, false);
    }
    
    public void delete(String key, boolean isPrivate, boolean isQueued)
    {
        this.remove(key, isPrivate, isQueued);
    }
    
    public void remove(String key)
    {
        this.remove(key, false, false);
    }
    
    public void remove(String key, boolean isPrivate)
    {
        this.remove(key, isPrivate, false);
    }

    public void remove(String key, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.remove(key, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (remove): " + e);
        }
    }

    public List<String> getKeys()
    {
        return this.getKeys(0, 2147483647, false);
    }
    
    public List<String> getKeys(boolean isPrivate)
    {
        return this.getKeys(0, 2147483647, isPrivate);
    }
    
    public List<String> getKeys(int startIndex)
    {
        return this.getKeys(startIndex, 2147483647, false);
    }
    
    public List<String> getKeys(int startIndex, int endIndex)
    {
        return this.getKeys(startIndex, endIndex, false);
    }
    
    public List<String> getKeys(int startIndex, int endIndex, boolean isPrivate)
    {
		this.initConnection();
	    
        List<String> names = null;
        try
        {
            names = this.mfnapiClient.getKeys(startIndex, endIndex, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getKeys): " + e);
        }
        return names;
    }

    public void createMap(String mapname)
    {
        this.createMap(mapname, false, false);
    }
    
    public void createMap(String mapname, boolean isPrivate)
    {
        this.createMap(mapname, isPrivate, false);
    }
    
    public void createMap(String mapname, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.createMap(mapname, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (createMap): " + e);
        }
    }
    
    public void putMapEntry(String mapname, String key, String value)
    {
        this.putMapEntry(mapname, key, value, false, false);
    }
    
    public void putMapEntry(String mapname, String key, String value, boolean isPrivate)
    {
        this.putMapEntry(mapname, key, value, isPrivate, false);
    }
    
    public void putMapEntry(String mapname, String key, String value, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.putMapEntry(mapname, key, value, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (putMapEntry): " + e);
        }
    }
    
    public String getMapEntry(String mapname, String key)
    {
        return this.getMapEntry(mapname, key, false);
    }
    
    public String getMapEntry(String mapname, String key, boolean isPrivate)
    {
		this.initConnection();
	    
        String value = null;
        try
        {
            value = this.mfnapiClient.getMapEntry(mapname, key, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getMapEntry): " + e);
        }
        return value;
    }
    
    public void deleteMapEntry(String mapname, String key)
    {
        this.deleteMapEntry(mapname, key, false, false);
    }
    
    public void deleteMapEntry(String mapname, String key, boolean isPrivate)
    {
        this.deleteMapEntry(mapname, key, isPrivate, false);
    }

    public void deleteMapEntry(String mapname, String key, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.deleteMapEntry(mapname, key, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (deleteMapEntry): " + e);
        }
    }
    
    public boolean containsMapKey(String mapname, String key)
    {
        return this.containsMapKey(mapname, key, false);
    }
    
    public boolean containsMapKey(String mapname, String key, boolean isPrivate)
    {
		this.initConnection();
	    
        boolean res = false;
        try
        {
            res = this.mfnapiClient.containsMapKey(mapname, key, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (containsMapKey): " + e);
        }
        return res;
    }
    
    public List<String> getMapNames()
    {
        return this.getMapNames(0, 2147483647, false);
    }
    
    public List<String> getMapNames(boolean isPrivate)
    {
        return this.getMapNames(0, 2147483647, isPrivate);
    }
    
    public List<String> getMapNames(int startIndex)
    {
        return this.getMapNames(startIndex, 2147483647, false);
    }
    
    public List<String> getMapNames(int startIndex, int endIndex)
    {
        return this.getMapNames(startIndex, endIndex, false);
    }
    
    public List<String> getMapNames(int startIndex, int endIndex, boolean isPrivate)
    {
		this.initConnection();
	    
        List<String> names = null;
        try
        {
            names = this.mfnapiClient.getMapNames(startIndex, endIndex, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getMapNames): " + e);
        }
        return names;
    }
    
    public Set<String> getMapKeys(String mapname)
    {
        return this.getMapKeys(mapname, false);
    }
    
    public Set<String> getMapKeys(String mapname, boolean isPrivate)
    {
		this.initConnection();
	    
        Set<String> keys = null;
        try
        {
            keys = this.mfnapiClient.getMapKeys(mapname, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getMapKeys): " + e);
        }
        return keys;
    }
    
    public Map<String, String> retrieveMap(String mapname)
    {
        return this.retrieveMap(mapname, false);
    }
    
    public Map<String, String> retrieveMap(String mapname, boolean isPrivate)
    {
		this.initConnection();
	    
        Map<String, String> map = null;
        try
        {
            map = this.mfnapiClient.retrieveMap(mapname, isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (retrieveMap): " + e);
        }
        return map;
    }
    
    public void deleteMap(String mapname)
    {
        this.deleteMap(mapname, false, false);
    }
    
    public void deleteMap(String mapname, boolean isPrivate)
    {
        this.deleteMap(mapname, isPrivate, false);
    }
    
    public void deleteMap(String mapname, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.deleteMap(mapname, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (deleteMap): " + e);
        }
    }
    
    public void clearMap(String mapname)
    {
        this.clearMap(mapname, false, false);
    }
    
    public void clearMap(String mapname, boolean isPrivate)
    {
        this.clearMap(mapname, isPrivate, false);
    }
    
    public void clearMap(String mapname, boolean isPrivate, boolean isQueued)
    {
		this.initConnection();
	    
        try
        {
            this.mfnapiClient.clearMap(mapname, isPrivate, isQueued);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (clearMap): " + e);
        }
    }

    public Map<String, Boolean> getDataToBeDeleted()
    {
        return this.getDataToBeDeleted(false);
    }
    
    public Map<String, Boolean> getDataToBeDeleted(boolean isPrivate)
    {
		this.initConnection();
	    
        Map<String, Boolean> map = null;
        try
        {
            map = this.mfnapiClient.get_data_to_be_deleted(isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getDataToBeDeleted): " + e);
        }
        return map;
    }
    
    public Map<String, String> getTransientDataOutput()
    {
        return this.getTransientDataOutput(false);
    }
    
    public Map<String, String> getTransientDataOutput(boolean isPrivate)
    {
    	this.initConnection();

        Map<String, String> map = null;
        try
        {
            map = this.mfnapiClient.get_transient_data_output(isPrivate);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (getTransientDataOutput): " + e);
        }
        return map;
    }

	public String getFunctionName() {
		this.initContextObjectProperties();

		return functionName;
	}

	public int getFunctionVersion() {
		this.initContextObjectProperties();

		return functionVersion;
	}

	public String getInvokedFunctionArn() {
		this.initContextObjectProperties();

		return invokedFunctionArn;
	}

	public int getMemoryLimitInMB() {
		this.initContextObjectProperties();

		return memoryLimitInMB;
	}

	public String getAwsRequestId() {
		this.initContextObjectProperties();

		return awsRequestId;
	}

	public String getLogGroupName() {
		this.initContextObjectProperties();

		return logGroupName;
	}

	public String getLogStreamName() {
		this.initContextObjectProperties();

		return logStreamName;
	}

	public LambdaCognitoIdentity getIdentity() {
		this.initContextObjectProperties();

		return identity;
	}

	public LambdaClientContext getClientContext() {
		this.initContextObjectProperties();

		return clientContext;
	}

	public Logger getLogger() {
		this.initContextObjectProperties();
		
		return logger;
	}
	
	public boolean addTriggerableBucket(String bucketName)
	{
		this.initConnection();

		boolean success = false;
		try
        {
            success = this.mfnapiClient.addTriggerableBucket(bucketName);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (addTriggerableBucket): " + e);
        }
        return success;
	}
	
	public boolean deleteTriggerableBucket(String bucketName)
	{
		this.initConnection();

		boolean success = false;
		try
        {
            success = this.mfnapiClient.deleteTriggerableBucket(bucketName);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (deleteTriggerableBucket): " + e);
        }
        return success;
	}
	
	public boolean addStorageTriggerForWorkflow(String workflowName, String bucketName)
	{
		this.initConnection();

		boolean success = false;
		try
        {
            success = this.mfnapiClient.addStorageTriggerForWorkflow(workflowName, bucketName);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (addStorageTriggerForWorkflow): " + e);
        }
        return success;
	}
	
	public boolean deleteStorageTriggerForWorkflow(String workflowName, String bucketName)
	{
		this.initConnection();

		boolean success = false;
		try
        {
            success = this.mfnapiClient.deleteStorageTriggerForWorkflow(workflowName, bucketName);
        }
        catch (Exception e)
        {
            LOGGER.error("Error in API call (deleteStorageTriggerForWorkflow): " + e);
        }
        return success;
	}
	
	// some versions that call the main method with various default values
	public TriggerAPIResult addTriggerAMQP(String triggerName, String AMQPAddress, String routingKey)
	{
		String exchange = "egress_exchange";
		boolean withAck = false;
		boolean isDurable = false;
		boolean isExclusive = false;
		double ignoreMessageProbability = 0.0;
		
		return this.addTriggerAMQP(triggerName, AMQPAddress, routingKey, exchange, withAck, isDurable, isExclusive, ignoreMessageProbability);
	}
	
	public TriggerAPIResult addTriggerAMQP(String triggerName, String AMQPAddress, String routingKey, double ignoreMessageProbability)
	{
		String exchange = "egress_exchange";
		boolean withAck = false;
		boolean isDurable = false;
		boolean isExclusive = false;
		
		return this.addTriggerAMQP(triggerName, AMQPAddress, routingKey, exchange, withAck, isDurable, isExclusive, ignoreMessageProbability);
	}
	
	public TriggerAPIResult addTriggerAMQP(String triggerName, String AMQPAddress, String routingKey, String exchange, 
			boolean withAck, boolean isDurable, boolean isExclusive, double ignoreMessageProbability)
	{
		this.initConnection();

		TriggerAPIResult result = null;
		
		TriggerInfoAMQP triggerInfo = new TriggerInfoAMQP();
		triggerInfo.setAmqp_addr(AMQPAddress);
		triggerInfo.setRouting_key(routingKey);
		triggerInfo.setExchange(exchange);
		triggerInfo.setWith_ack(withAck);
		triggerInfo.setDurable(isDurable);
		triggerInfo.setExclusive(isExclusive);
		triggerInfo.setIgnr_msg_prob(ignoreMessageProbability);
		
		try
		{
			result = this.mfnapiClient.addTriggerAMQP(triggerName, triggerInfo);
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (addTriggerAMQP): " + e);
		}
		return result;
	}
	
	public TriggerAPIResult addTriggerTimer(String triggerName, long timerIntervalMilliseconds)
	{
		this.initConnection();

		TriggerAPIResult result = null;
		
		TriggerInfoTimer triggerInfo = new TriggerInfoTimer();
		triggerInfo.setTimerIntervalMilliseconds(timerIntervalMilliseconds);

		try
		{
			result = this.mfnapiClient.addTriggerTimer(triggerName, triggerInfo);
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (addTriggerTimer): " + e);
		}
		return result;
	}
	
	public TriggerAPIResult addTriggerForWorkflow(String triggerName, String workflowName)
	{
		return this.addTriggerForWorkflow(triggerName, workflowName, "");
	}

	public TriggerAPIResult addTriggerForWorkflow(String triggerName, String workflowName, String workflowState)
	{
		this.initConnection();

		TriggerAPIResult result = null;
		try
		{
			result = this.mfnapiClient.addTriggerForWorkflow(triggerName, workflowName, workflowState);
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (addTriggerForWorkflow): " + e);
		}
		return result;
	}
	
	public TriggerAPIResult deleteTriggerForWorkflow(String triggerName, String workflowName)
	{
		this.initConnection();

		TriggerAPIResult result = null;
		try
		{
			result = this.mfnapiClient.deleteTriggerForWorkflow(triggerName, workflowName);
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (deleteTriggerForWorkflow): " + e);
		}
		return result;
	}

	public TriggerAPIResult deleteTrigger(String triggerName)
	{
		this.initConnection();

		TriggerAPIResult result = null;
		try
		{
			result = this.mfnapiClient.deleteTrigger(triggerName);
		}
		catch (Exception e)
		{
			LOGGER.error("Error in API call (deleteTrigger): " + e);
		}
		return result;
	}

}
