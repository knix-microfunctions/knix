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

import json

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    message = ''
    success = False
    response = {}
    response_data = {"status": False}
    dlc = None

    try:
        '''
        {
            "action": "performStorageAction", 
            "data": { 
                "user": { "token" : token },   <must come as part of user request>
                "storage": {...}               <must come as part of user request> (see handleStorageAction) 
                "email": "...",                <added automatically by management service entry>
                "storage_userid": "...",       <added automatically by management service entry>
                "usertoken": "..."             <added automatically by management service entry>
            }
        }
        '''
        verified, message = verifyData(data)
        if verified == False:
            raise Exception("Invalid data provided. " + message)
        
        storage = data['storage']
        storage_userid = data["storage_userid"]
        dlc = sapi.get_privileged_data_layer_client(storage_userid)
        
        success, message, response_data = handleStorageAction(storage, dlc)

    except Exception as e:
        success = False
        message = "Error while performing storage operation; "+str(e)

    if dlc != None:
        dlc.shutdown()

    if success:
        response["status"] = "success"
        response_data["message"] = "Successful storage op: " + message
        response["data"] = response_data
    else:
        response["status"] = "failure"
        response_data["message"] = "Error while performing storage operation; "+str(e)
        response["data"] = response_data
        print(str(response))

    '''
    {
        "status": "success" or "failure",
        "data": {
            "message": "...",
            "status": True or False  <boolean>
            "value": ""  <incase of getdata request>
            "keylist": []  <incase of listkeys request>
        }
    }
    '''
    return response

def handleStorageAction(storage, dlc):
    '''
    "storage": {
        "action": "getdata",  OR  "deletedata",  OR  "putdata",  OR  "listkeys",
        "table": "tablename",
        "key": "keyname",              (for get, delete, and put)
        "value": "stringdata",         (for put)
        "start": 1,                    (int, for listkeys)
        "count": 500,                  (int, for listkeys)
    }
    '''

    message = ''
    response_data = {"status": False}
    storage_action = storage['action']

    if storage_action == 'getdata':
        message = "getdata: key:" + storage['key'] + ", table: " + storage['table'] + ", keyspace: " + dlc.keyspace
        val = dlc.get(storage['key'], tableName=storage['table'])
        if val == None:
            return False, "getdata returned None value. " + message, response_data
        response_data['value'] = val

    elif storage_action == 'deletedata':
        message = "deletedata: key:" + storage['key'] + ", table: " + storage['table'] + ", keyspace: " + dlc.keyspace
        status = dlc.delete(storage['key'], tableName=storage['table'])
        if status == False:
            return False, "deletedata returned False. " + message, response_data

    elif storage_action == 'putdata':
        message = "putdata: key:" + storage['key'] + ", table: " + storage['table'] + ", keyspace: " + dlc.keyspace
        status = dlc.put(storage['key'], storage['value'], tableName=storage['table'])
        if status == False:
            return False, "putdata returned False. " + message, response_data

    elif storage_action == 'listkeys':
        message = "listkeys: key:" + storage['key'] + ", table: " + storage['table'] + ", keyspace: " + dlc.keyspace
        keylist = dlc.listKeys(storage['start'], storage['count'], tableName=storage['table'])
        response_data['keylist'] = keylist 
        if keylist == []:
            return False, "listkeys returned and empty list. " + message, response_data
    else:
        return False, "Invalid operation specified", response_data
    
    response_data['status'] = True
    return True, message, response_data


def verifyData(data):
    verified, message = isValidString(data, 'storage_userid')
    if verified == False: 
        return False, "Invalid storage_userid. " + message

    if 'storage' not in data:
        return False, "Storage object not specified"
    
    storage = data['storage']
    if type(storage) != type({}):
        return False, "Storage data not specified as a dict"
    
    verified, message = isValidString(storage, 'action')
    if verified == False: 
        return False, "Invalid storage action specified. " + message

    verified, message = isValidString(storage, 'table')
    if verified == False: 
        return False, "Invalid table specified. " + message

    action = storage['action']
    validActions = set(['getdata', 'deletedata', 'putdata', 'listkeys'])
    if action not in validActions:
        return False, "Unknown storage action specified: " + action

    if action == 'getdata' or action == 'deletedata' or action == 'putdata':
        verified, message = isValidString(storage, 'key')
        if verified == False:
            return False, "Invalid key specified. " + message

    if action == 'putdata':
        verified, message = isValidString(storage, 'value')
        if verified == False:
            return False, "Invalid value specified. " + message 

    if action == 'listkeys':
        verified, message = isValidInt(storage, 'start')
        if verified == False:
            return False, "Invalid start specified. " + message 

        verified, message = isValidInt(storage, 'count')
        if verified == False:
            return False, "Invalid count specified. " + message 

    return True, "verified"

def isValidString(data, keyname):
    if keyname not in data:
        return False, "'" + keyname + "' is missing."
    if data[keyname] == None:
        return False, "'" + keyname + "' is None."
    if not isinstance(data[keyname], str):
        return False, "'" + keyname + "' is not a string."
    if data[keyname] == '':
        return False, "'" + keyname + "' is an empty string."
    return True, "verified"

def isValidInt(data, keyname):
    if keyname not in data:
        return False, "'" + keyname + "' is missing."
    if data[keyname] == None:
        return False, "'" + keyname + "' is None."
    if not isinstance(data[keyname], int):
        return False, "'" + keyname + "' is not an int."
    return True, "verified"

