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

import java.io.FileInputStream;
import java.io.InputStream;
import java.util.HashMap;

import org.json.JSONObject;
import org.json.JSONTokener;

public class JavaWorkerMain
{
    public static void main(String[] args)
    {
    	String paramsFilename = args[0];
    	
    	// _XXX_: if we have only a single JVM for all java functions, the parameters for all are passed in one file
    	boolean singleJVM = false;
    	if (paramsFilename.equalsIgnoreCase("/opt/mfn/workflow/states/single_jvm_worker_params.json"))
    	{
    		singleJVM = true;
    	}
    	
    	JSONObject params = null;
    	try
    	{
        	InputStream is = new FileInputStream(paramsFilename);
        	JSONTokener tokener = new JSONTokener(is);
        	params = new JSONObject(tokener);
    	}
    	catch (Exception e)
    	{
    		e.printStackTrace();
    		System.exit(1);
    	}
    	
    	if (singleJVM)
    	{
	    	//HashMap<String, RequestServer> requestServerMap = new HashMap<String, RequestServer>();
	    	for (String statename: params.keySet())
	    	{
	    		JSONObject stateParams = params.getJSONObject(statename);
	            HashMap<String, String> argsmap = new HashMap<String, String>();
	            
	            argsmap.put("functionPath", stateParams.getString("functionPath"));
	            argsmap.put("functionName", stateParams.getString("functionName"));
	            argsmap.put("serverSocketFilename", stateParams.getString("serverSocketFilename"));
	            
	            RequestServer rs = new RequestServer(argsmap);
	            Thread requestServerThread = new Thread(rs);
	            requestServerThread.start();
	            
	            //requestServerMap.put(statename, rs);
	    	}
    	}
    	else
    	{
            HashMap<String, String> argsmap = new HashMap<String, String>();
            
            argsmap.put("functionPath", params.getString("functionPath"));
            argsmap.put("functionName", params.getString("functionName"));
            argsmap.put("serverSocketFilename", params.getString("serverSocketFilename"));
            
            RequestServer rs = new RequestServer(argsmap);
            Thread requestServerThread = new Thread(rs);
            requestServerThread.start();
    		
    	}
    }
}
