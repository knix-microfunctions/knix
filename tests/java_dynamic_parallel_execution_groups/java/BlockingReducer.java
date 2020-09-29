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
import java.util.List;
import java.util.Set;

import org.json.JSONArray;
import org.json.JSONObject;
import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class BlockingReducer
{
	private JSONObject reduceResultsWordCount(HashMap<Integer, JSONObject> mapperResults)
	{
		JSONObject finalResult = new JSONObject();
		Set<Integer> mappers = mapperResults.keySet();
		for (Integer mapper: mappers)
		{
			JSONObject mres = mapperResults.get(mapper);
			Set<String> words = mres.keySet();
			for (String word: words)
			{
				if (!finalResult.has(word))
				{
					finalResult.put(word, 0);
				}
				finalResult.put(word, finalResult.getInt(word) + mres.getInt(word));
			}
		}

		return finalResult;
	}
	
	private JSONArray reduceResultsMergeSort(HashMap<Integer, JSONArray> mapperResults)
	{
		List<Integer> finalResult = new ArrayList<Integer>();
		
		assert(mapperResults.size() == 2);
		
		JSONArray data1 = mapperResults.get(0);
		JSONArray data2 = mapperResults.get(1);
		
		int i = 0;
		int j = 0;
		int size1 = data1.length();
		int size2 = data2.length();
		while (i < size1 && j < size2)
		{
			int v1 = data1.getInt(i);
			int v2 = data2.getInt(j);
			if (v1 < v2)
			{
				finalResult.add(v1);
				i++;
			}
			else
			{
				finalResult.add(v2);
				j++;
			}
		}
		
		while (i < size1)
		{
			int v1 = data1.getInt(i);
			finalResult.add(v1);
			i++;
		}
		
		while (j < size2)
		{
			int v2 = data2.getInt(j);
			finalResult.add(v2);
			j++;
		}
		
		JSONArray result = new JSONArray(finalResult);
		return result;
	}

	public Object handle(Object event, MicroFunctionsAPI context)
	{
		if (event == null)
		{
			return "";
		}
		
		// initialize
		JSONObject event2 = (JSONObject) event;
		String reducerIdKey = event2.getString("reducer_id_key");
		String rfid = context.getSessionFunctionId();
		context.log("reducerIdKey: " + reducerIdKey + ", rfid: " + rfid);
		context.put(reducerIdKey, rfid, true);
				
		int numMappersToExpect = event2.getInt("num_mappers");
		
		context.log("numMappersToExpect: " + numMappersToExpect);

		HashMap<Integer, JSONObject> mapperResultsJSONObject = new HashMap<Integer, JSONObject>();
		HashMap<Integer, JSONArray> mapperResultsJSONArray = new HashMap<Integer, JSONArray>();
		
		context.log("PEG id: " + event2.getString("peg_id"));
		
		List<String> messages = context.getSessionUpdateMessages(numMappersToExpect, true);
		
		context.log("All mapper results received; continuing... " + event2.getString("peg_id"));

		int size = messages.size();
		for (int i = 0; i < size; i++)
		{
			String message = messages.get(i);
			context.log("New message from mapper: " + message.substring(0, Math.min(100, message.length())) + "  ...");
			JSONObject mres = new JSONObject(message);
			int mapperId = mres.getInt("mapper_id");
			Object result = mres.get("mapper_result");
			if (result instanceof JSONObject)
			{
				mapperResultsJSONObject.put(mapperId, (JSONObject) result);
			}
			else if (result instanceof JSONArray)
			{				
				context.log("JSON Array");
				mapperResultsJSONArray.put(mapperId, (JSONArray) result);
			}
			
		}
		
		JSONObject myJob = event2.getJSONObject("job");
		JSONObject finalResultJSONObject = null;
		JSONArray finalResultJSONArray = null;
		if (myJob.getString("type").equalsIgnoreCase("wordcount"))
		{
			finalResultJSONObject = reduceResultsWordCount(mapperResultsJSONObject);
		}
		else if (myJob.getString("type").equalsIgnoreCase("mergesort"))
		{
			finalResultJSONArray = reduceResultsMergeSort(mapperResultsJSONArray);
		}
		
		if (event2.has("next_reducer_id") && event2.has("mapper_id"))
		{
			String nextReducerId = event2.getString("next_reducer_id");
			int myId = event2.getInt("mapper_id");
			
			JSONObject msg = new JSONObject();
			msg.put("mapper_id", myId);
			if (finalResultJSONObject != null)
			{
				msg.put("mapper_result", finalResultJSONObject);
			}
			else if (finalResultJSONArray != null)
			{
				msg.put("mapper_result", finalResultJSONArray);
			}
			context.sendToRunningFunctionInSession(nextReducerId, msg, false);
		}
		else
		{
			String nextReceiver = event2.getString("final_next");
			if (finalResultJSONObject != null)
			{
				context.addWorkflowNext(nextReceiver, finalResultJSONObject);
			}
			else if (finalResultJSONArray != null)
			{
				context.addWorkflowNext(nextReceiver, finalResultJSONArray);
			}
		}
		
		return "";
	}
}