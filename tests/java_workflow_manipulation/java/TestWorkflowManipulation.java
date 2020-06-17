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
import java.util.StringTokenizer;

import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class TestWorkflowManipulation
{
    public Object handle(Object event, MicroFunctionsAPI context)
    {
        context.log("event in java: " + event);
        if (event != null)
        {
            String eventStr = (String) event;
            StringTokenizer s = new StringTokenizer(eventStr, " ");
            String t = s.nextToken();
            String apiCall = s.nextToken();

            Object value = getNextFunctionValue(t);
            context.log("got value: " + value);
            if (apiCall.equalsIgnoreCase("addWorkflowNext"))
            {
                context.addWorkflowNext("final", value + "_" + apiCall);
            }
            else if (apiCall.equalsIgnoreCase("addDynamicNext"))
            {
                context.addDynamicNext("final", value + "_" + apiCall);
            }
            else if (apiCall.equalsIgnoreCase("addDynamicWorkflowTrigger"))
            {
                HashMap<String, Object> trigger = new HashMap<String, Object>();
                trigger.put("next", "final");
                trigger.put("value", value + "_" + apiCall);
                context.addDynamicWorkflow(trigger);
            }
            else if (apiCall.equalsIgnoreCase("addDynamicWorkflowTriggerList"))
            {
                HashMap<String, Object> trigger = new HashMap<String, Object>();
                trigger.put("next", "final");
                trigger.put("value", value + "_" + apiCall);
                ArrayList<HashMap<String, Object>> triggerList = new ArrayList<HashMap<String, Object>>();
                triggerList.add(trigger);
                context.addDynamicWorkflow(triggerList);
            }
        }

        return "";
    }

    private Object getNextFunctionValue(String t)
    {
        if (t.equalsIgnoreCase("int"))
        {

            return 42;
        }
        else if (t.equalsIgnoreCase("double"))
        {
            return 42.0;
        }
        else if (t.equalsIgnoreCase("float"))
        {
            return 42.0f;
        }
        else if (t.equalsIgnoreCase("dict"))
        {
            HashMap<String, Boolean> map = new HashMap<String, Boolean>();
            map.put("mykey", true);
            return map;
        }
        else if (t.equalsIgnoreCase("list"))
        {
            ArrayList<String> list = new ArrayList<String>();
            list.add("myelement");
            return list;
        }
        else if (t.equalsIgnoreCase("string"))
        {
            String mystr = "mystring";
            return mystr;
        }
        else
        {
            return null;
        }
    }
}

