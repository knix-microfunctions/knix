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

public class TestDataLayerOperations
{
    public Object handle(Object event, MicroFunctionsAPI context)
    {
        HashMap<String, Boolean> testResultMap = new HashMap<String, Boolean>();

        // isPrivate = true
        testKVOperations(context, true, testResultMap);
        testKVOperations(context, false, testResultMap);

        testCounterOperations(context, true, testResultMap);
        testCounterOperations(context, false, testResultMap);

        testSetOperations(context, true, testResultMap);
        testSetOperations(context, false, testResultMap);

        testMapOperations(context, true, testResultMap);
        testMapOperations(context, false, testResultMap);

        return testResultMap;
    }

    private void testKVOperations(MicroFunctionsAPI context,
            boolean isPrivate,
            HashMap<String, Boolean> testResultMap)
    {
        List<String> keys = context.getKeys(isPrivate);
        int oldLength = keys.size();

        boolean success = false;
        String postfix = "";
        if (isPrivate)
        {
            postfix = "Private";
        }

        Random r = new Random();
        String key = "key_" + System.currentTimeMillis();
        // should be empty string
        String gotValue = context.get(key, isPrivate);

        String value = "" + r.nextInt(100000);

        context.put(key, value, isPrivate);

        // should be equal to 'value'
        String gotValue2 = context.get(key, isPrivate);

        sleepALittle();

        List<String> keys2 = context.getKeys(isPrivate);
        int newLength = keys2.size();

        context.delete(key, isPrivate);

        // should be equal to empty string
        String gotValue3 = context.get(key, isPrivate);
        if (gotValue == null && value.equalsIgnoreCase(gotValue2) && gotValue3 == null)
        {
            success = true;
        }
        testResultMap.put("testPut" + postfix, success);
        testResultMap.put("testGet" + postfix, success);
        testResultMap.put("testDelete" + postfix, success);

        sleepALittle();
        sleepALittle();

        List<String> keys3 = context.getKeys(isPrivate);
        int newLength2 = keys3.size();

        success = false;
        if ((oldLength + 1 == newLength) && (oldLength == newLength2))
        {
            success = true;
        }
        testResultMap.put("testGetKeys" + postfix, success);

    }

    private void testCounterOperations(MicroFunctionsAPI context,
            boolean isPrivate,
            HashMap<String, Boolean> testResultMap)
    {
        boolean success = false;
        String postfix = "";
        if (isPrivate)
        {
            postfix = "Private";
        }

        Random r = new Random();
        String countername = "myCounter" + r.nextInt(10000);
        long initialvalue = r.nextInt(1000);

        List<String> names = context.getCounterNames(isPrivate);

        context.createCounter(countername, initialvalue, isPrivate);

        long oldvalue = context.getCounterValue(countername, isPrivate);

        sleepALittle();

        context.log("createCounter, " + isPrivate + ", countername: " + countername);
        List<String> names2 = context.getCounterNames(isPrivate);

        context.log("counter, " + isPrivate + ", countername: " + countername);
        context.log("counter, " + isPrivate + ", initialvalue: " + initialvalue);

        context.log("counter names (old): " + names + " (new): " + names2);

        if (names.indexOf(countername) == -1 && names2.indexOf(countername) != -1)
        {
            success = true;
        }

        testResultMap.put("testCreateCounter" + postfix, success);

        success = false;
        if (oldvalue == initialvalue)
        {
            success = true;
        }

        testResultMap.put("testGetCounterValue" + postfix, success);
        testResultMap.put("testGetCounterNames" + postfix, success);

        boolean success2 = false;
        long increment = r.nextInt(1000);
        context.incrementCounter(countername, increment, isPrivate);

        sleepALittle();

        long newvalue = context.getCounterValue(countername, isPrivate);

        context.log("incrementCounter, " + isPrivate + ", oldvalue: " + oldvalue);
        context.log("incrementCounter, " + isPrivate + ", increment: " + increment);
        context.log("incrementCounter, " + isPrivate + ", newvalue: " + newvalue);

        if (newvalue == (oldvalue + increment))
        {
            success2 = true;
        }

        testResultMap.put("testIncrementCounter" + postfix, success2);

        boolean success3 = false;
        long oldvalue2 = context.getCounterValue(countername, isPrivate);

        sleepALittle();

        long decrement = r.nextInt(1000);
        context.decrementCounter(countername, decrement, isPrivate);

        sleepALittle();

        long newvalue2 = context.getCounterValue(countername, isPrivate);

        context.log("decrementCounter, " + isPrivate + ", oldvalue2: " + oldvalue2);
        context.log("decrementCounter, " + isPrivate + ", decrement: " + decrement);
        context.log("decrementCounter, " + isPrivate + ", newvalue2: " + newvalue2);
        if (newvalue2 == (oldvalue2 - decrement))
        {
            success3 = true;
        }

        testResultMap.put("testDecrementCounter" + postfix, success3);

        boolean success4 = false;
        context.deleteCounter(countername, isPrivate);

        sleepALittle();
        List<String> names3 = context.getCounterNames(isPrivate);

        int i = 0;
        while (names3.indexOf(countername) != -1 && i <= 5)
        {
            context.log("waiting for deletion to sync... deleteCounter, " + isPrivate + ", names3: " + names3.toString());
            sleepALittle();
            i++;
            names3 = context.getCounterNames(isPrivate);
        }

        context.log("deleteCounter, " + isPrivate + ", names3: " + names3.toString());

        if (names3.indexOf(countername) == -1)
        {
            success4 = true;
        }

        testResultMap.put("testDeleteCounter" + postfix, success4);
    }

