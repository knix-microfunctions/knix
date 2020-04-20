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
import org.json.JSONObject;

import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class FailFunctionCatchJava
{
    public Object handle(Object event, MicroFunctionsAPI context) throws Exception
    {
        if (event != null)
        {
            if (event instanceof org.json.JSONObject)
            {
                JSONObject eventInput = (org.json.JSONObject) event;
                if (eventInput.has("invalid_value"))
                {
                    throw new StringIndexOutOfBoundsException();
                }
                else if (eventInput.has("invalid_type"))
                {
                    throw new NumberFormatException();
                }
                else if (eventInput.has("invalid_denominator"))
                {
                    throw new ArithmeticException();
                }
                else if (eventInput.has("invalid_all"))
                {
                    throw new Exception("States.All");
                }
            }
            else
            {
                context.log(event.getClass().getName());
            }
        }
        else
        {
            context.log("event is null");
        }

        return event;
    }

}
