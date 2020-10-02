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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.Set;

import org.json.JSONArray;
import org.json.JSONObject;
import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class EntryFunction
{

    public Object handle(Object event, MicroFunctionsAPI context)
    {
        if (event == null)
        {
            return "";
        }

        Object retval = null;

        JSONObject eventobj = (JSONObject) event;

        boolean sendNow = false;

        context.log("Starting regular function (EntryFunction.java) with input: " + event);

        String action = eventobj.getString("action");

        if (action.equalsIgnoreCase("--create-new-session"))
        {
            context.log("Creating new session...");
            JSONArray sessionDescription = eventobj.getJSONArray("session");
            int len = sessionDescription.length();
            for (int i = 0; i < len; i++)
            {
                JSONObject jobjsf = sessionDescription.getJSONObject(i);

                JSONObject event2 = new JSONObject();
                event2.put("sessionStartParams", jobjsf.getString("parameters"));
                String gname = jobjsf.getString("name");
                // capitalize the name, because we are in Java
                gname = gname.substring(0, 1).toUpperCase() + gname.substring(1);
                context.addWorkflowNext(gname, event2);
            }
        }
        else if (action.equalsIgnoreCase("--update-session"))
        {
            if (eventobj.has("immediate"))
            {
                sendNow = eventobj.getBoolean("immediate");
            }

            Object message = null;
            try
            {
                message = eventobj.getJSONObject("sessionUpdateParams");
            }
            catch (Exception e)
            {
                message = eventobj.getString("sessionUpdateParams");
            }

            context.log("Updating existing session...");

            String messageType = eventobj.getString("messageType");
            if (messageType.equalsIgnoreCase("name"))
            {
                String gname = eventobj.getString("messageToFunction");
                context.log("Updating all session functions with a given name: " + gname);
                if (message instanceof JSONObject)
                {
                    context.sendToAllRunningFunctionsInSessionWithFunctionName(gname, (JSONObject) message, sendNow);
                }
                else if (message instanceof String)
                {
                    context.sendToAllRunningFunctionsInSessionWithFunctionName(gname, (String) message, sendNow);
                }
            }
            else if (messageType.equalsIgnoreCase("session"))
            {
                context.log("Updating all session functions in a session");
                if (message instanceof JSONObject)
                {
                    context.sendToAllRunningFunctionsInSession((JSONObject) message, sendNow);
                }
                else if (message instanceof String)
                {
                    context.sendToAllRunningFunctionsInSession((String) message, sendNow);
                }
            }
        }
        else if (action.equalsIgnoreCase("--update-session-function"))
        {
            if (eventobj.has("immediate"))
            {
                sendNow = eventobj.getBoolean("immediate");
            }
            String sgid = eventobj.getString("sessionFunctionId");
            context.log("Updating specific session function instance: " + sgid);

            Object message = null;
            try
            {
                message = eventobj.getJSONObject("sessionUpdateParams");
            }
            catch (Exception e)
            {
                message = eventobj.getString("sessionUpdateParams");
            }

            if (message instanceof JSONObject)
            {
                context.sendToRunningFunctionInSession(sgid, (JSONObject) message, sendNow);
            }
            else if (message instanceof String)
            {
                context.sendToRunningFunctionInSession(sgid, (String) message, sendNow);
            }
        }
        else if (action.equalsIgnoreCase("--get-session-info"))
        {
            context.log("Getting session info...");
            String sid = context.getSessionId();
            List<String> rgidlist = context.getAllSessionFunctionIds();

            JSONObject info = new JSONObject();
            info.put("session_id", sid);
            info.put("session_function_ids", rgidlist);

            retval = info;
        }
        else if (action.equalsIgnoreCase("--get-session-alias-summary"))
        {
            context.log("Getting session alias info...");
            Map<String, Map<String, String>> aliasSummary = context.getAliasSummary();

            retval = aliasSummary;
        }
        else if (action.equalsIgnoreCase("--set-alias"))
        {
            String aliasType = eventobj.getString("alias_type");
            String alias = eventobj.getString("alias");
            if (aliasType.equalsIgnoreCase("session"))
            {
                context.setSessionAlias(alias);
            }
            else if (aliasType.equalsIgnoreCase("function"))
            {
                String functionId = eventobj.getString("function_id");
                context.setSessionFunctionAlias(alias, functionId);
            }
        }
        else if (action.equalsIgnoreCase("--unset-alias"))
        {
            String aliasType = eventobj.getString("alias_type");
            if (aliasType.equalsIgnoreCase("session"))
            {
                context.unsetSessionAlias();
            }
            else if (aliasType.equalsIgnoreCase("function"))
            {
                String functionId = eventobj.getString("function_id");
                context.unsetSessionFunctionAlias(functionId);
            }
        }
        else if (action.equalsIgnoreCase("--update-session-function-with-alias"))
        {
            String alias = eventobj.getString("alias");

            Object message = null;
            try
            {
                message = eventobj.getJSONObject("sessionUpdateParams");
            }
            catch (Exception e)
            {
                message = eventobj.getString("sessionUpdateParams");
            }

            if (message instanceof JSONObject)
            {
                context.sendToRunningFunctionInSessionWithAlias(alias, (JSONObject) message, true);
            }
            else if (message instanceof String)
            {
                context.sendToRunningFunctionInSessionWithAlias(alias, (String) message, true);
            }
        }

        if (retval == null)
        {
            retval = context.getSessionId();
        }

        if (sendNow)
        {
            try
            {
                context.log("Sleeping for 5 seconds...");
                Thread.sleep(5000);
            }
            catch (Exception e)
            {
            }
        }

        context.log("Finished regular function (EntryFunction.java).");

        return retval;
    }


}
