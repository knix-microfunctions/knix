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
package org.microfunctions.mfnapi;

import org.json.JSONObject;

public class FunctionAPIMessage
{
    private Object value;
    private String serialized;
    
    public FunctionAPIMessage(Object value)
    {
        this.value = value;
        this.serialize();
    }
    
    public FunctionAPIMessage(String serialized)
    {
    	this.serialized = serialized;
    	this.deserialize();
    }
    
    public String toString()
    {
        return this.serialized;
    }
    
    public Object getValue()
    {
    	return this.value;
    }
    
    public void serialize()
    {
        JSONObject obj = new JSONObject();
        if (this.value == null)
        {
            obj.put("value", JSONObject.NULL);
        }
        else
        {
            obj.put("value", this.value);
        }
        this.serialized = obj.toString();
    }
    
    public void deserialize()
    {
    	try
    	{
    		JSONObject obj = new JSONObject(this.serialized);
    		this.value = obj.get("value");
    	}
    	catch (Exception e)
    	{
    		this.value = this.serialized;
    	}
    }
}