    private void testMapOperations(MicroFunctionsAPI context,
            boolean isPrivate,
            HashMap<String, Boolean> testResultMap)
    {
        boolean success = false;
        String postfix = "";
        if (isPrivate)
        {
            postfix = "Private";
        }

        Random r = new Random();
        String mapname = "myMap" + r.nextInt(10000);

        List<String> names = context.getMapNames(isPrivate);

        boolean success2 = false;
        String key = "k" + r.nextInt(10000);
        String value = "v" + r.nextInt(10000);
        String key2 = "k" + r.nextInt(10000);
        String value2 = "v" + r.nextInt(10000);

        context.putMapEntry(mapname, key, value, isPrivate);
        context.putMapEntry(mapname, key2, value2, isPrivate);

        List<String> names2 = context.getMapNames(isPrivate);

        int i = 0;
        while (names2.indexOf(mapname) == -1 && i <= 5)
        {
            context.log("waiting creation to sync... createMap, " + isPrivate + ", names2: " + names2.toString());
            i++;
            names2 = context.getMapNames(isPrivate);
        }

        context.log("createMap, " + isPrivate + ", names: " + names.toString());
        context.log("createMap, " + isPrivate + ", names2: " + names2.toString());

        if (names.indexOf(mapname) == -1 && names2.indexOf(mapname) != -1)
        {
            success = true;
        }

        testResultMap.put("testCreateMap" + postfix, success);
        testResultMap.put("testGetMapNames" + postfix, success);

        Map<String, String> map = context.retrieveMap(mapname, isPrivate);
        if (map.containsKey(key) && map.containsKey(key2) && map.containsValue(value) && map.containsValue(value2))
        {
            success2 = true;
        }

        testResultMap.put("testRetrieveMap" + postfix, success2);

        boolean success3 = false;
        String gotValue = context.getMapEntry(mapname, key, isPrivate);
        String gotValue2 = context.getMapEntry(mapname, key2, isPrivate);
        String gotValue3 = context.getMapEntry(mapname, "nonExistingKey", isPrivate);

        if (value.equalsIgnoreCase(gotValue) && value2.equalsIgnoreCase(gotValue2) && gotValue3 == null)
        {
            success3 = true;
        }

        testResultMap.put("testPutMapEntry" + postfix, success3);
        testResultMap.put("testGetMapEntry" + postfix, success3);

        boolean success4 = false;

        context.deleteMapEntry(mapname, key2, isPrivate);

        sleepALittle();

        Set<String> keys = context.getMapKeys(mapname, isPrivate);
        if (!keys.contains(key2))
        {
            success4 = true;
        }

        testResultMap.put("testDeleteMapEntry" + postfix, success4);
        testResultMap.put("testGetMapKeys" + postfix, success4);

        boolean success5 = false;

        boolean containsItem = context.containsMapKey(mapname, key, isPrivate);
        boolean containsItem2 = context.containsMapKey(mapname, key2, isPrivate);
        if (containsItem && !containsItem2)
        {
            success5 = true;
        }

        testResultMap.put("testContainsMapKey" + postfix, success5);

        boolean success6 = false;
        context.clearMap(mapname, isPrivate);
        sleepALittle();
        Set<String> keys2 = context.getMapKeys(mapname, isPrivate);
        if (keys2.size() == 0)
        {
            success6 = true;
        }
        testResultMap.put("testClearMap" + postfix, success6);

        boolean success7 = false;
        context.deleteMap(mapname, isPrivate);

        sleepALittle();
        List<String> names3 = context.getMapNames(isPrivate);

        i = 0;
        while (names3.indexOf(mapname) != -1 && i <= 5)
        {
            context.log("waiting for deletion to sync... deleteMap, " + isPrivate + ", names3: " + names3.toString());
            sleepALittle();
            i++;
            names3 = context.getMapNames(isPrivate);
        }

        context.log("deleteMap, " + isPrivate + ", names3: " + names3.toString());

        if (names3.indexOf(mapname) == -1)
        {
            success7 = true;
        }

        testResultMap.put("testDeleteMap" + postfix, success7);

    }

