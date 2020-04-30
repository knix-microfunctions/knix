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

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONException;
import java.util.ArrayList;
import java.util.Random;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class TokenAuthenticatorViaManagementService {
    private static final Logger logger = LogManager.getLogger(TokenAuthenticatorViaManagementService.class);

	private String datalayerServerHost = null;
	private int datalayerServerPort = 0;
    private int requestTimeoutMs = 0;
    private boolean runningInsideKubernetes = false;
    private ArrayList<String> managementEndpoints = null;
    Random rand = new Random();

    public TokenAuthenticatorViaManagementService(String datalayerServerHost, int datalayerServerPort, int requestTimeoutMs) {
		this.datalayerServerHost = datalayerServerHost;
		this.datalayerServerPort = datalayerServerPort;
        this.requestTimeoutMs = requestTimeoutMs;
        this.managementEndpoints = new ArrayList<String>();
        this.runningInsideKubernetes = false;
        Map<String, String> env = System.getenv();
        if (env.containsKey("KUBERNETES_PORT")) {
            this.runningInsideKubernetes = true;
        }
    }
    private void populateManagementServiceUrls() {
        // DLCLIENT_MANAGEMENT = DataLayerClient(1,sid="Management",wid="Management",is_wf_private=True,for_mfn=False, connect=connect, init_tables=True)
        //      if is_wf_private:
        //          self.keyspace = "sbox_" + sid
        //          self.tablename = "wf_" + wid
        // endpoint_list = [url]
        // DLCLIENT_MANAGEMENT.put("management_endpoints", json.dumps(endpoint_list))
        this.managementEndpoints.clear();
        String keyspace = "sbox_Management";
        String tablename = "wf_Management";
        String keyname = "management_endpoints";
        String ret = StorageOperations.getData(this.datalayerServerHost, this.datalayerServerPort, this.requestTimeoutMs, keyspace, tablename, keyname);
        if (ret == null) {
            logger.error("populateManagementServiceUrls: " + "No data found for: " + keyspace + ":" + tablename + ":" + keyname);
            return;
        }

        try {
            logger.error("populateManagementServiceUrls: " + "Data found for: " + keyspace + ":" + tablename + ":" + keyname + ": " + ret);
            JSONArray urllist = new JSONArray(ret);
            for (int i = 0; i < urllist.length(); i++) {
                String httpurl = urllist.getString(i);
                if (httpurl != null && httpurl != "") {
                    this.managementEndpoints.add(httpurl);
                }
            }
        } catch (JSONException e) {
            logger.error("populateManagementServiceUrls error: " + e.getMessage());
        }
        return;
    }

    private String selectManagementServiceEndpoint() {
        String endpoint = null;
        if (this.managementEndpoints.isEmpty()) {
            this.populateManagementServiceUrls();
        }

        if (this.managementEndpoints.isEmpty()) {
            logger.error("selectManagementServiceEndpoint error: managementEndpoints.isEmpty()");
            return null;
        }

        // pick an endpoint in a loadbalanced way if there is more than one url available
        if (this.managementEndpoints.size() == 1) {
            endpoint = this.managementEndpoints.get(0);
        } else {
            int n = rand.nextInt(this.managementEndpoints.size());
            endpoint = this.managementEndpoints.get(n);
        }
        return endpoint;
    }

    private String getHostName(String httpurl) {
        String hostname = null;
        Pattern p1 = Pattern.compile("https?://([^:]+).*");
        Matcher m1 = p1.matcher(httpurl);
        if (m1.find()) {
            hostname = m1.group(1);
        }
        return hostname;
    }

    private String getHostNameFirstPart(String hostname) {
        String hostname_part1 = null;
        Pattern p2 = Pattern.compile("([^\\.]+)+");
        Matcher m2 = p2.matcher(hostname);
        if (m2.find()) {
            hostname_part1 = m2.group(1);
        }
        return hostname_part1;
    }

    private JSONObject invokeManagementService(String httpurl, JSONObject data, String endpointHostname, String endpointHostnameFirstPartAsUrl) {
        if (runningInsideKubernetes == true) {
            if (endpointHostname != null && endpointHostnameFirstPartAsUrl != null) {
                httpurl = endpointHostnameFirstPartAsUrl;
            }
            else {
                logger.error("invokeManagementService error: endpointHostname or endpointHostnameFirstPartAsUrl are null");
                logger.error("invokeManagementService error: endpointHostname: " + endpointHostname);
                logger.error("invokeManagementService error: endpointHostnameFirstPartAsUrl: " + endpointHostnameFirstPartAsUrl);
                return null;
            }
        }

        JSONObject responseObject = null;
        try {

            URL url = new URL (httpurl);
            HttpURLConnection con = (HttpURLConnection)url.openConnection();
            con.setRequestMethod("POST");
            con.setRequestProperty("Content-Type", "application/json; utf-8");
            con.setRequestProperty("Accept", "application/json");
            if (runningInsideKubernetes == true) {
                con.setRequestProperty("Host", endpointHostname);
            }
            con.setDoOutput(true);
            String jsonInputString = data.toString();
            OutputStream os = con.getOutputStream();
            byte[] input = jsonInputString.getBytes("utf-8");
            os.write(input, 0, input.length);

            int code = con.getResponseCode();
            BufferedReader br = new BufferedReader(new InputStreamReader(con.getInputStream(), "utf-8"));
            StringBuilder responseString = new StringBuilder();
            String responseLine = null;
            while ((responseLine = br.readLine()) != null) {
                responseString.append(responseLine.trim());
            }

            if (code == 200) {
                responseObject = new JSONObject(responseString.toString());
            }
            

        } catch (Exception e) {
            logger.error("invokeManagementService error: " + e.getMessage());
            logger.error("invokeManagementService error: httpurl: " + httpurl);
            logger.error("invokeManagementService error: endpointHostname: " + endpointHostname);
            logger.error("invokeManagementService error: endpointHostnameFirstPartAsUrl: " + endpointHostnameFirstPartAsUrl);
            return null;
        }
        return responseObject;
    }


    public String verifyUser(String token, String email) {
        String statusmessage = "Connection error";

        String endpoint = selectManagementServiceEndpoint();
        if (endpoint == null || (!endpoint.startsWith("http"))) {
            logger.error("verifyUser error: " + "Missing Management service endpoint url");
            return "Missing Management service endpoint url";
        }

        // String endpoint="https://wf-mfn1-management.mfn.knix.io:443";
        // String endpointHostname="wf-mfn1-management.mfn.knix.io";
        // String endpointHostnameFirstPart="wf-mfn1-management"; // this used for kubernetes only
        String endpointHostname = null;
        String endpointHostnameFirstPartAsUrl = null;
        if (runningInsideKubernetes == true) {
            endpointHostname = this.getHostName(endpoint);
            if (endpointHostname != null) {
                //System.out.println("endpointHostname: " + hostname);
                String endpointHostnameFirstPart = this.getHostNameFirstPart(endpointHostname);
                if (endpointHostnameFirstPart != null) {
                    //System.out.println("endpointHostnameFirstPart: " + endpointHostnameFirstPart);
                    endpointHostnameFirstPartAsUrl = "http://" + endpointHostnameFirstPart; // this used for kubernetes only
                }
            }
        }

        /*
        request = \
        {
            "action": "verifyUser",
            "data": {
                "user": {"token": _usertoken, "email": _useremail},
            }
        }
        */

        JSONObject user = new JSONObject();
        user.put("token", token);
        user.put("email", email);
        JSONObject data = new JSONObject();
        data.put("user", user);
        JSONObject request = new JSONObject();
        request.put("action", "verifyUser");
        request.put("data", data);
        //logger.info("verifyUser: " + " endpoint: " + endpoint + ", request: " + request.toString());

        JSONObject response = invokeManagementService(endpoint, request, endpointHostname, endpointHostnameFirstPartAsUrl);
        /*
        {
            "status": "success"  or "failure", 
            "data": 
            {
                "message": "some status message",
                "email": "abcd@abcd",   if status == "success"
                "token": "sklfds2480958",  if status == "success"
                "storageEndpoint": "abcdATabcd"  if status == "success"
            }
        }
        */
        if (response == null) {
            return statusmessage;
        }        
        //logger.info("verifyUser: " + "response: " + response.toString());
        if (!(response.has("status") && response.has("data"))) {
            return statusmessage;
        }
        String status = response.getString("status");
        JSONObject dataInResponse = response.getJSONObject("data");
        String message = dataInResponse.getString("message");
        if (status.equalsIgnoreCase("success")) {
            statusmessage = "success: " + message;
        } else {
            statusmessage = "failure: " + message;
        }
        return statusmessage;
    }
}