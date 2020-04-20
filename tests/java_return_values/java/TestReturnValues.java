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

import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class TestReturnValues
{
    public Object handle(Object event, MicroFunctionsAPI context)
    {
        context.log("event in java: " + event);
        if (event != null)
        {
            String eventStr = (String) event;
            if (eventStr.equalsIgnoreCase("int"))
            {
                return 42;
            }
            else if (eventStr.equalsIgnoreCase("double"))
            {
                return 42.0;
            }
            else if (eventStr.equalsIgnoreCase("float"))
            {
                return 42.0f;
            }
            else if (eventStr.equalsIgnoreCase("dict"))
            {
                HashMap<String, Boolean> map = new HashMap<String, Boolean>();
                map.put("mykey", true);
                return map;
            }
            else if (eventStr.equalsIgnoreCase("list"))
            {
                ArrayList<String> list = new ArrayList<String>();
                list.add("myelement");
                return list;
            }
            else if (eventStr.equalsIgnoreCase("string"))
            {
                String mystr = "mystring";
                return mystr;
            }
        }
        context.log("no match; gonna return null");

        //return null;
        return new Object[] {null};
    }

}
