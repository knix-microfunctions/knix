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

import org.json.JSONObject;

public class FunctionExecutionResult
{
    private String key;
    private Object functionResult;
    private boolean hasError;
    private String errorType;
    private String errorTrace;

    public FunctionExecutionResult(String key, Object functionResult, boolean hasError, String errorType, StringBuilder et)
    {
        this.key = key;
        this.functionResult = functionResult;
        if (functionResult instanceof Object[] && ((Object[]) functionResult).length == 1)
        {
            this.functionResult = ((Object[]) functionResult)[0];
        }
        this.hasError = hasError;
        this.errorType = errorType;
        this.errorTrace = et.toString();
    }
    
    public String toString()
    {
        return this.serialize();
    }
    
    private String serialize()
    {
        JSONObject obj = new JSONObject();
        obj.put("key", this.key);
        if (this.functionResult == null)
        {
            obj.put("functionResult", JSONObject.NULL);
        }
        else
        {
            obj.put("functionResult", this.functionResult);
        }
        obj.put("hasError", this.hasError);
        obj.put("errorType", this.errorType);
        obj.put("errorTrace", this.errorTrace);
        
        return obj.toString();
    }
}
