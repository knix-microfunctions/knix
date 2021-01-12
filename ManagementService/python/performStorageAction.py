#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import base64

VALID_STORAGE_DATA_TYPES = set(["kv", "map", "set", "counter"])
VALID_ACTIONS = {}
VALID_ACTIONS["kv"] = set(["getdata", "deletedata", "putdata", "listkeys"])
VALID_ACTIONS["map"] = set(["createmap", "getmapentry", "putmapentry", "deletemapentry", "retrievemap", "containsmapkey", "getmapkeys", "clearmap", "deletemap", "listmaps"])
VALID_ACTIONS["set"] = set(["createset", "addsetentry", "removesetentry", "containssetitem", "retrieveset", "clearset", "deleteset", "listsets"])
VALID_ACTIONS["counter"] = set(["createcounter", "getcounter", "incrementcounter", "decrementcounter", "deletecounter", "listcounters"])

# for checking the types of the required parameters for corresponding data type and action
REQUIRED_PARAMETERS = {}

# KV operations
REQUIRED_PARAMETERS["getdata"] = {}
REQUIRED_PARAMETERS["getdata"]["key"] = "str"

REQUIRED_PARAMETERS["putdata"] = {}
REQUIRED_PARAMETERS["putdata"]["key"] = "str"
REQUIRED_PARAMETERS["putdata"]["value"] = "str"

REQUIRED_PARAMETERS["deletedata"] = {}
REQUIRED_PARAMETERS["deletedata"]["key"] = "str"

REQUIRED_PARAMETERS["listkeys"] = {}
REQUIRED_PARAMETERS["listkeys"]["start"] = "int"
REQUIRED_PARAMETERS["listkeys"]["count"] = "int"

# map operations
REQUIRED_PARAMETERS["createmap"] = {}
REQUIRED_PARAMETERS["createmap"]["mapname"] = "str"

REQUIRED_PARAMETERS["getmapentry"] = {}
REQUIRED_PARAMETERS["getmapentry"]["mapname"] = "str"
REQUIRED_PARAMETERS["getmapentry"]["key"] = "str"

REQUIRED_PARAMETERS["putmapentry"] = {}
REQUIRED_PARAMETERS["putmapentry"]["mapname"] = "str"
REQUIRED_PARAMETERS["putmapentry"]["key"] = "str"
REQUIRED_PARAMETERS["putmapentry"]["value"] = "str"

REQUIRED_PARAMETERS["deletemapentry"] = {}
REQUIRED_PARAMETERS["deletemapentry"]["mapname"] = "str"
REQUIRED_PARAMETERS["deletemapentry"]["key"] = "str"

REQUIRED_PARAMETERS["retrievemap"] = {}
REQUIRED_PARAMETERS["retrievemap"]["mapname"] = "str"

REQUIRED_PARAMETERS["containsmapkey"] = {}
REQUIRED_PARAMETERS["containsmapkey"]["mapname"] = "str"
REQUIRED_PARAMETERS["containsmapkey"]["key"] = "str"

REQUIRED_PARAMETERS["getmapkeys"] = {}
REQUIRED_PARAMETERS["getmapkeys"]["mapname"] = "str"

REQUIRED_PARAMETERS["clearmap"] = {}
REQUIRED_PARAMETERS["clearmap"]["mapname"] = "str"

REQUIRED_PARAMETERS["deletemap"] = {}
REQUIRED_PARAMETERS["deletemap"]["mapname"] = "str"

REQUIRED_PARAMETERS["listmaps"] = {}
REQUIRED_PARAMETERS["listmaps"]["start"] = "int"
REQUIRED_PARAMETERS["listmaps"]["count"] = "int"

# set operations
REQUIRED_PARAMETERS["createset"] = {}
REQUIRED_PARAMETERS["createset"]["setname"] = "str"

REQUIRED_PARAMETERS["addsetentry"] = {}
REQUIRED_PARAMETERS["addsetentry"]["setname"] = "str"
REQUIRED_PARAMETERS["addsetentry"]["item"] = "str"

