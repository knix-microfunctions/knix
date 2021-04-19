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

'''
The microfunctions Session API accessible by the function worker for session related actions.
'''

import hashlib
import random

import json

from DataLayerClient import DataLayerClient
from SessionHelperThread import SessionHelperThread

class SessionUtils:

    def __init__(self, worker_params, publication_utils, logger):
        self._logger = logger

        self._queue = worker_params["queue"]
        self._datalayer = worker_params["datalayer"]

        self._session_function_id = None

        self._hostname = worker_params["hostname"]
        self._userid = worker_params["userid"]
        self._sandboxid = worker_params["sandboxid"]
        self._workflowid = worker_params["workflowid"]
        self._function_state_name = worker_params["function_state_name"]
        self._function_topic = worker_params["function_topic"]
        self._internal_endpoint = worker_params["internal_endpoint"]

        self._publication_utils = publication_utils

        self._is_session_function_running = False

        self._helper_thread = None

        self._global_data_layer_client = None

        # only valid if this is a session function (i.e., session_function_id is not None)
        self._local_topic_communication = None

        self._session_function_parameters = None

        # to be set later
        self._key = None
        self._session_id = None

        # _XXX_: the following does not have any effect and makes unnecessary calls
        # to the data layer
        # the main reason is that the backend at the data layer does not create
        # sets and maps (i.e., createSet, createMap) until an entry is made
        # the addition of the entries will succeed without requiring the
        # corresponding set/map to have been created.
        #self._create_metadata_tables()

        #self._logger.debug("[SessionUtils] init done.")

    def set_key(self, key):
        self._key = key

    def set_session_id(self, session_id=None):
        if session_id is None:
            self._generate_session_id()
        else:
            self._session_id = session_id

        self._setup_metadata_tablenames()

        self._global_data_layer_client = DataLayerClient(locality=1, sid=self._sandboxid, for_mfn=True, connect=self._datalayer)


    ###########################
    #
    # Alias operations with a given session id?
    # probably not needed. the session id that is generated at session start
    # would be returned to the client,
    # which would send it back in the future to set the context correctly
    # (i.e., happens implicitly during function instantiation and/or communication).
    # the application can then also set a session alias and return it to the client,
    # which can use it in the future to set the context.
    # however, the session will be implicitly identified via the client sending back
    # the session id and/or the alias.
    # no need to allow other explicit access to alias operations.
    #
    # How to deal with access control between sessions?
    # (i.e., a function session A should not be able to set an alias for session B).
    # when the context is correctly set via the session id and/or the session alias
    # and with no explicit access to alias operations with a given session id,
    # this cannot happen.
    #
    # Alias operations with a session function id?
    # in a given session, any function may assign an alias to another session function instance
    # in other words, it doesn't need to be the actual session function instance that is setting
    # its alias; it could be a regular function that is assigning aliases to session function instances.
    # when that happens, we'd need to update the relevant session function with its new alias,
    # Actually, just keep all aliases in the data layer, so that get() operations read it from there
    # and set() operations update it there (i.e., no need to keep localized versions)
    # keeping the localized versions up-to-date with the data layer would require
    # synchronization when there is an update (most probably via an immediate special message)
    ###########################

    def set_session_alias(self, alias):
        # update metadata (session alias -> session id) mapping
        # check whether it is already in use
        old_session_id = self._global_data_layer_client.getMapEntry(self._map_name_session_alias_id, alias)
        if old_session_id is not None and old_session_id != "" and old_session_id != self._session_id:
            self._logger.warning("Cannot overwrite alias (" + alias + ") that is in use by another session (existing session id: " + old_session_id + ").")
            return

        self._global_data_layer_client.putMapEntry(self._map_name_session_alias_id, alias, self._session_id)
        self._global_data_layer_client.putMapEntry(self._map_name_session_id_alias, self._session_id, alias)

    def get_session_alias(self):
        session_alias = self._global_data_layer_client.getMapEntry(self._map_name_session_id_alias, self._session_id)
        if session_alias == "":
            session_alias = None
        return session_alias

    def unset_session_alias(self):
        # update metadata
        session_alias = self.get_session_alias()
        if session_alias is not None:
            self._global_data_layer_client.deleteMapEntry(self._map_name_session_alias_id, session_alias)
            self._global_data_layer_client.deleteMapEntry(self._map_name_session_id_alias, self._session_id)

    def set_session_function_alias(self, alias, session_function_id=None):
        # handle setting an alias for another session function
        if session_function_id is None:
            session_function_id = self._session_function_id
        else:
            # check whether the session function id actually exists in the session functions list
            rgidlist = self.get_all_session_function_ids()
            if session_function_id not in rgidlist:
                self._logger.warning("Cannot find session function with id: " + str(session_function_id) + " for setting its alias.")
                return

        # check whether it is already in use; cannot have the same alias for two different instances
        old_session_function_id = self._global_data_layer_client.getMapEntry(self._map_name_session_function_alias_id, alias)
        if old_session_function_id is not None and old_session_function_id != "" and old_session_function_id != session_function_id:
            self._logger.warning("Cannot use alias (" + alias + ") that is in use by another session function (existing session function id: " + old_session_function_id + ").")
            return

        # update metadata (session function alias -> session function id) mapping
        # also (session function id -> session function alias) mapping
        self._global_data_layer_client.putMapEntry(self._map_name_session_function_alias_id, alias, session_function_id)
        self._global_data_layer_client.putMapEntry(self._map_name_session_function_id_alias, session_function_id, alias)

    def get_session_function_alias(self, session_function_id=None):
        # handle setting an alias for another session function
        if session_function_id is None:
            session_function_id = self._session_function_id
        else:
            # check whether the session function id actually exists in the session functions list
            rgidlist = self.get_all_session_function_ids()
            if session_function_id not in rgidlist:
                self._logger.warning("Cannot find session function with id: " + str(session_function_id) + " for getting its alias.")
                return None

        # handle getting an alias for another session function
        alias = self._global_data_layer_client.getMapEntry(self._map_name_session_function_id_alias, session_function_id)
        if alias == "":
            alias = None
        return alias

    def unset_session_function_alias(self, session_function_id=None):
        # handle unsetting the alias for another session function
        if session_function_id is None:
            session_function_id = self._session_function_id
        else:
            # check whether the session function id actually exists in the session functions list
            rgidlist = self.get_all_session_function_ids()
            if session_function_id not in rgidlist:
                self._logger.warning("Cannot find session function with id: " + str(session_function_id) + " for unsetting its alias.")
                return

        # update metadata
        session_function_alias = self.get_session_function_alias(session_function_id)
        if session_function_alias is not None:
            self._global_data_layer_client.deleteMapEntry(self._map_name_session_function_alias_id, session_function_alias)
            self._global_data_layer_client.deleteMapEntry(self._map_name_session_function_id_alias, session_function_id)

    def get_session_id(self):
        return self._session_id

    def get_session_function_id(self):
        return self._session_function_id

    def get_session_function_id_with_alias(self, alias=None):
        if alias is None:
            return self._session_function_id

        sgid = self._global_data_layer_client.getMapEntry(self._map_name_session_function_alias_id, alias)
        return sgid

    def get_all_session_function_ids(self):
        rgidset = self._global_data_layer_client.getMapKeys(self._map_name_session_functions)
        rgidlist = list(rgidset)
        return rgidlist

    def get_all_session_function_aliases(self):
        alias_map = {}
        alias_map = self._global_data_layer_client.retrieveMap(self._map_name_session_function_alias_id)
        return alias_map

    def get_alias_summary(self):
        alias_summary = {}
        # 1. add current session alias
        alias_summary["session"] = {}
        session_alias = self.get_session_alias()
        if session_alias is None:
            session_alias = ""
        alias_summary["session"][self._session_id] = session_alias

        # 2. add current session function aliases
        alias_summary["session_functions"] = {}

        # 2.1. get all session function ids
        rgidlist = self.get_all_session_function_ids()

        for rgid in rgidlist:
            alias_summary["session_functions"][rgid] = ""

        # 2.2. get assigned aliases to all session functions
        alias_map = self.get_all_session_function_aliases()

        # 2.3. merge 2.1 and 2.2
        # it is possible that some session functions will have no alias
        for alias in alias_map.keys():
            rgid = alias_map[alias]
            alias_summary["session_functions"][rgid] = alias

        return alias_summary

    # every function in a session workflow will call this, setting up the metadata tablenames
    def _generate_session_id(self):
        if self._session_id is None:
            # MUST be unique and deterministic (so that multiple, concurrent instances generate the same)
            # uid + sid + wid + key
            # emitting messages during execution MUST use existing session id
            # due to key being different for each request to the workflow
            plain_session_id_bytes = (self._userid + "_" + self._sandboxid + "_" + self._workflowid + "_" + self._key).encode()
            self._session_id = hashlib.sha256(plain_session_id_bytes).hexdigest()
            #self._logger.debug("[SessionUtils] Session id: " + self._session_id)

    def _generate_session_function_id(self):
        if self._session_function_id is None:
            # this cannot be just instanceid (i.e., key of the request); multiple functions receive the same instance id
            # should include some randomness, so that the same function can be instantiated more than once
            # need to use (gname + key + random)
            # we are only interested in keeping the session function ids of the same sandbox/workflow/session
            random.seed()
            plain_session_function_id_bytes = (self._function_state_name + "_" + self._key + "_" + str(random.uniform(0, 100000))).encode()
            self._session_function_id = hashlib.sha256(plain_session_function_id_bytes).hexdigest()
            #self._logger.debug("[SessionUtils] Session function id: " + self._session_function_id)

    # these calls don't have an effect until an entry is added
    # and the entries still succeed even without calling to createSet or createMap
    # making these calls unnecessary
    def _create_metadata_tables(self):
        # create the metadata tables if necessary
        names_sets = self._global_data_layer_client.getSetNames()
        names_maps = self._global_data_layer_client.getMapNames()

        if self._map_name_session_functions not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_functions)

        if self._map_name_session_function_name_id_sets not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_function_name_id_sets)

        if self._set_name_session_function_name_ids not in names_sets:
            self._global_data_layer_client.createSet(self._set_name_session_function_name_ids)

        if self._map_name_session_alias_id not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_alias_id)

        if self._map_name_session_id_alias not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_id_alias)

        if self._map_name_session_function_alias_id not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_function_alias_id)

        if self._map_name_session_function_id_alias not in names_maps:
            self._global_data_layer_client.createMap(self._map_name_session_function_id_alias)

    def _setup_metadata_tablenames(self):
        # set up metadata tables
        # we know the session id, so each metadata table has it in its name
        # 1. session function instance id -> function instance metadata as 'map'
        # 2. session function name -> ref to set name of instance ids as 'map'
        # 3. session function instance ids as 'set' (with session function name as 'set' name)
        # 4. session alias -> session id metadata as 'map'
        # 5. session function alias -> session function id metadata as 'map'

        # 0. set of session function instance ids
        # we just expose the function instance ids to the application via the map keys
        # 1. map of session function instances and metadata (key = session function instance id, value = name, location, ...)
        self._map_name_session_functions = "SessionFunctionInstanceIdMap_" + self._session_id

        # 2. map of function names and ref to set of instance ids
        self._map_name_session_function_name_id_sets = "SessionFunctionNameIdSetsMap_" + self._session_id

        # 3. set of function instance ids of a function; referenced by SessionFunctionNameIdSetsMap
        self._set_name_session_function_name_ids = "SessionFunctionNameIdsSet_" + self._session_id + "_" + self._function_state_name

        # 4. session alias -> session id mapping; needs to be sandbox-level (i.e., without self._session_id)
        self._map_name_session_alias_id = "SessionAliasIdMap_" + self._sandboxid

        # 5. session id -> session alias mapping; needs to be sandbox-level (i.e., without self._session_id)
        self._map_name_session_id_alias = "SessionIdAliasMap_" + self._sandboxid

        # 6. session function alias -> session function id mapping
        self._map_name_session_function_alias_id = "SessionFunctionAliasIdMap_" + self._session_id

        # 7. session function id -> session function alias mapping
        self._map_name_session_function_id_alias = "SessionFunctionIdAliasMap_" + self._session_id

    def _store_metadata(self):
        # add yourself to the metadata in the data layer
        # 1. add yourself to the metadata map
        # use this information in host agent to find the correct host and deliver new messages correctly
        # need to include the global queue topic name, so that messages
        # can be also delivered from remote hosts
        function_metadata = {}
        function_metadata["hostname"] = self._hostname
        function_metadata["sandboxId"] = self._sandboxid
        function_metadata["workflowId"] = self._workflowid
        function_metadata["sessionId"] = self._session_id
        function_metadata["functionName"] = self._function_state_name
        function_metadata["communicationTopic"] = self._local_topic_communication
        function_metadata["remote_address"] = self._internal_endpoint
        metadata = json.dumps(function_metadata)

        #self._logger.debug("[SessionUtils] Session function metadata: " + metadata)

        self._global_data_layer_client.putMapEntry(self._map_name_session_functions, self._session_function_id, metadata)

        # 2. put the reference to the set of instance ids with our name
        self._global_data_layer_client.putMapEntry(self._map_name_session_function_name_id_sets, self._function_state_name, self._set_name_session_function_name_ids)

        # 3. update the set of instance ids with our session function id
        self._global_data_layer_client.addSetEntry(self._set_name_session_function_name_ids, self._session_function_id)

    def _remove_metadata(self):
        # remove any session function alias mappings
        self.unset_session_function_alias()

        #if self._key_update_message is not None:
        #    self._local_data_layer_client.delete(self._key_update_message)

        self._global_data_layer_client.removeSetEntry(self._set_name_session_function_name_ids, self._session_function_id)
        self._global_data_layer_client.deleteMapEntry(self._map_name_session_function_name_id_sets, self._function_state_name)
        self._global_data_layer_client.deleteMapEntry(self._map_name_session_functions, self._session_function_id)

        # TODO: we also need to remove the metadata tables at session end as well as the session alias mappings
        # i.e., when all functions in the session have been finished.

    def _setup_session_function_helper(self):
        params = {}
        params["sandboxid"] = self._sandboxid
        params["workflowid"] = self._workflowid
        params["session_id"] = self._session_id
        params["session_function_id"] = self._session_function_id

        # obtain parameters from the function worker
        params["heartbeat_parameters"] = self._session_function_parameters

        params["communication_parameters"] = {}
        params["communication_parameters"]["local_topic_communication"] = self._local_topic_communication

        self._helper_thread = SessionHelperThread(params, self._logger, self._publication_utils, self, self._queue, self._datalayer)
        self._helper_thread.daemon = False
        self._helper_thread.start()

    def shutdown_helper_thread(self):
        if self._helper_thread is not None:
            self._helper_thread.shutdown()

    def cleanup(self):
        self._remove_metadata()

        self._global_data_layer_client.shutdown()

    # only to be called from the function worker when it is a session function
    def setup_session_function(self, session_function_parameters):
        self._session_function_parameters = session_function_parameters
        # generate a new session function id
        self._generate_session_function_id()

        # for receiving update messages
        # also set up a global queue topic name, so that this session
        # function can be sent messages from remote hosts
        #self._key_update_message = "UpdateMessage_" + self._session_function_id
        self._local_topic_communication = "SessionFunctionUpdateTopic_" + self._session_function_id

        # set up metadata tables if necessary and register yourself
        # maybe first fork? need to have its own global data layer client
        # no, because this setup is crucial for the operation of the session function
        # if it fails, we'd need to stop everything else.
        self._store_metadata()

        self._is_session_function_running = True

        # set up the helper thread
        self._setup_session_function_helper()


    def set_session_function_running(self, is_running):
        self._is_session_function_running = is_running

    def is_session_function_running(self):
        return self._is_session_function_running

    # API to send a message to another session function
    # check the locally running functions, and send them the message locally if so
    # otherwise, send it to the EventGlobalPublisher's queue
    def send_to_running_function_in_session(self, session_function_id, message, send_now=False):
        #self._logger.debug("[SessionUtils] Sending message to running function: " + str(session_function_id) + " now: " + str(send_now))
        # send the message to the specific running function id
        function_metadatastr = self._global_data_layer_client.getMapEntry(self._map_name_session_functions, session_function_id)
        try:
            #self._logger.debug("[SessionUtils] function metadata: " + function_metadatastr)
            function_metadata = json.loads(function_metadatastr)
        except Exception as exc:
            self._logger.warning("[SessionUtils] No such running function instance: " + session_function_id + " " + str(exc))
            return

        # we can use the 'globalTopic' in metadata to also deliver
        # the message directly to the locally running session function instances
        # that means, we can skip the delivery by the function worker
        # that however also means, that the decapsulation of the message
        # has to happen at the session function's helper thread
        trigger = {}
        trigger["value"] = message
        trigger["to_running_function"] = True
        trigger["next"] = function_metadata["communicationTopic"]
        if self._hostname == function_metadata["hostname"]:
            # local function instance; send it via local queue
            #self._logger.debug("[SessionUtils] Local session function: " + str(session_function_id))
            trigger["is_local"] = True
        else:
            # remote function instance
            #self._logger.debug("[SessionUtils] Remote session function: " + str(session_function_id))
            trigger["is_local"] = False
            trigger["remote_address"] = function_metadata["remote_address"]

        if send_now:
            self._publication_utils.send_to_function_now("-1l", trigger)
        else:
            self._publication_utils.append_trigger(trigger)

    def send_to_all_running_functions_in_session_with_function_name(self, session_function_name, message, send_now=False):
        # get the function ids and send message
        rgidsetname = self._global_data_layer_client.getMapEntry(self._map_name_session_function_name_id_sets, session_function_name)
        rgidset = self._global_data_layer_client.retrieveSet(rgidsetname)
        rgidlist = list(rgidset)
        for rgid in rgidlist:
            self.send_to_running_function_in_session(rgid, message, send_now)

    def send_to_all_running_functions_in_session(self, message, send_now=False):
        # get the function ids and send message
        rgidset = self._global_data_layer_client.getMapKeys(self._map_name_session_functions)
        rgidlist = list(rgidset)
        for rgid in rgidlist:
            self.send_to_running_function_in_session(rgid, message, send_now)

    def send_to_running_function_in_session_with_alias(self, session_function_alias, message, send_now=False):
        # lookup the session function id and then send to it
        rgid = self._global_data_layer_client.getMapEntry(self._map_name_session_function_alias_id, session_function_alias)

        if rgid == "":
            self._logger.warning("Cannot send message to session function with alias; no session function with that alias.")
            return

        self.send_to_running_function_in_session(rgid, message, send_now)

    def get_session_update_messages_with_local_queue(self, count=1, block=False):
        if self._session_function_id is not None:
            messages = self._helper_thread.get_messages(count=count, block=block)
            return messages
        return None
