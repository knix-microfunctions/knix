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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class TestMiscOperations
{
    public Object handle(Object event, MicroFunctionsAPI context)
    {
        HashMap<String, Boolean> testResultMap = new HashMap<String, Boolean>();

        testMiscOperations(context, testResultMap);

        return testResultMap;
    }

    private void testMiscOperations(MicroFunctionsAPI context,
        HashMap<String, Boolean> testResultMap)
    {
        boolean success = false;
        Random r = new Random();
        int myrand = r.nextInt(1000);

        String response = context.ping(myrand);
        if (response.equalsIgnoreCase("pong " + myrand))
        {
            success = true;
        }

        testResultMap.put("ping", success);

        boolean success2 = false;
        long remtime = context.getRemainingTimeInMillis();
        if (remtime == 300000l)
        {
            success2 = true;
        }

        testResultMap.put("getRemainingTimeInMillis", success2);

        boolean success3 = false;
        String key = context.getEventKey();
        String instanceid = context.getInstanceId();
        if (!key.equalsIgnoreCase("") && !instanceid.equalsIgnoreCase("") && key.equalsIgnoreCase(instanceid))
        {
            success3 = true;
        }

        testResultMap.put("getEventKey", success3);
        testResultMap.put("getInstanceId", success3);

        myrand = r.nextInt(1000);

        try
        {
            context.log("Logging test: " + myrand);
            testResultMap.put("log", true);
        }
        catch (Exception e)
        {
        }

    }

}
