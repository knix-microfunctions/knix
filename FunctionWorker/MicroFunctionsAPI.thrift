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
namespace java org.microfunctions.mfnapi

service MicroFunctionsAPIService {
    string ping(1:i32 n),

    void update_metadata(1: string metadata_name, 2: string metadata_value, 3: bool is_privileged_metadata),

    void send_to_running_function_in_session(1: string rgid, 2: string message, 3: bool send_now),  // message?
    void send_to_all_running_functions_in_session_with_function_name(1: string gname, 2: string message, 3: bool send_now),  // message
    void send_to_all_running_functions_in_session(1: string message, 2: bool send_now),  //message
    void send_to_running_function_in_session_with_alias(1: string als, 2: string message, 3: bool send_now),  // message

    list<string> get_session_update_messages(1: i32 count, 2: bool blck),

    void set_session_alias(1: string als),
    void unset_session_alias(),
    string get_session_alias(),
    void set_session_function_alias(1: string als, 2: string session_function_id),
    void unset_session_function_alias(1: string session_function_id),
    string get_session_function_alias(1: string session_function_id),
    map<string, string> get_all_session_function_aliases(),
    map<string, map<string, string>> get_alias_summary(),

    string get_session_id(),
    string get_session_function_id(),
    string get_session_function_id_with_alias(1: string als),
    list<string> get_all_session_function_ids(),

    bool is_still_running(),

    void add_workflow_next(1: string nxt, 2: string value),  // value
    void add_dynamic_next(1: string nxt, 2: string value),  // value
    void send_to_function_now(1: string destination, 2: string value),  // value
    void add_dynamic_workflow(1: list<map<string, string>> dynamic_trigger),  // dynamic_trigger
    list<map<string, string>> get_dynamic_workflow(),  // return value

    i64 get_remaining_time_in_millis(),
    void log(1: string text, 2: string level),
    string get_event_key(),
    string get_instance_id(),

    void put(1: string key, 2: string value, 3: bool is_private, 4: bool is_queued),
    string get(1: string key, 2: bool is_private),
    void remove(1: string key, 2: bool is_private, 3: bool is_queued),

    void createMap(1: string mapname, 2: bool is_private, 3: bool is_queued),
    void putMapEntry(1: string mapname, 2: string key, 3: string value, 4: bool is_private, 5: bool is_queued),
    string getMapEntry(1: string mapname, 2: string key, 3: bool is_private),
    void deleteMapEntry(1: string mapname, 2: string key, 3: bool is_private, 4: bool is_queued),
    bool containsMapKey(1: string mapname, 2: string key, 3: bool is_private),
    set<string> getMapKeys(1: string mapname, 2: bool is_private),
    void clearMap(1: string mapname, 2: bool is_private, 3: bool is_queued),
    void deleteMap(1: string mapname, 2: bool is_private, 3: bool is_queued),
    map<string, string> retrieveMap(1: string mapname, 2: bool is_private),
    list<string> getMapNames(1: i32 start_index, 2: i32 end_index, 3: bool is_private),

    void createSet(1: string setname, 2: bool is_private, 3: bool is_queued),
    void addSetEntry(1: string setname, 2: string item, 3: bool is_private, 4: bool is_queued),
    void removeSetEntry(1: string setname, 2: string item, 3: bool is_private, 4: bool is_queued),
    bool containsSetItem(1: string setname, 2: string item, 3: bool is_private),
    set<string> retrieveSet(1: string setname, 2: bool is_private),
    void clearSet(1: string setname, 2: bool is_private, 3: bool is_queued),
    void deleteSet(1: string setname, 2: bool is_private, 3: bool is_queued),
    list<string> getSetNames(1: i32 start_index, 2: i32 end_index, 3: bool is_private),

    void createCounter(1: string countername, 2: i64 count, 3: bool is_private, 4: bool is_queued),
    i64 getCounterValue(1: string countername, 2: bool is_private),
    bool incrementCounter(1: string countername, 2: i64 increment, 3: bool is_private, 4: bool is_queued),
    bool decrementCounter(1: string countername, 2: i64 decrement, 3: bool is_private, 4: bool is_queued),
    void deleteCounter(1: string countername, 2: bool is_private, 3: bool is_queued),
    list<string> getCounterNames(1: i32 start_index, 2: i32 end_index, 3: bool is_private),

    map<string, string> get_transient_data_output(1: bool is_private),
    map<string, bool> get_data_to_be_deleted(1: bool is_private)
}

