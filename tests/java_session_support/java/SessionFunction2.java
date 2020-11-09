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

public class SessionFunction2
{

    private String functionName = "SessionFunction2";

    private final long SLEEP_TIME = 10000;

    private String params;

    private String doStuff(String sgid)
    {
        return "telemetry_" + this.functionName + "::doStuff()";
    }

    private String doSomethingElse(String sgid)
    {
        return "telemetry_" + this.functionName + "::doSomethingElse()";
    }

    public Object handle(Object event, MicroFunctionsAPI context)
    {
        String sgid = context.getSessionFunctionId();

        context.log("Starting long-running function (" + this.functionName + ") with input: " + event + " session function id: " + sgid);

        JSONObject eventobj = (JSONObject) event;

        this.params = eventobj.getString("sessionStartParams");

        while (context.isStillRunning())
        {
            context.log("New loop iteration (" + this.functionName + ")... session function id: " + sgid);

            List<String> msgs = context.getSessionUpdateMessages();

            int len = msgs.size();
            for (int i = 0; i < len; i++)
            {
                String msg = msgs.get(i);
                if (msg != null)
                {
                    context.log("Received message (" + this.functionName + "): " + msg + " session function id: " + sgid);
                    this.params = msg;
                }
            }

            JSONObject telemetry = new JSONObject();
            telemetry.put("action", "--telemetry");
            telemetry.put("function_name", this.functionName);
            telemetry.put("session_id", context.getSessionId());
            telemetry.put("session_function_id", sgid);
            telemetry.put("timestamp", System.currentTimeMillis());

            if (this.params.equalsIgnoreCase("config1"))
            {
                telemetry.put("telemetry", doStuff(sgid));
            }
            else if (this.params.equalsIgnoreCase("config2"))
            {
                telemetry.put("telemetry", doSomethingElse(sgid));
            }
            else
            {
                context.log("Undefined configuration parameter (" + this.functionName + "): " + this.params + "; not doing anything... session function id: " + sgid);
                telemetry.put("telemetry", this.functionName + "::None");
            }

            context.sendToFunctionNow("telemetryHandler", telemetry);

            try
            {
                Thread.sleep(this.SLEEP_TIME);
            }
            catch (Exception e)
            {
            }

        }

        context.log("Finished long-running function (" + this.functionName + "). session function id: " + sgid);

        return "end of " + this.functionName;
    }

}