    private void testSetOperations(MicroFunctionsAPI context,
            boolean isPrivate,
            HashMap<String, Boolean> testResultMap)
    {
        boolean success = false;
        String postfix = "";
        if (isPrivate)
        {
            postfix = "Private";
        }

        Random r = new Random();
        String setname = "mySet" + r.nextInt(10000);

        List<String> names = context.getSetNames(isPrivate);

        boolean success2 = false;
        String item = "" + r.nextInt(10000);
        String item2 = "a" + r.nextInt(10000);

        context.addSetEntry(setname, item, isPrivate);
        context.addSetEntry(setname, item2, isPrivate);

        List<String> names2 = context.getSetNames(isPrivate);

        int i = 0;
        while (names2.indexOf(setname) == -1 && i <= 5)
        {
            context.log("waiting creation to sync... createSet, " + isPrivate + ", names2: " + names2.toString());
            i++;
            names2 = context.getSetNames(isPrivate);
        }

        context.log("createSet, " + isPrivate + ", names: " + names.toString());
        context.log("createSet, " + isPrivate + ", names2: " + names2.toString());

        if (names.indexOf(setname) == -1 && names2.indexOf(setname) != -1)
        {
            success = true;
        }

        testResultMap.put("testCreateSet" + postfix, success);
        testResultMap.put("testGetSetNames" + postfix, success);

        Set<String> items = context.retrieveSet(setname, isPrivate);
        if (items.contains(item) && items.contains(item2))
        {
            success2 = true;
        }

        testResultMap.put("testAddSetEntry" + postfix, success2);
        testResultMap.put("testRetrieveSet" + postfix, success2);

        boolean success3 = false;
        context.removeSetEntry(setname, item2, isPrivate);

        sleepALittle();
        Set<String> items2 = context.retrieveSet(setname, isPrivate);
        if (items2.contains(item) && !items2.contains(item2))
        {
            success3 = true;
        }

        testResultMap.put("testRemoveSetEntry" + postfix, success3);

        boolean success4 = false;

        boolean containsItem = context.containsSetItem(setname, item, isPrivate);
        boolean containsItem2 = context.containsSetItem(setname, item2, isPrivate);
        if (containsItem && !containsItem2)
        {
            success4 = true;
        }

        testResultMap.put("testContainsSetItem" + postfix, success4);

        boolean success5 = false;

        context.clearSet(setname, isPrivate);

        sleepALittle();

        Set<String> items4 = context.retrieveSet(setname, isPrivate);
        if (items4.size() == 0)
        {
            success5 = true;
        }

        testResultMap.put("testClearSet" + postfix, success5);

        boolean success6 = false;
        context.deleteSet(setname, isPrivate);

        sleepALittle();
        List<String> names3 = context.getSetNames(isPrivate);

        i = 0;
        while (names3.indexOf(setname) != -1 && i <= 5)
        {
            context.log("waiting for deletion to sync... deleteSet, " + isPrivate + ", names3: " + names3.toString());
            sleepALittle();
            i++;
            names3 = context.getSetNames(isPrivate);
        }

        context.log("deleteSet, " + isPrivate + ", names3: " + names3.toString());

        if (names3.indexOf(setname) == -1)
        {
            success6 = true;
        }

        testResultMap.put("testDeleteSet" + postfix, success6);

    }

    // ======================================

    private void sleepALittle()
    {
        try
        {
            Thread.sleep(1500);
        }
        catch (Exception e)
        {
            e.printStackTrace();
        }
    }

}