REQUIRED_PARAMETERS["removesetentry"] = {}
REQUIRED_PARAMETERS["removesetentry"]["setname"] = "str"
REQUIRED_PARAMETERS["removesetentry"]["item"] = "str"

REQUIRED_PARAMETERS["containssetitem"] = {}
REQUIRED_PARAMETERS["containssetitem"]["setname"] = "str"
REQUIRED_PARAMETERS["containssetitem"]["item"] = "str"

REQUIRED_PARAMETERS["retrieveset"] = {}
REQUIRED_PARAMETERS["retrieveset"]["setname"] = "str"

REQUIRED_PARAMETERS["clearset"] = {}
REQUIRED_PARAMETERS["clearset"]["setname"] = "str"

REQUIRED_PARAMETERS["deleteset"] = {}
REQUIRED_PARAMETERS["deleteset"]["setname"] = "str"

REQUIRED_PARAMETERS["listsets"] = {}
REQUIRED_PARAMETERS["listsets"]["start"] = "int"
REQUIRED_PARAMETERS["listsets"]["count"] = "int"

# counter operations
REQUIRED_PARAMETERS["createcounter"] = {}
REQUIRED_PARAMETERS["createcounter"]["countername"] = "str"
REQUIRED_PARAMETERS["createcounter"]["countervalue"] = "int"

REQUIRED_PARAMETERS["getcounter"] = {}
REQUIRED_PARAMETERS["getcounter"]["countername"] = "str"

REQUIRED_PARAMETERS["incrementcounter"] = {}
REQUIRED_PARAMETERS["incrementcounter"]["countername"] = "str"
REQUIRED_PARAMETERS["incrementcounter"]["increment"] = "int"

REQUIRED_PARAMETERS["decrementcounter"] = {}
REQUIRED_PARAMETERS["decrementcounter"]["countername"] = "str"
REQUIRED_PARAMETERS["decrementcounter"]["decrement"] = "int"

REQUIRED_PARAMETERS["deletecounter"] = {}
REQUIRED_PARAMETERS["deletecounter"]["countername"] = "str"

REQUIRED_PARAMETERS["listcounters"] = {}
REQUIRED_PARAMETERS["listcounters"]["start"] = "int"
REQUIRED_PARAMETERS["listcounters"]["count"] = "int"

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    print(data)

    message = ''
    success = False
    response = {}
    response_data = {"status": False}
    dlc = None

    try:
        '''
        {
            "action": "performStorageAction",
            "data": {                          <this is what is contained in 'data' variable of this function>
                "user": { "token" : token },   <must come as part of user request>
                "storage": {...}               <must come as part of user request> (see handle_storage_action)
                "email": "...",                <added automatically by management service entry>
                "storage_userid": "...",       <added automatically by management service entry>
                "usertoken": "..."             <added automatically by management service entry>
            }
        }
        '''
        valid, message = validate_data(data)
        if not valid:
            raise Exception("Invalid data provided. " + message)

        storage = data['storage']
        storage_userid = data["storage_userid"]

        dlc = None

        if "workflowid" in storage and storage["workflowid"] is not None and storage["workflowid"] != "":
            dlc = sapi.get_privileged_data_layer_client(is_wf_private=True, sid=storage["workflowid"])
        elif "tableName" in storage and storage["tableName"] is not None:
            dlc = sapi.get_privileged_data_layer_client(storage_userid, tableName=storage["tableName"])
        else:
            dlc = sapi.get_privileged_data_layer_client(storage_userid)

        success, message, response_data = handle_storage_action(storage, dlc)

    except Exception as e:
        success = False
        message = "Exception: " + str(e)

    if dlc is not None:
        dlc.shutdown()

    if success:
        response["status"] = "success"
        response_data["message"] = "Successful storage op: " + message
        response["data"] = response_data
    else:
        response["status"] = "failure"
        response_data["message"] = "Error while performing storage operation; " + message
        response["data"] = response_data
        print("[StorageAction] Error: " + str(response_data))

    '''
    {
        "status": "success" or "failure",    <always included in response>
        "data": {
            "message": "...",    <always included in response>
            "status": True or False  <boolean, always included in reponse>
            "value": "..."  <string, incase of getdata request>
            "keylist": []  <list, incase of listkeys request>
        }
    }
    '''
    return response

