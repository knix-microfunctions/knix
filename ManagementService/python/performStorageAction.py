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
            "data": {                          <this is what is contained in 'data' variable of this function>
                "user": { "token" : token },   <must come as part of user request>
                "storage": {...}               <must come as part of user request> (see handleStorageAction)
                "email": "...",                <added automatically by management service entry>
                "storage_userid": "...",       <added automatically by management service entry>
                "usertoken": "..."             <added automatically by management service entry>
            }
        }
        '''
        verified, message = verifyData(data)
        if not verified:
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
            

        success, message, response_data = handleStorageAction(storage, dlc)

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

def handleStorageAction(storage, dlc):
    '''
    "storage": {
        "workflowid": <workflowid> OR non-existing (i.e., user-level storage)
        "tableName": name of table to perform storage operations on
        "action": "getdata",  OR  "deletedata",  OR  "putdata",  OR  "listkeys",  <case insensitive>
        "key": "keyname",               (for getdata, deletedata, and putdata)
        "value": "stringdata",          (for putdata)
        "start": 1,                     (int, for listkeys)
        "count": 2000,                  (int, for listkeys)
    }
    '''

    message = ''
    
    response_data = {"status": False}
    storage_action = storage['action'].lower()

    if storage_action == 'getdata':
        message = "getdata, key:" + storage['key'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
        print("[StorageAction] " + message)
        val = dlc.get(storage['key'])
        if val is None:
            return False, "getdata returned None value. " + message, response_data

        response_data['value'] = val
        
    elif storage_action == 'deletedata':
        message = "deletedata, key:" + storage['key'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
        print("[StorageAction] " + message)
        status = dlc.delete(storage['key'])
        if not status:
            return False, "deletedata returned False. " + message, response_data

    elif storage_action == 'putdata':
        message = "putdata, key: " + storage['key'] + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
        print("[StorageAction] " + message)
        status = dlc.put(storage['key'], storage['value'])
        if not status:
            return False, "putdata returned False. " + message, response_data

    elif storage_action == 'listkeys':
        message = "listkeys, start: " + str(storage['start']) + ", count: " + str(storage['count']) + ", table: " + dlc.tablename + ", keyspace: " + dlc.keyspace
        print("[StorageAction] " + message)
        listkeys_response = dlc.listKeys(storage['start'], storage['count'])
        response_data['keylist'] = listkeys_response   # should always be a list. Empty list is a valid response

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
    if not verified:
        return False, "Invalid storage action specified. " + message

    action = storage['action'].lower()
    validActions = set(['getdata', 'deletedata', 'putdata', 'listkeys'])
    if action not in validActions:
        return False, "Unknown storage action specified: " + action

    if action == 'getdata' or action == 'deletedata' or action == 'putdata':
        verified, message = isValidString(storage, 'key')
        if not verified:
            return False, "Invalid key specified. " + message

    # _XXX_: 'value' can be an empty string
    #if action == 'putdata':
    #    verified, message = isValidString(storage, 'value')
    #    if verified == False:
    #        return False, "Invalid value specified. " + message

    if action == 'listkeys':
        verified, message = isValidInt(storage, 'start')
        if not verified:
            return False, "Invalid start specified. " + message

        verified, message = isValidInt(storage, 'count')
        if not verified:
            return False, "Invalid count specified. " + message
        if storage['count'] > 1000000:
            return False, "Invalid count specified. 'count' too high. It should be < 1000000."

    return True, "verified"

def isValidString(data, keyname):
    if keyname not in data:
        return False, "'" + keyname + "' is missing."
    if data[keyname] is None:
        return False, "'" + keyname + "' is None."
    if not isinstance(data[keyname], str):
        return False, "'" + keyname + "' is not a string."
    if data[keyname] == '':
        return False, "'" + keyname + "' is an empty string."
    return True, "verified"

def isValidInt(data, keyname):
    if keyname not in data:
        return False, "'" + keyname + "' is missing."
    if data[keyname] is None:
        return False, "'" + keyname + "' is None."
    if not isinstance(data[keyname], int):
        return False, "'" + keyname + "' is not an int."
    if data[keyname] < 0:
        return False, "'" + keyname + "' is an int smaller than 0. It should be >= 0."
    return True, "verified"

