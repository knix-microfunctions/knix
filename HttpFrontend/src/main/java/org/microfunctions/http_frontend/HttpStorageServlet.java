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

import java.io.BufferedReader;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;

import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@SuppressWarnings("serial")
public class HttpStorageServlet extends HttpServlet {
	
	private static final Logger logger = LogManager.getLogger(HttpStorageServlet.class);
    
	private String datalayerServerHost = null;
	private int datalayerServerPort = 0;
    private int requestTimeoutMs = 0;
    private TokenAuthenticatorViaManagementService tokenAuthenticatorViaManagementService = null;
	
	public HttpStorageServlet(String datalayerServerHost, int datalayerServerPort, int requestTimeoutMs) {
		this.datalayerServerHost = datalayerServerHost;
		this.datalayerServerPort = datalayerServerPort;
        this.requestTimeoutMs = requestTimeoutMs;
        this.tokenAuthenticatorViaManagementService = new TokenAuthenticatorViaManagementService(datalayerServerHost, datalayerServerPort, requestTimeoutMs);
	}
	
	private String generateKeyspace(String email) {
	    String keyspace = null;
	    if (email != null) {
	        keyspace = "storage_" + email.replace("@", "AT").replace(".", "_").replace("-", "_");
	    }
	    return keyspace;
	}
    
	@Override
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws IOException {
        
		String value = null;
		
		// read request body if present

		StringBuffer requestBody = new StringBuffer();
        String line = null;
        BufferedReader reader = request.getReader();

	    while((line = reader.readLine()) != null)
	    {
	    	requestBody.append(line);
	        line = reader.readLine();
        }

		if (requestBody.length() > 0) {
			value = requestBody.toString();	
		} else {
			value = request.getParameter("value");
		}

        String token = request.getParameter("token");
	    if (token == null) {
            logger.error("doPost: " + "token unspecified");
	        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"token\" unspecified.");
	        return;
        }

        String email = request.getParameter("email");
	    if (email == null) {
	        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"email\" unspecified.");
	        return;
        }

        String verification = this.tokenAuthenticatorViaManagementService.verifyUser(token, email);
        //logger.info("doPost: " + "verification: " + verification);

        if ( !verification.startsWith("success") ) {
            logger.error("doPost: " + "token verification failed: " + verification);
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"token\" verification failed: " + verification);
	        return;
        }

        String keyspace = this.generateKeyspace(email);
	    
	    String table = request.getParameter("table");
	    if (table == null) {
	        response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"table\" unspecified.");
            return;
	    }
	    
        String action = request.getParameter("action");
        if (action == null) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"action\" unspecified.");
            return;
        }
        
        String key = request.getParameter("key");
        
        String strStart = request.getParameter("start");
        String strCount = request.getParameter("count");
        int start = 0;
        int count = 0;
        String ret = null;
        
        switch (action.toLowerCase()) {
        case "getdata":
            if (key == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"key\" unspecified.");
                return;
            }
            
            ret = StorageOperations.getData(this.datalayerServerHost, this.datalayerServerPort, this.requestTimeoutMs, keyspace, table, key);
            break;
        case "putdata":
            if (key == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"key\" unspecified.");
                return;
            }
            
            if (value == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"value\" unspecified.");
                return;
            }
            
            ret = String.valueOf(StorageOperations.putData(this.datalayerServerHost, this.datalayerServerPort, this.requestTimeoutMs, keyspace, table, key, value));
            break;
        case "deletedata":
            if (key == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"key\" unspecified.");
                return;
            }
            
            ret = String.valueOf(StorageOperations.deleteData(this.datalayerServerHost, this.datalayerServerPort, this.requestTimeoutMs, keyspace, table, key));
            break;
        case "listkeys":
            if (strStart == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"start\" unspecified.");
                return;
            }
        
            try {
                start = Integer.valueOf(strStart);
            } catch (NumberFormatException e) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"start\" invalid.");
                return;
            }

            if (strCount == null) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"count\" unspecified.");
                return;
            }

            try {
                count = Integer.valueOf(strCount);
            } catch (NumberFormatException e) {
                response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"count\" invalid.");
                return;
            }
            
            ret = StorageOperations.listKeys(this.datalayerServerHost, this.datalayerServerPort, this.requestTimeoutMs, keyspace, table, start, count);
            break;
        default:
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "\"action\" invalid.");
            return;
        }
        
        logger.info("[StorageOperation] Executed Action: " + action + ", Keyspace: " + keyspace + ", Table: " + table);

		response.setContentType("text/plain");
		response.setStatus(HttpServletResponse.SC_OK);
		response.getWriter().print(ret);
	}
	
	@Override
	protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
		this.doPost(request, response);
	}
	
	@Override
	protected void doPut(HttpServletRequest request, HttpServletResponse response) throws IOException {
		response.sendError(HttpServletResponse.SC_NOT_IMPLEMENTED, "PUT unimplemented.");
	}

	@Override
	protected void doDelete(HttpServletRequest request, HttpServletResponse response) throws IOException {
		response.sendError(HttpServletResponse.SC_NOT_IMPLEMENTED, "DELETE unimplemented.");
	}
}