def handle_storage_action(storage, dlc):
    '''
    "storage": {
        "workflowid": <workflowid> OR non-existing (i.e., user-level storage)
        "data_type": "", "kv", "map", "set", "counter" (if data_type = "", it is assumed that it is "kv")
        "parameters": <must come as part of user request> (see handle_storage_action_<data_type>)
    }
    '''

    print(storage)

    message = ''
    response_data = {"status": False}
    storage_data_type = storage["data_type"]
    parameters = storage["parameters"]

    if storage_data_type == "kv":
        status, message, response_data = handle_storage_action_kv(parameters, dlc)
    elif storage_data_type == "map":
        status, message, response_data = handle_storage_action_map(parameters, dlc)
    elif storage_data_type == "set":
        status, message, response_data = handle_storage_action_set(parameters, dlc)
    elif storage_data_type == "counter":
        status, message, response_data = handle_storage_action_counter(parameters, dlc)
    else:
        print("storage data type not valid")

    return status, message, response_data

def handle_storage_action_kv(parameters, dlc):
    '''
    "parameters": <must come as part of user request> (see handle_storage_action_<data_type>)
    {
        "action": "getdata",  OR  "deletedata",  OR  "putdata",  OR  "listkeys",  <case insensitive>
        "key": "keyname",               (for getdata, deletedata, and putdata)
        "value": "stringdata",          (for putdata)
        "start": 1,                     (int, for listkeys)
        "count": 2000,                  (int, for listkeys)
    }
    '''
    storage_action = parameters['action'].lower()
    response_data = {}

    if storage_action == "listkeys":
        message = storage_action + ", start: " + str(parameters['start']) + ", count: " + str(parameters['count']) + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    else:
        message = storage_action + ", key: " + parameters['key'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    print("[StorageAction] " + message)

    status = False

    if storage_action == 'getdata':
        val = dlc.get(parameters['key'])
        if val is not None:
            # the GUI expects this to be base64-encoded
            val = bytes(val, 'utf-8')
            val = base64.b64encode(val).decode()

        response_data['value'] = val
        status = True

    elif storage_action == 'deletedata':
        status = dlc.delete(parameters['key'])

    elif storage_action == 'putdata':
        status = dlc.put(parameters['key'], parameters['value'])

    elif storage_action == 'listkeys':
        status = True
        listkeys_response = dlc.listKeys(parameters['start'], parameters['count'])
        response_data['keylist'] = listkeys_response   # should always be a list. Empty list is a valid response

    if not status:
        message = storage_action + " returned False. " + message

    response_data['status'] = status
    return status, message, response_data

def handle_storage_action_map(parameters, dlc):
    '''
    "parameters": <must come as part of user request> (see handle_storage_action_<data_type>)
    {
        "action": "createmap", OR "putmapentry", OR "getmapentry", OR "deletemapentry", OR "retrievemap", "containsmapkey", OR "getmapkeys", OR "clearmap", OR "deletemap", OR "listmaps"; <case insensitive>
        "mapname": (for all operations, except for listmaps)
        "key": "keyname",               (for *mapentry)
        "value": "stringdata",          (for putmapentry)
        "start": 1,                     (int, for listmaps)
        "count": 2000,                  (int, for listmaps)
    }
    '''
    storage_action = parameters['action'].lower()
    response_data = {}

    if storage_action == "listmaps":
        message = storage_action + ", start: " + str(parameters['start']) + ", count: " + str(parameters['count']) + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    else:
        message = storage_action + ", mapname: " + parameters['mapname'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    print("[StorageAction] " + message)

    status = False

    if storage_action == "createmap":
        status = dlc.createMap(parameters["mapname"])

    elif storage_action == "putmapentry":
        status = dlc.putMapEntry(parameters["mapname"], parameters["key"], parameters["value"])

    elif storage_action == "getmapentry":
        val = dlc.getMapEntry(parameters["mapname"], parameters["key"])
        if val is not None:
            val = bytes(val, 'utf-8')
            val = base64.b64encode(val).decode()

        response_data['value'] = val
        status = True

    elif storage_action == "deletemapentry":
        status = dlc.deleteMapEntry(parameters["mapname"], parameters["key"])

    elif storage_action == "retrievemap":
        mapentries = dlc.retrieveMap(parameters["mapname"])
        response_data["mapentries"] = mapentries
        status = True

    elif storage_action == "containsmapkey":
        ret = dlc.containsMapKey(parameters["mapname"], parameters["key"])
        response_data["containskey"] = ret
        status = True

    elif storage_action == "getmapkeys":
        mapkeys = dlc.getMapKeys(parameters["mapname"])
        response_data["mapkeys"] = mapkeys
        status = True

    elif storage_action == "clearmap":
        status = dlc.clearMap(parameters["mapname"])

    elif storage_action == "deletemap":
        status = dlc.deleteMap(parameters["mapname"])

    elif storage_action == "listmaps":
        maplist = dlc.getMapNames(parameters["start"], parameters["count"])
        response_data["maplist"] = maplist
        status = True

    if not status:
        if storage_action == "getmapentry":
            message = storage_action + " returned None value. " + message
        else:
            message = storage_action + " returned False. " + message
        message = storage_action + " returned False. " + message

    response_data["status"] = status

    return status, message, response_data

def handle_storage_action_set(parameters, dlc):
    '''
    "parameters": <must come as part of user request> (see handle_storage_action_<data_type>)
    {
        "action": "createset", OR "addsetentry", OR "removesetentry", OR "containssetitem", OR "retrieveset", OR "clearset", OR "deleteset", OR "listsets"; <case insensitive>
        "setname": (for all operations, except for listsets)
        "item": "item",               (for *setentry)
        "start": 1,                     (int, for listsets)
        "count": 2000,                  (int, for listsets)
    }
    '''
    storage_action = parameters['action'].lower()
    response_data = {}

    if storage_action == "listsets":
        message = storage_action + ", start: " + str(parameters['start']) + ", count: " + str(parameters['count']) + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    else:
        message = storage_action + ", setname: " + parameters['setname'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    print("[StorageAction] " + message)

    status = False

    if storage_action == "createset":
        status = dlc.createSet(parameters["setname"])

    elif storage_action == "addsetentry":
        status = dlc.addSetEntry(parameters["setname"], parameters["item"])

    elif storage_action == "removesetentry":
        status = dlc.removeSetEntry(parameters["setname"], parameters["item"])

    elif storage_action == "containssetitem":
        ret = dlc.containsSetItem(parameters["setname"], parameters["item"])
        response_data["containsitem"] = ret
        status = True

    elif storage_action == "retrieveset":
        items = dlc.retrieveSet(parameters["setname"])
        response_data["items"] = items
        status = True

    elif storage_action == "clearset":
        status = dlc.clearSet(parameters["setname"])

    elif storage_action == "deleteset":
        status = dlc.deleteSet(parameters["setname"])

    elif storage_action == "listsets":
        setlist = dlc.getSetNames(parameters["start"], parameters["count"])
        response_data["setlist"] = setlist
        status = True

    if not status:
        message = storage_action + " returned False. " + message

    response_data["status"] = status

    return status, message, response_data

def handle_storage_action_counter(parameters, dlc):
    '''
    "parameters": <must come as part of user request> (see handle_storage_action_<data_type>)
    {
        "action": "createcounter", OR "getcounter", OR "incrementcounter", OR "decrementcounter", OR "deletecounter", OR "listcounters"; <case insensitive>
        "countername": (for all operations, except for listcounters)
        "countervalue": <value>,   (int, for createcounter)
        "increment": <value>,      (int, for incrementcounter)
        "decrement": <value>       (int, for decrementcounter)
        "start": 1,                     (int, for listcounters)
        "count": 2000,                  (int, for listcounters)
    }
    '''
    storage_action = parameters['action'].lower()
    response_data = {}

    if storage_action == "listcounters":
        message = storage_action + ", start: " + str(parameters['start']) + ", count: " + str(parameters['count']) + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    else:
        message = storage_action + ", countername: " + parameters['countername'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
    print("[StorageAction] " + message)

    status = False

    if storage_action == "createcounter":
        status = dlc.createCounter(parameters["countername"], parameters["countervalue"])

    elif storage_action == "getcounter":
        cv = dlc.getCounter(parameters["countername"])
        response_data["countervalue"] = cv
        status = True

    elif storage_action == "incrementcounter":
        status = dlc.incrementCounter(parameters["countername"], parameters["increment"])

    elif storage_action == "decrementcounter":
        status = dlc.decrementCounter(parameters["countername"], parameters["decrement"])

    elif storage_action == "deletecounter":
        status = dlc.deleteCounter(parameters["countername"])

    elif storage_action == "listcounters":
        counters = dlc.getCounterNames(parameters["start"], parameters["count"])
        response_data["counterlist"] = counters
        status = True

    if not status:
        message = storage_action + " returned False. " + message

    response_data["status"] = status

    return status, message, response_data

def validate_data(data):
    valid = True
    message = "validated"

    params_to_validate = {}
    params_to_validate["storage_userid"] = "str"
    params_to_validate["storage"] = "dict"

    for param in params_to_validate:
        valid, message = validate_parameter(data, param, params_to_validate[param])
        if not valid:
            message = "Invalid/missing parameter: " + message
            break

    if valid:
        storage_params_to_validate = {}
        storage_params_to_validate["data_type"] = "str"
        storage_params_to_validate["parameters"] = "dict"
        for param in storage_params_to_validate:
            valid, message = validate_parameter(data["storage"], param, storage_params_to_validate[param])
            if not valid:
                message = "Invalid/missing parameter: " + message
                break

    if valid:
        data_type = data["storage"]["data_type"].lower()

        # special case for backward-compatibility
        if data_type == "":
            data_type = "kv"
            data["storage"]["data_type"] = "kv"

        if data_type not in VALID_STORAGE_DATA_TYPES:
            message = "Invalid data type specified."
            valid = False

    if valid:
        parameters = data["storage"]["parameters"]
        valid, message = validate_parameter(parameters, "action", "str")
        if not valid:
            message = "Invalid/missing parameter: " + message

    if valid:
        action = data["storage"]["parameters"]["action"].lower()
        if action not in VALID_ACTIONS[data_type]:
            message = "Unknown storage action: " + action + " for data type: " + data_type
            valid = False

    if valid:
        for req_param in REQUIRED_PARAMETERS[action]:
            valid, message = validate_parameter(parameters, req_param, REQUIRED_PARAMETERS[action][req_param])
            if not valid:
                message = "Invalid/missing parameter: " + message
                break

    if valid:
        if action in ("listkeys", "listmaps", "listsets", "listcounters"):
            if parameters["start"] < 0 or parameters["start"] > 1000000:
                valid = False
                message = "'start' should be between 0 and 1000000."
            elif parameters["count"] < 0 or parameters["count"] > 1000000:
                valid = False
                message = "'count' should be between 0 and 1000000."

    return valid, message

def validate_parameter(data, keyname, keytype):
    status = True
    message = "validated"
    if keyname not in data:
        status = False
        message = "'" + keyname + "' is missing."
    elif data[keyname] is None:
        status = False
        message = "'" + keyname + "' is None."

    if (keytype == "int" and not isinstance(data[keyname], int)):
        status = False
        message = "'" + keyname + "' is not a " + keytype + "."
    elif (keytype == "str" and not isinstance(data[keyname], str)):
        return False, "'" + keyname + "' is not a " + keytype + "."
    elif (keytype == "dict" and not isinstance(data[keyname], dict)):
        return False, "'" + keyname + "' is not a " + keytype + "."

    return status, message
