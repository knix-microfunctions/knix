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
The MicroFunctions API accessible by functions.
'''

from DataLayerClient import DataLayerClient
from DataLayerOperator import DataLayerOperator
from MicroFunctionsExceptions import MicroFunctionsWorkflowException, MicroFunctionsSessionAPIException, MicroFunctionsUserLogException, MicroFunctionsDataLayerException

import py3utils
import requests
import json
import random

from typing import Dict, Any
from datetime import date

LambdaDict = Dict[str, Any]


class LambdaCognitoIdentity(object):
    cognito_identity_id: str
    cognito_identity_pool_id: str


class LambdaClientContextMobileClient(object):
    installation_id: str
    app_title: str
    app_version_name: str
    app_version_code: str
    app_package_name: str


class LambdaClientContext(object):
    client: LambdaClientContextMobileClient
    custom: LambdaDict
    env: LambdaDict


class MicroFunctionsAPI:
    '''
    This class defines the API that is exposed to the user functions.
    An object of this class is passed to the user function along with the input event.
    It enables operations related to the following features:
    - logging
    - data layer access
    - dynamic generation of workflows
    - communication with other (sesssion or regular) functions during execution
    - session customization
    '''

    #def __init__(self, uid, sid, wid, funcstatename, key, publication_utils, is_session_workflow, is_session_function, session_utils, logger, datalayer, external_endpoint, internal_endpoint, useremail, usertoken, management_endpoints):
    def __init__(self, worker_params, publication_utils, session_utils, usertoken, logger):
        '''
        Initialize data structures for MicroFunctionsAPI object created for a function instance.

        Args:
            uid (string): user id
            sid (string): sandbox id
            wid (string): workflow id
            logger (logger): log object
            funcstatename (string): function's state name
            key (string): key of the input message
            datalayer (string): host:port of the local data layer server
            external_endpoint (string): external endpoint of this sandbox
            useremail (string): email address of the user
            usertoken (string): token to invoke management service APIs
            management_endpoints: external endpoints of the management service

        Returns:
            None
        '''

        self._logger = logger
        self._datalayer = worker_params["datalayer"]
        self._external_endpoint = worker_params["external_endpoint"]
        self._internal_endpoint = worker_params["internal_endpoint"]
        self._management_endpoints = worker_params["management_endpoints"]
        self._usertoken = usertoken
        self._sid = worker_params["sandboxid"]
        self._wid = worker_params["workflowid"]
        self._suid = worker_params["storage_userid"]

        self._data_layer_operator = DataLayerOperator(self._suid, self._sid, self._wid, self._datalayer)

        # for sending immediate triggers to other functions
        self._publication_utils = publication_utils

        self._is_session_workflow = worker_params["is_session_workflow"]
        self._is_session_function = worker_params["is_session_function"]
        self._session_utils = session_utils

        self._function_state_name = worker_params["function_state_name"]
        self._function_version = 1  # Currently hardcoded to 1

        self._instanceid = None

        self._is_privileged = False
        if self._sid == "Management" and self._wid == "Management":
            self._is_privileged = True

        '''
        AWS context object properties required for API compatibility, TODO: remove hardcoding of some values
        '''
        self.function_name = self._function_state_name  # The name of the function.
        # The version of the function.
        self.function_version = self._function_version
        # The Amazon Resource Name (ARN) that's used to invoke the function. Indicates if the invoker specified a version number or alias.
        self.invoked_function_arn = self.function_name + \
            ":" + str(self.function_version)
        # The amount of memory that's allocated for the function. Always -1, as there is no memory limit set for KNIX
        self.memory_limit_in_mb = 3008
        # The identifier of the invocation request. Return the KNIX message key instead
        self.aws_request_id = self._instanceid
        # The log group name for the function. Follows a "/provider/service/functionname" scheme
        self.log_group_name = "/knix/mfn/" + self.function_name

        today = date.today()  # calculate date
        d1 = today.strftime("%Y/%m/%d")
        # The log stream name for this function instance.
        self.log_stream_name = str(d1) + "[$LATEST]" + str(self._logger.name)

        # Amazon Cognito identity that authorized the request.
        self.identity = LambdaCognitoIdentity()
        # set to knix identity id
        self.identity.cognito_identity_id = 'knix_cognito_identity_id'
        # set to knix identity pool id
        self.identity.cognito_identity_pool_id = 'knix_cognito_identity_pool_id'

        # generate ContextMobileClent object
        self.client_context_mobile_client = LambdaClientContextMobileClient()
        self.client_context_mobile_client.installation_id = 'knix_installation_id'  # set to KNIX id
        self.client_context_mobile_client.app_title = 'knix_app_title'  # set to KNIX app title
        # set to KNIX app name
        self.client_context_mobile_client.app_version_name = 'knix_app_version_name'
        # set to KNIX app code
        self.client_context_mobile_client.app_version_code = 'knix_app_version_code'
        # set to KNIX app package name
        self.client_context_mobile_client.app_package_name = 'knix_app_package_name'

        self.client_context = LambdaClientContext()  # generate ClientContext object
        # set to client mobile context
        self.client_context.client = self.client_context_mobile_client
        # set to KNIX context custom
        self.client_context.custom = {'knix_custom': True}
        # set to KNIX context env
        self.client_context.env = {'knix_env': 'test'}

        #self._logger.debug("[MicroFunctionsAPI] init done.")

    def set_key(self, key):
        self._instanceid = key
        # The AWS identifier of the invocation request. Return the KNIX message key instead
        self.aws_request_id = self._instanceid

    def get_context_object_properties(self):
        context_properties = {}
        context_properties["function_name"] = self.function_name
        context_properties["function_version"] = self.function_version
        context_properties["invoked_function_arn"] = self.invoked_function_arn
        context_properties["memory_limit_in_mb"] = self.memory_limit_in_mb
        context_properties["aws_request_id"] = self.aws_request_id
        context_properties["log_group_name"] = self.log_group_name
        context_properties["log_stream_name"] = self.log_stream_name

        context_properties["identity"] = {}
        context_properties["identity"]["cognito_identity_id"] = self.identity.cognito_identity_id
        context_properties["identity"]["cognito_identity_pool_id"] = self.identity.cognito_identity_pool_id

        context_properties["client_context"] = {}

        context_properties["client_context"]["client"] = {}
        context_properties["client_context"]["client"]["installation_id"] = self.client_context_mobile_client.installation_id
        context_properties["client_context"]["client"]["app_title"] = self.client_context_mobile_client.app_title
        context_properties["client_context"]["client"]["app_version_name"] = self.client_context_mobile_client.app_version_name
        context_properties["client_context"]["client"]["app_version_code"] = self.client_context_mobile_client.app_version_code
        context_properties["client_context"]["client"]["app_package_name"] = self.client_context_mobile_client.app_package_name

        context_properties["client_context"]["custom"] = self.client_context.custom
        context_properties["client_context"]["env"] = self.client_context.env

        return json.dumps(context_properties)

    def ping(self, num):
        self._logger.info("ping: " + str(num))
        output = num
        return 'pong ' + str(output)

    def get_privileged_data_layer_client(self, suid=None, sid=None, for_mfn=False, is_wf_private=False, init_tables=False, drop_keyspace=False, tableName=None):
        '''
        Obtain a privileged data layer client to access a user's storage, a workflow-private storage or mfn internal tables of a workflow.
        Only can be usable by the management service.

        Args:
            suid (string): the storage user id
            sid (string): sandbox id

            init_tables (boolean): whether relevant data layer tables should be initialized; default: False.
            drop_keyspace (boolean): whether the relevant keyspace for the user's storage should be dropped; default: False.
            for_mfn: whether it is about the mfn internal table of a workflow; default: False.
            tableName (string): name of the table to be used for subsequent storage operations. By default, the default table will be used.
                 If this method is called with is_wf_private = True, then the tableName parameter will be ignored.

        Returns:
            A data layer client with access to a user's storage.

        '''
        if self._is_privileged:
            if suid is not None:
                if tableName is not None:
                    return DataLayerClient(locality=1, suid=suid, connect=self._datalayer, init_tables=init_tables, drop_keyspace=drop_keyspace, tableName=tableName)
                else:
                    return DataLayerClient(locality=1, suid=suid, connect=self._datalayer, init_tables=init_tables, drop_keyspace=drop_keyspace)
            elif for_mfn:
                return DataLayerClient(locality=1, sid=sid, for_mfn=True, init_tables=init_tables, connect=self._datalayer, drop_keyspace=drop_keyspace)
            elif is_wf_private:
                return DataLayerClient(locality=1, sid=sid, wid=sid, is_wf_private=True, init_tables=init_tables, connect=self._datalayer, drop_keyspace=drop_keyspace)

        return None

    def update_metadata(self, metadata_name, metadata_value, is_privileged_metadata=False):
        '''
        Update the metadata that can be passed to other function instances and other components (e.g., recovery manager (not yet implemented)).

        Args:
            metadata_name (string): the key of the metadata to update
            metadata_value (string): the value of the metadata
            is_privileged_metadata (boolean): whether the metadata is privileged belonging to the management service

        Returns:
            None

        '''
        is_privileged = False
        if is_privileged_metadata and self._is_privileged:
            is_privileged = True

        self._publication_utils.update_metadata(
            metadata_name, metadata_value, is_privileged=is_privileged)

    # session related API calls
    # only valid if the workflow has at least one session function
    def send_to_running_function_in_session(self, rgid, message, send_now=False):
        '''
        Send a message to a long-running session function instance identified with its id in this session.

        Args:
            rgid (string): the running long-running session function instance's id.
            message (*): the message to be sent; can be any python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).
            send_now (boolean): whether the message should be sent immediately or at the end of current function's execution; default: False.

        Returns:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        message = self._publication_utils.convert_api_message_to_python_object(
            message)

        if not self._publication_utils.is_valid_value(message):
            errmsg = "Malformed message: 'message' must a python data type (dict, list, str, int, float, or None)."
            raise MicroFunctionsSessionAPIException(errmsg)

        if self._is_session_workflow:
            self._session_utils.send_to_running_function_in_session(
                rgid, message, send_now)
        else:
            self._logger.warning(
                "Cannot send a session update message in a workflow with no session functions.")

    def send_to_all_running_functions_in_session_with_function_name(self, gname, message, send_now=False):
        '''
        Send a message to all long-running session function instances identified with their function name in this session.
        There can be multiple instances with the same function name, which will all receive the message.
        The function name refers to the function name;
        it is not to be confused with the 'alias' that may have been assigned to each long-running, session function instance.

        Args:
            gname (string): the function name of the running long-running session function instance(s).
            message (*): the message to be sent; can be any python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).
            send_now (boolean): whether the message should be sent immediately or at the end of current function's execution; default: False.

        Returns:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        message = self._publication_utils.convert_api_message_to_python_object(
            message)

        if not self._publication_utils.is_valid_value(message):
            errmsg = "Malformed message: 'message' must a python data type (dict, list, str, int, float, or None)."
            raise MicroFunctionsSessionAPIException(errmsg)

        if self._is_session_workflow:
            self._session_utils.send_to_all_running_functions_in_session_with_function_name(
                gname, message, send_now)
        else:
            self._logger.warning(
                "Cannot send a session update message in a workflow with no session functions.")

    def send_to_all_running_functions_in_session(self, message, send_now=False):
        '''
        Send a message to all long-running session function instances in this session.

        Args:
            message (*): the message to be sent; can be any python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).
            send_now (boolean): whether the message should be sent immediately or at the end of current function's execution; default: False.

        Returns:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        message = self._publication_utils.convert_api_message_to_python_object(
            message)

        if not self._publication_utils.is_valid_value(message):
            errmsg = "Malformed message: 'message' must a python data type (dict, list, str, int, float, or None)."
            raise MicroFunctionsSessionAPIException(errmsg)

        if self._is_session_workflow:
            self._session_utils.send_to_all_running_functions_in_session(
                message, send_now)
        else:
            self._logger.warning(
                "Cannot send a session update message in a workflow with no session functions.")

    def send_to_running_function_in_session_with_alias(self, alias, message, send_now=False):
        '''
        Send a message to a long-running session function instance identified with its alias in this session.
        The alias would have to be assigned before calling this function.
        The alias can belong to only a single long-running, session function instance.

        Args:
            alias (string): the alias of the running long-running session function instance that is the destination of the message.
            message (*): the message to be sent; can be any python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).
            send_now (boolean): whether the message should be sent immediately or at the end of current function's execution; default: False.

        Returns:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        message = self._publication_utils.convert_api_message_to_python_object(
            message)

        if not self._publication_utils.is_valid_value(message):
            errmsg = "Malformed message: 'message' must a python data type (dict, list, str, int, float, or None)."
            raise MicroFunctionsSessionAPIException(errmsg)

        if self._is_session_workflow:
            self._session_utils.send_to_running_function_in_session_with_alias(
                alias, message, send_now)
        else:
            self._logger.warning(
                "Cannot send a session update message in a workflow with no session functions.")

    def get_session_update_messages(self, count=1, block=False):
        '''
        Retrieve the list of update messages sent to a session function instance.
        The list contains messages that were sent and delivered since the last time the session function instance has retrieved it.
        These messages are retrieved via a local queue. There can be more than one message.
        The optional count argument specifies how many messages should be retrieved.
        If there are fewer messages than the requested count, all messages will be retrieved and returned.

        Args:
            count (int): the number of messages to retrieve; default: 1
            block (boolean): whether it should block until 'count' number of messages have been received.

        Returns:
            List of messages that were sent to the session function instance.
            If in non-blocking mode, the number of returned messages will be less than or equal to 'count'.

        Warns:
            When the calling function is not a session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        messages = []
        if self._is_session_function:
            #self._logger.debug("[MicroFunctionsAPI] getting session update messages...")
            messages2 = self._session_utils.get_session_update_messages_with_local_queue(
                count=count, block=block)
            for msg2 in messages2:
                msg = self._publication_utils.convert_python_object_to_api_message(
                    msg2)
                messages.append(msg)
        else:
            self._logger.warning(
                "Cannot get session update messages in a non-session function: " + self._function_state_name)

        return messages

    def set_session_alias(self, alias):
        '''
        Assign an alias to the current session.

        Args:
            alias (string): the custom name to be assigned to the session.

        Returns:
            None

        Raises:
            MicroFunctionsSessionAPIException: when the alias is not a string, or is empty string.

        Warns:
            When the alias is already in use by another session.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if not py3utils.is_string(alias):
            raise MicroFunctionsSessionAPIException(
                "Invalid session alias; must be a non-empty string.")
        elif alias == "":
            raise MicroFunctionsSessionAPIException(
                "Session alias cannot be empty.")

        if self._is_session_workflow:
            self._session_utils.set_session_alias(alias)
        else:
            self._logger.warning(
                "Cannot set a session alias in a workflow with no session functions.")

    def unset_session_alias(self):
        '''
        Remove the existing alias of the current session.

        Args:
            None

        Returns:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        self._session_utils.unset_session_alias()

    def get_session_alias(self):
        '''
        Retrieve the existing alias of the current session.

        Args:
            None

        Returns:
            The existing session alias (string) or None if no alias is set.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if self._is_session_workflow:
            return self._session_utils.get_session_alias()
        else:
            self._logger.warning(
                "Cannot get a session alias in a workflow with no session functions.")
        return ""

    def set_session_function_alias(self, alias, session_function_id=None):
        '''
        Assign an alias to a session function instance in this session.
        If the session function id is not set, the alias will be assigned to the calling function instance.
        If it is set, the alias will be assigned to the function instance with the given id.

        Args:
            alias (string): the custom name to be assigned to the session function instance.
            session_function_id (string): the session function instance id for which this alias should be assigned; default: None

        Returns:
            None

        Raises:
            MicroFunctionsSessionAPIException: when the alias is not a string, or is empty string

        Warns:
            When calling function is not a session function.
            When no session function instance exists with the given session function id.
            When the alias is already in use by another existing session function instance.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if not py3utils.is_string(alias):
            raise MicroFunctionsSessionAPIException(
                "Invalid session function alias; must be a non-empty string.")
        elif alias == "":
            raise MicroFunctionsSessionAPIException(
                "Session function alias cannot be empty.")

        # handle another session function's alias
        if session_function_id is not None:
            self._session_utils.set_session_function_alias(
                alias, session_function_id)
        elif self._is_session_function:
            self._session_utils.set_session_function_alias(alias)
        else:
            self._logger.warning(
                "Cannot set a session function alias in a non-session function.")

    def unset_session_function_alias(self, session_function_id=None):
        '''
        Remove the current alias of the session function instance in this session.
        If the session function id is not set, the current function instance's alias will be removed.
        If it is set, the alias of the session function instance corresponding to the id will be removed.

        Args:
            session_function_id (string): the id of the session function instance whose alias should be removed; default: None.

        Returns:
            None

        Warns:
            When calling function is not a session function if session function id is None.
            When no session function instance exists with the given session function id.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # handle another session function's alias
        if session_function_id is not None:
            self._session_utils.unset_session_function_alias(
                session_function_id)
        elif self._is_session_function:
            self._session_utils.unset_session_function_alias()
        else:
            self._logger.warning(
                "Cannot unset a session function alias in a non-session function.")

    def get_session_function_alias(self, session_function_id=None):
        '''
        Retrieve the current alias of the session function instance in this session.
        If the session function id is not set, the current function instance's alias will be retrieved.
        If it is set, the alias of the session function instance corresponding to the id will be retrieved.

        Args:
            session_function_id (string): the id of the session function instance whose alias should be retrieved; default: None.

        Returns:
            The existing alias of the session function instance (string) or None if no alias is set.

        Warns:
            When calling function is not a session function if session function id is None.
            When no session function instance exists with the given session function id.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # handle another session function's alias
        if session_function_id is not None:
            return self._session_utils.get_session_function_alias(session_function_id)
        elif self._is_session_function:
            return self._session_utils.get_session_function_alias()
        else:
            self._logger.warning(
                "Cannot get a session function alias in a non-session function.")
        return None

    def get_all_session_function_aliases(self):
        '''
        Retrieve the session function instance and alias mapping for all the session function instances in this session.

        Args:
            None

        Returns:
            A dictionary with session function instance id as the key and the alias as the value involving all session function instances in this session.

        Warns:
            When the calling function is not part of a workflow with at least one session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        aliases = {}
        if self._is_session_workflow:
            aliases = self._session_utils.get_all_session_function_aliases()
        else:
            self._logger.warning(
                "Cannot get session function aliases in a workflow with no session functions.")
        return aliases

    def get_alias_summary(self):
        '''
        Retrieve a summary of the aliases of the current session and its session function instances.

        Args:
            None

        Returns:
            Dictionary with two keys -- 'session' and 'session_functions', each referring to another dictionary.
            'session' dictionary will have an item with the session id as the key and the session alias as the value.
            'session_functions' dictionary will have one or more entries, where each key will be the id of a session function instance
            and the corresponding value will be the alias assigned to that session function instance.
            If any alias is not set, then the values will be None.

        Warns:
            When the calling function is not part of a workflow with at least one session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        alias_summary = {}
        if self._is_session_workflow:
            alias_summary = self._session_utils.get_alias_summary()
        else:
            self._logger.warning(
                "Cannot get alias summary for session in a workflow with no session functions.")
        return alias_summary

    def get_session_id(self):
        '''
        Retrieve the current session's id.

        Args:
            None

        Returns:
            The session id of the current session.

        Warns:
            When the calling function is not part of a workflow with at least one session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if self._is_session_workflow:
            return self._session_utils.get_session_id()
        else:
            self._logger.warning(
                "Cannot get a session id in a workflow with no session functions.")
        return None

    def get_session_function_id(self):
        '''
        Retrieve the current session function instance's id.

        Args:
            None

        Returns:
            The id of the current session function instance.

        Warns:
            When the calling function is not a session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if self._is_session_function:
            return self._session_utils.get_session_function_id()
        else:
            self._logger.warning(
                "Cannot get session function id in a non-session function.")
        return None

    def get_session_function_id_with_alias(self, alias=None):
        '''
        Retrieve the id of a session function instance using an alias.
        When alias is not set, the id of the current session function instance will be returned.
        When it is not set, the id of the session function instance with that alias will be returned.

        Args:
            alias (string): The alias that needs to be used to retrieve the id of the session function instance; default: None

        Returns:
            The id of the current session function instance when alias is not set, or the ide of the session function instance with the given alias.

        Warns:
            When the calling function is not a session function if the alias is not given.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # handle another session function's alias
        if alias is not None:
            return self._session_utils.get_session_function_id_with_alias(alias)
        elif self._is_session_function:
            return self._session_utils.get_session_function_id_with_alias()
        else:
            self._logger.warning(
                "Cannot get session function id in a non-session function.")
        return None

    def get_all_session_function_ids(self):
        '''
        Retrieve a list of all ids of the session function instances in this session.

        Args:
            None

        Returns:
            List of ids of all the session function instances in this session.

        Warns:
            When the calling function is not part of a workflow with at least one session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        rgidlist = []
        if self._is_session_workflow:
            rgidlist = self._session_utils.get_all_session_function_ids()
        else:
            self._logger.warning(
                "Cannot get session function ids in a workflow with no session functions.")
        return rgidlist

    def is_still_running(self):
        '''
        Retrieve the status of this session function instance.
        The status of the session function instance could have been changed via a special message
        delivered to the session function instance and handled by the platform.
        A session function should call this method to handle such cases.

        Args:
            None

        Returns:
            True if the session function instance has not received a special message to stop, or False otherwise.

        Warns:
            When the calling function is not a session function.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., session functions).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        if self._is_session_function:
            return self._session_utils.is_session_function_running()
        else:
            self._logger.warning(
                "Cannot get status of running in a non-session function.")
        return None

    ##########################
    # _XXX_: API call changes:
    # 1. for better function names that reflect the intention (e.g., add_workflow_next)
    # 2. new API call for sending immediate messages
    # 2.1 need to get a list of functions in this sandbox for sanity checking
    # (i.e., messages should only be sent to functions listed in this sandbox)
    # 3. better checking of _wf_pot_next
    # (i.e., when adding a dynamic trigger rather than publishing at the end of execution)
    # 4. optimization of the trigger validity check
    def add_workflow_next(self, next, value):
        '''
        Construct a dynamic trigger and add it to the workflow.
        The dynamic trigger will define the next function to be executed after this function
        and the value that will be passed as input to the next function.
        If the 'value' field is not used, the 'next' function will be executed with an empty string as input.

        Args:
            next (string): the function name to be executed after this function; must be of a string.
            value: the input value to be passed to the next function; can be any python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).

        Returns:
            None

        Raises:
            MicroFunctionsWorkflowException: when either 'next' is not a string or 'value' is not a valid python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., dynamic workflow manipulation).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        value = self._publication_utils.convert_api_message_to_python_object(
            value)

        is_valid, is_privileged, errmsg = self._publication_utils.is_valid_trigger_message(
            next, value, False)

        if is_valid:
            trigger = {}
            trigger["next"] = next
            trigger["value"] = value
            trigger["is_privileged"] = is_privileged
            self._publication_utils.append_trigger(trigger)
        else:
            raise MicroFunctionsWorkflowException(errmsg)

    def add_dynamic_next(self, next, value):
        '''
        Alias for add_workflow_next(self, next, value).

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., dynamic workflow manipulation).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        self.add_workflow_next(next, value)

    def send_to_function_now(self, destination, value):
        '''
        Send a new event message to another function immediately instead of waiting until the end of the current function execution.
        The destination can be any function in the workflow description.
        The value must be a python data type.

        Args:
            destination (string): the destination of the message
            value (*): the message to be sent; must be a python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).

        Raises:
            MicroFunctionsWorkflowException: when either the destination is not a string or the value is not a python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., 'AllowImmediateMessages').
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        value = self._publication_utils.convert_api_message_to_python_object(
            value)

        is_valid, is_privileged, errmsg = self._publication_utils.is_valid_trigger_message(
            destination, value, True)

        if is_valid:
            trigger = {}
            trigger["next"] = destination
            trigger["value"] = value
            trigger["is_privileged"] = is_privileged
            self._publication_utils.send_to_function_now(
                self._instanceid, trigger)
        else:
            raise MicroFunctionsWorkflowException(errmsg)

    #########################

    def add_dynamic_workflow(self, dynamic_trigger):
        '''
        Add dynamically generated trigger(s) to the workflow.
        The dynamically generated trigger can be a single dictionary with 'next' and 'value' fields,
        or a list of dictionaries with 'next' and 'value' fields.
        In each dictionary, the 'next' field defines the next function that needs to be triggered.
        The 'value' field defines the input to the respective next function.
        This function will check the validity of the dictionary and raise MicroFunctionsWorkflowException if either 'next' is not a string or 'value' is not a valid python data type (<type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>).

        Args:
            dynamic_trigger (list of dicts, or dict): each dictionary must be of the form: {'next': <type 'str'>, 'value': <type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>}

        Returns:
            None

        Raises:
            MicroFunctionsWorkflowException: when the input is neither a list of dictionaries or a single dictionary.
            MicroFunctionsWorkflowException: when in a dictionary, 'next' or 'value' is missing.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., dynamic workflow manipulation).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        # _XXX_: Java objects need to be serialized and passed to python; however, API functions expect python objects
        # we make the conversion according to the runtime
        dynamic_trigger = self._publication_utils.convert_api_message_to_python_object(
            dynamic_trigger)

        is_valid = True
        # 'dynamic_trigger' can be a single dictionary or a list of dictionaries.
        # each dictionary must be of the form: {'next': <type 'str'>, 'value': <type 'dict', 'list', 'str', 'int', 'float', or 'NoneType'>}
        if isinstance(dynamic_trigger, dict):
            if 'next' in dynamic_trigger and 'value' in dynamic_trigger:
                self.add_workflow_next(
                    dynamic_trigger['next'], dynamic_trigger['value'])
            else:
                errmsg = "Malformed dynamic trigger definition; 'next' and 'value' must be present in the trigger dict()."
                is_valid = False
        elif isinstance(dynamic_trigger, list):
            for trigger in dynamic_trigger:
                if 'next' in trigger and 'value' in trigger:
                    self.add_workflow_next(trigger['next'], trigger['value'])
                else:
                    errmsg = "Malformed dynamic trigger definition; 'next' and 'value' must be present in the trigger dict()."
                    is_valid = False
                    break
        else:
            errmsg = "Malformed dynamic trigger definition; use either a dict() with 'next' and 'value' fields or a list of dict()."
            is_valid = False

        if not is_valid:
            raise MicroFunctionsWorkflowException(errmsg)

    def get_dynamic_workflow(self):
        '''
        Returns:
            The dynamically generated workflow information,
            so that this function instance can trigger other functions when it finishes.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., dynamic workflow manipulation).
            Using a KNIX-specific feature might make the workflow description incompatible with other platforms.

        '''
        return self._publication_utils.get_dynamic_workflow()

    #########################

    def get_remaining_time_in_millis(self):
        '''
        Return the remaining time this function instance is allowed to continue running.
        The time is returned in milliseconds.
        This function exists for AWS Lambda compatibility.
        As of 10.04.2018, the maximum time a function instance can execute is not limited.
        This will change in the future.
        '''
        # 5 minutes always
        return 300000

    def log(self, text, level="INFO"):
        '''
        Log text. Uses the instance id to indicate which function instance logged the text.

        Args:
            text (string): text to be logged.
            level (string): log level to be used.
        Returns:
            None.

        Raises:
            MicroFunctionsUserLogException: when there are any errors in the logging function.
        '''

        if level == "INFO":
            self._logger.info(text)
        elif level == "WARNING":
            self._logger.warning(text)
        elif level == "DEBUG":
            self._logger.debug(text)
        elif level == "ERROR":
            self._logger.error(text)
        else:
            raise MicroFunctionsUserLogException(
                "User logging exception; unsupported log level: " + str(level))

    def get_event_key(self):
        '''
        Returns:
            The function instance id (i.e., the key of the trigger event).
        '''
        return self._instanceid

    def get_instance_id(self):
        '''
        Returns:
            The function instance id (i.e., the key of the trigger event).
        '''
        return self._instanceid

    def put(self, key, value, is_private=False, is_queued=False, bucketName=None):
        '''
        Access to data layer to store a data item in the form of a (key, value) pair.
        By default, the put operation is reflected on the data layer immediately.
        If the put operation is queued (i.e., is_queued = True),
        the data item is put into the transient data bucket.
        If the key was previously deleted by the function instance,
        it is removed from the list of items to be deleted.
        When the function instance finishes,
        the transient data items are committed to the data layer.

        Args:
            key (string): the key of the data item
            value (string): the value of the data item
            is_private (boolean): whether the item should be written to the private data layer of the workflow; default: False
            is_queued (boolean): whether the put operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the put operation will be reflected on the data layer immediately)
            bucketName (string): name of the bucket where to put the key. By default, it will be put in the default bucket. If this method is
                called with is_private = True, then the bucketName parameter will be ignored.

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the key and/or value are not strings.
        '''
        if py3utils.is_string(key) and py3utils.is_string(value) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.put(
                key, value, is_private, is_queued, table=bucketName)
        else:
            errmsg = "MicroFunctionsAPI.put(key, value) accepts a string as 'key' and 'value'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def get(self, key, is_private=False, bucketName=None):
        '''
        Access to data layer to load the value of a given key.
        The key is first checked in the transient deleted items.
        If it is not deleted, the key is then checked in the transient data bucket.
        If it is not there, it is retrieved from the global data layer.
        As a result, the value returned is consistent with
        what this function instance does with the data item.
        If the data item is not present in either the transient data bucket
        nor in the global data layer, an empty string (i.e., "") will be
        returned.
        If the function used put() and delete() operations with is_queued=False (default),
        then the checks of the transient bucket will result in empty values,
        so that the item will be retrieved from the global data layer.

        Args:
            key (string): the key of the data item
            is_private (boolean): whether the item should be read from the private data layer of the workflow; default: False
            bucketName (string): name of the bucket where to get the key from. By default, it will be fetched from the default bucket. If this method is
                called with is_private = True, then the bucketName parameter will be ignored.

        Returns:
            value (string): the value of the data item; empty string if the data item is not present.

        Raises:
            MicroFunctionsDataLayerException: when the key is not a string.
        '''
        # check first transient_output
        # if not there, return the actual (global) data layer data item
        # if not there either, return empty string (as defined in the DataLayerClient)
        if py3utils.is_string(key) and isinstance(is_private, bool):
            return self._data_layer_operator.get(key, is_private, table=bucketName)
        else:
            errmsg = "MicroFunctionsAPI.get(key) accepts a string as 'key'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def delete(self, key, is_private=False, is_queued=False, bucketName=None):
        '''
        Alias for remove(key, is_private, is_queued, tableName).
        '''
        self.remove(key, is_private, is_queued, bucketName)

    def remove(self, key, is_private=False, is_queued=False, bucketName=None):
        '''
        Access to data layer to remove data item associated with a given key.
        By default, the remove operation is reflected on the data layer immediately.
        If the delete operation is queued (i.e., is_queued = True),
        the key is removed from the transient data bucket.
        It is also added to the list of items to be deleted from the global
        data layer when the function instance finishes.

        Args:
            key (string): the key of the data item
            is_private (boolean): whether the item should be deleted from the private data layer of the workflow; default: False
            is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the delete operation will be reflected on the data layer immediately)
            bucketName (string): name of the bucket where to remove the key from. By default, it will be deleted from the default bucket.

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the key is not a string.

        '''
        if py3utils.is_string(key) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.delete(
                key, is_private, is_queued, table=bucketName)
        else:
            errmsg = "MicroFunctionsAPI.delete(key) accepts a string as 'key'"
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getKeys(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Args:
            start_index (int): the starting index of the keys to be retrieved; default: 0
            end_index (int): the end index of the keys to be retrieved; default: 2147483647
            is_private (boolean): whether the keys should be retrieved from the private data layer of the workflow; default: False

        Returns:
            List of keys (list)

        Raises:
            MicroFunctionsDataLayerException: when start_index < 0 and/or end_index > 2147483647.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if start_index >= 0 and end_index <= 2147483647 and isinstance(is_private, bool):
            return self._data_layer_operator.getKeys(start_index, end_index, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getKeys(start_index, end_index) accepts indices between 0 and 2147483647 (defaults)."
            errmsg = errmsg + "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def listKeys(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Alias for getKeys(start_index, end_index, is_private)
        '''
        return self.getKeys(start_index, end_index, is_private)

    # map operations sanity checking
    def createMap(self, mapname, is_private=False, is_queued=False):
        # _XXX_: the backend at the data layer does not create
        # sets and maps (i.e., createSet, createMap) until an entry is made
        # the addition of the entries will succeed without requiring the
        # corresponding set/map to have been created.
        '''
        Args:
            mapname (string): the name of the map to be created
            is_private (boolean): whether the map should be created in the private data layer of the workflow; default: False
            is_queued (boolean): whether the create operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the create operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the mapname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        self._logger.warning(
            "MicroFunctionsAPI.createMap() does not have an effect; it will be removed in the future.")
        self._logger.warning(
            "(Entries can still be added without calling createMap() beforehand.)")
        return
        # if py3utils.is_string(mapname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
        #    self._data_layer_operator.createMap(mapname, is_private, is_queued)
        # else:
        #    errmsg = "MicroFunctionsAPI.createMap(mapname) accepts a string as 'mapname'."
        #    errmsg = errmsg + "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
        #    raise MicroFunctionsDataLayerException(errmsg)

    def putMapEntry(self, mapname, key, value, is_private=False, is_queued=False):
        '''
        Args:
            mapname (string): the name of the map
            key (string): the key of the data item
            value (string): the value of the data item
            is_private (boolean): whether the item should be written to the private data layer of the workflow; default: False
            is_queued (boolean): whether the put operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the put operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when any of mapname, key and value is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and py3utils.is_string(key) and py3utils.is_string(value) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.putMapEntry(
                mapname, key, value, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.putMapEntry(mapname, key, value) accepts a string as 'mapname', 'key' and 'value'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getMapEntry(self, mapname, key, is_private=False):
        '''
        Args:
            mapname (string): the name of the map
            key (string): the key of the data item
            is_private (boolean): whether the item should be retrieved from the private data layer of the workflow; default: False

        Returns:
            The value associated with the key in the map (string), or empty string "" if the key does not exist.

        Raises:
            MicroFunctionsDataLayerException: when any of mapname and key is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and py3utils.is_string(key) and isinstance(is_private, bool):
            return self._data_layer_operator.getMapEntry(mapname, key, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getMapEntry(mapname, key) accepts a string as 'mapname' and 'key'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def deleteMapEntry(self, mapname, key, is_private=False, is_queued=False):
        '''
        Args:
            mapname (string): the name of the map
            key (string): the key of the data item
            is_private (boolean): whether the item should be deleted from the private data layer of the workflow; default: False
            is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the delete operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when any of mapname and key is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and py3utils.is_string(key) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.deleteMapEntry(
                mapname, key, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.deleteMapEntry(mapname, key) accepts a string as 'mapname' and 'key'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def containsMapKey(self, mapname, key, is_private=False):
        '''
        Args:
            mapname (string): the name of the map
            key (string): the key of the data item
            is_private (boolean): whether the map should be checked in the private data layer of the workflow; default: False

        Returns:
            True if key exists in the map; False otherwise (boolean)

        Raises:
            MicroFunctionsDataLayerException: when any of mapname and key is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and py3utils.is_string(key) and isinstance(is_private, bool):
            return self._data_layer_operator.containsMapKey(mapname, key, is_private)
        else:
            errmsg = "MicroFunctionsAPI.containsMapKey(mapname, key) accepts a string as 'mapname' and 'key'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getMapKeys(self, mapname, is_private=False):
        '''
        Args:
            mapname (string): the name of the map whose keys are to be retrieved
            is_private (boolean): whether the map should be retrieved from the private data layer of the workflow; default: False

        Returns:
            Set of map keys (set)

        Raises:
            MicroFunctionsDataLayerException: when the mapname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and isinstance(is_private, bool):
            return self._data_layer_operator.getMapKeys(mapname, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getMapKeys(mapname) accepts a string as 'mapname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def clearMap(self, mapname, is_private=False, is_queued=False):
        '''
        Args:
            mapname (string): the name of the map to be cleared
            is_private (boolean): whether the map should be cleared in the private data layer of the workflow; default: False
            is_queued (boolean): whether the clear operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the clear operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the mapname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.clearMap(mapname, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.clearMap(mapname) accepts a string as 'mapname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def deleteMap(self, mapname, is_private=False, is_queued=False):
        '''
        Args:
            mapname (string): the name of the map to be deleted
            is_private (boolean): whether the map should be deleted from the private data layer of the workflow; default: False
            is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the delete operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the mapname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.deleteMap(mapname, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.deleteMap(mapname) accepts a string as 'mapname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def retrieveMap(self, mapname, is_private=False):
        '''
        Args:
            mapname (string): the name of the map to be retrieved
            is_private (boolean): whether the map should be retrieved from the private data layer of the workflow; default: False

        Returns:
            Map of data items as a collection of (key, value) pairs (dict)

        Raises:
            MicroFunctionsDataLayerException: when the mapname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(mapname) and isinstance(is_private, bool):
            return self._data_layer_operator.retrieveMap(mapname, is_private)
        else:
            errmsg = "MicroFunctionsAPI.retrieveMap(mapname) accepts a string as 'mapname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getMapNames(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Args:
            start_index (int): the starting index of the map names to be retrieved; default: 0
            end_index (int): the end index of the map names to be retrieved; default: 2147483647
            is_private (boolean): whether the map names should be retrieved from the private data layer of the workflow; default: False

        Returns:
            List of map names (list)

        Raises:
            MicroFunctionsDataLayerException: when start_index < 0 and/or end_index > 2147483647.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if start_index >= 0 and end_index <= 2147483647 and isinstance(is_private, bool):
            return self._data_layer_operator.getMapNames(start_index, end_index, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getMapNames(start_index, end_index) accepts indices between 0 and 2147483647 (defaults)."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def listMaps(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Alias for getMapNames(start_index, end_index, is_private)
        '''
        return self.getMapNames(start_index, end_index, is_private)

    # set operations sanity checking
    def createSet(self, setname, is_private=False, is_queued=False):
        # _XXX_: the backend at the data layer does not create
        # sets and maps (i.e., createSet, createMap) until an entry is made
        # the addition of the entries will succeed without requiring the
        # corresponding set/map to have been created.
        '''
        Args:
            setname (string): the name of the set to be created
            is_private (boolean): whether the set should be created in the private data layer of the workflow; default: False
            is_queued (boolean): whether the create operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the create operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the setname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        self._logger.warning(
            "MicroFunctionsAPI.createSet() does not have an effect; it will be removed in the future.")
        self._logger.warning(
            "(Items can still be added without calling createSet() beforehand.)")
        return
        # if py3utils.is_string(setname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
        #    self._data_layer_operator.createSet(setname, is_private, is_queued)
        # else:
        #    errmsg = "MicroFunctionsAPI.createSet(setname) accepts a string as 'setname'."
        #    errmsg = errmsg + "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
        #    raise MicroFunctionsDataLayerException(errmsg)

    def addSetEntry(self, setname, item, is_private=False, is_queued=False):
        '''
        Args:
            setname (string): the name of the set
            item (string): the item to be added to the set
            is_private (boolean): whether the item should be written to the private data layer of the workflow; default: False
            is_queued (boolean): whether the add operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the add operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when any of setname and item is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and py3utils.is_string(item) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.addSetEntry(
                setname, item, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.addSetEntry(setname, item) accepts a string as 'setname' and 'item'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def removeSetEntry(self, setname, item, is_private=False, is_queued=False):
        '''
        Args:
            setname (string): the name of the set
            item (string): the item to be removed from the set
            is_private (boolean): whether the item should be removed from the private data layer of the workflow; default: False
            is_queued (boolean): whether the remove operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the remove operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when any of setname and item is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and py3utils.is_string(item) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.removeSetEntry(
                setname, item, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.removeSetEntry(setname, item) accepts a string as 'setname' and 'item'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def containsSetItem(self, setname, item, is_private=False):
        '''
        Args:
            setname (string): the name of the set
            item (string): the item to be checked in the set
            is_private (boolean): whether the item should be checked in the private data layer of the workflow; default: False

        Returns:
            True if item exists in the set; False otherwise (boolean)

        Raises:
            MicroFunctionsDataLayerException: when any of setname and item is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and py3utils.is_string(item) and isinstance(is_private, bool):
            return self._data_layer_operator.containsSetItem(setname, item, is_private)
        else:
            errmsg = "MicroFunctionsAPI.containsSetItem(setname, item) accepts a string as 'setname' and 'item'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def retrieveSet(self, setname, is_private=False):
        '''
        Args:
            setname (string): the name of the set to be retrieved
            is_private (boolean): whether the set should be retrieved from the private data layer of the workflow; default: False

        Returns:
            Set of set items (set)

        Raises:
            MicroFunctionsDataLayerException: when the setname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and isinstance(is_private, bool):
            return self._data_layer_operator.retrieveSet(setname, is_private)
        else:
            errmsg = "MicroFunctionsAPI.retrieveSet(setname) accepts a string as 'setname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def clearSet(self, setname, is_private=False, is_queued=False):
        '''
        Args:
            setname (string): the name of the set to be cleared
            is_private (boolean): whether the set should be cleared in the private data layer of the workflow; default: False
            is_queued (boolean): whether the clear operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the clear operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the setname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.clearSet(setname, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.clearSet(setname) accepts a string as 'setname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def deleteSet(self, setname, is_private=False, is_queued=False):
        '''
        Args:
            setname (string): the name of the set to be deleted
            is_private (boolean): whether the set should be deleted from the private data layer of the workflow; default: False
            is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the delete operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the setname is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(setname) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.deleteSet(setname, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.deleteSet(setname) accepts a string as 'setname'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getSetNames(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Args:
            start_index (int): the starting index of the set names to be retrieved; default: 0
            end_index (int): the end index of the set names to be retrieved; default: 2147483647
            is_private (boolean): whether the set names should be retrieved from the private data layer of the workflow; default: False

        Returns:
            List of set names (list)

        Raises:
            MicroFunctionsDataLayerException: when start_index < 0 and/or end_index > 2147483647.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if start_index >= 0 and end_index <= 2147483647 and isinstance(is_private, bool):
            return self._data_layer_operator.getSetNames(start_index, end_index, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getSetNames(start_index, end_index) accepts indices between 0 and 2147483647 (defaults)."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def listSets(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Alias for getSetNames(start_index, end_index, is_private)
        '''
        return self.getSetNames(start_index, end_index, is_private)

    # counter operations sanity checking
    def createCounter(self, countername, count, is_private=False, is_queued=False):
        '''
        Args:
            countername (string): the name of the counter to be created
            count (int): the initial value of the counter
            is_private (boolean): whether the counter should be created in the private data layer of the workflow; default: False
            is_queued (boolean): whether the create operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the create operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the countername is not a string and/or the initial count is not an integer.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(countername) and isinstance(count, int) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.createCounter(
                countername, count, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.createCounter(countername, count) accepts a string as 'countername' and an integer as 'count'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getCounterValue(self, countername, is_private=False):
        '''
        Args:
            countername (string): the name of the counter whose value is to be retrieved
            is_private (boolean): whether the counter should be retrieved from the private data layer of the workflow; default: False

        Returns:
            The current value of the counter (int), or None if the counter does not exist.

        Raises:
            MicroFunctionsDataLayerException: when the countername is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(countername) and isinstance(is_private, bool):
            return self._data_layer_operator.getCounterValue(countername, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getCounterValue(countername) accepts a string as 'countername'."
            raise MicroFunctionsDataLayerException(errmsg)

    def incrementCounter(self, countername, increment, is_private=False, is_queued=False):
        '''
        Args:
            countername (string): the name of the counter to be incremented
            increment (int): the value to be added to the counter
            is_private (boolean): whether the counter should be incremented in the private data layer of the workflow; default: False
            is_queued (boolean): whether the increment operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the increment operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the countername is not a string and/or the increment is not an integer.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(countername) and isinstance(increment, int) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.incrementCounter(
                countername, increment, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.incrementCounter(countername, increment) accepts a string as 'countername' and an integer as 'increment'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def decrementCounter(self, countername, decrement, is_private=False, is_queued=False):
        '''
        Args:
            countername (string): the name of the counter to be decremented
            decrement (int): the value to be subtracted from the counter
            is_private (boolean): whether the counter should be decremented in the private data layer of the workflow; default: False
            is_queued (boolean): whether the decrement operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the decrement operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the countername is not a string and/or the decrement is not an integer.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(countername) and isinstance(decrement, int) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.decrementCounter(
                countername, decrement, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.decrementCounter(countername, increment) accepts a string as 'countername' and an integer as 'decrement'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def deleteCounter(self, countername, is_private=False, is_queued=False):
        '''
        Args:
            countername (string): the name of the counter to be deleted
            is_private (boolean): whether the counter should be deleted in the private data layer of the workflow; default: False
            is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False
                (i.e., the delete operation will be reflected on the data layer immediately)

        Returns:
            None

        Raises:
            MicroFunctionsDataLayerException: when the countername is not a string.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if py3utils.is_string(countername) and isinstance(is_private, bool) and isinstance(is_queued, bool):
            self._data_layer_operator.deleteCounter(
                countername, is_private, is_queued)
        else:
            errmsg = "MicroFunctionsAPI.deleteCounter(countername) accepts a string as 'countername'."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) and is_queued (boolean) are also accepted; defaults are False."
            raise MicroFunctionsDataLayerException(errmsg)

    def getCounterNames(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Args:
            start_index (int): the starting index of the counter names to be retrieved; default: 0
            end_index (int): the end index of the counter names to be retrieved; default: 2147483647
            is_private (boolean): whether the counter names should be retrieved from the private data layer of the workflow; default: False

        Returns:
            List of counter names (list)

        Raises:
            MicroFunctionsDataLayerException: when start_index < 0 and/or end_index > 2147483647.

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for CRDTs).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        if start_index >= 0 and end_index <= 2147483647 and isinstance(is_private, bool):
            return self._data_layer_operator.getCounterNames(start_index, end_index, is_private)
        else:
            errmsg = "MicroFunctionsAPI.getCounterNames(start_index, end_index) accepts indices between 0 and 2147483647 (defaults)."
            errmsg = errmsg + \
                "\nOptionally, is_private (boolean) is also accepted; default is False."
            raise MicroFunctionsDataLayerException(errmsg)

    def listCounters(self, start_index=0, end_index=2147483647, is_private=False):
        '''
        Alias for getCounterNames(start_index, end_index, is_private)
        '''
        return self.getCounterNames(start_index, end_index, is_private)

    def get_transient_data_output(self, is_private=False):
        '''
        Returns:
            The transient data, so that it can be committed to the data layer
            when the function instance finishes.
        '''
        return self._data_layer_operator.get_transient_data_output(is_private)

    def get_data_to_be_deleted(self, is_private=False):
        '''
        Returns:
            The list of deleted data items, so that they can be committed to the data layer
            when the function instance finishes.
        '''
        return self._data_layer_operator.get_data_to_be_deleted(is_private)

    def _get_data_layer_client(self, is_private=False):
        '''
        Returns:
            The data layer client, so that it can be used to commit to the data layer
            when the function instance finishes.
            If it is not initialized yet, it will be initialized here.
        '''
        return self._data_layer_operator._get_data_layer_client(is_private)

    def _shutdown_data_layer_client(self):
        '''
        Shut down the data layer client if it has been initialized
        after the function instance finishes committing changes
        to the data layer.
        '''
        self._data_layer_operator._shutdown_data_layer_client()

    def addTriggerableBucket(self, bucketName):
        '''
        Args:
            bucketName (string): the name of the bucket to be added

        Returns:
            Boolean, indicating whether the bucket was created successfully

        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for storage triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "addTriggerableBucket",
                "data": {
                    "bucketname": bucketName
                }
            }
        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to add a triggerable bucket: " + bucketName +
                  ", Error message: " + str(message) + ", response: " + str(response))
            return False
        return True

    def addStorageTriggerForWorkflow(self, workflowName, bucketName):
        '''
        Args:
            workflowName (string): the name of the workflow to be associated with a bucket. This workflow will be triggered whenever a key is added to the associated bucket.
            bucketName (string): the name of the bucket with which to associate the workflow

        Returns:
            Boolean, indicating whether the storage trigger was created successfully

        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for storage triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "addStorageTriggerForWorkflow",
                "data": {
                    "workflowname": workflowName,
                    "bucketname": bucketName
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to add a storage trigger for workflow " + workflowName + ", Triggerable bucket " +
                  bucketName + "Error message: " + str(message) + ", response: " + str(response))
            return False
        return True

    def deleteTriggerableBucket(self, bucketName):
        '''
        Args:
            bucketName (string): the name of the bucket to delete

        Returns:
            Boolean, indicating whether the bucket was deleted successfully

        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for storage triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "deleteTriggerableBucket",
                "data": {
                    "bucketname": bucketName
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to delete a triggerable bucket: " + bucketName +
                  ", Error message: " + str(message) + ", response: " + str(response))
            return False
        return True

    def deleteStorageTriggerForWorkflow(self, workflowName, bucketName):
        '''
        Args:
            workflowName (string): the name of the workflow to disassociate from the bucket. This workflow will not be triggered anymore when a key is added to the associated bucket.
            bucketName (string): the name of the bucket currently associated with the workflow

        Returns:
            Boolean, indicating whether the storage trigger was deleted successfully

        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for storage triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "deleteStorageTriggerForWorkflow",
                "data": {
                    "workflowname": workflowName,
                    "tablename": bucketName
                }
            }
        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to delete a storage trigger for workflow " + workflowName +
                  ", Triggerable bucket " + bucketName + "Error message: " + str(message) + ", response: " + str(response))
            return False
        return True

    def _getTriggerableBuckets(self):
        '''
        Get a list of triggerable buckets. Response structure is
        {
          'status': 'success' or 'failure',
          'data': {
              'message': '...',
              'buckets': {
                  '<bucket-name-1>': [list of workflow names associated with <bucket-name-1>],
                  '<bucket-name-2>': [list of workflow names associated with <bucket-name-2>],
                  ...
              }
          }
        }
        '''
        request = \
            {
                "action": "getTriggerableBuckets",
                "data": {
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to fetch a triggerable buckets, Error message: " +
                  str(message) + ", response: " + str(response))
            return None

        return response

    def _getWorkflowDetails(self, workflowName):
        '''
        Get details of a workflow. Response structure is
        {
          'status': 'success',
          'data': {
              'email': '...',
              'name': '...',
              'id': '...',
              'status': '...',
              'endpoints': '[]',
              'modified': '...',
              'associatedTriggerableTables': {
                  '<table-name-1>': '',
                  '<table-name-2>': '',
                  ...
              },
              'associatedTriggers': {
                  '<trigger-name-1>': '' or '<local-queue-topic-name-of-a-state>',
                  '<trigger-name-2>': '' or '<local-queue-topic-name-of-a-state>',
                  ...
              }
          }
        }
        '''
        request = \
            {
                "action": "getWorkflowDetails",
                "data": {
                    "workflowname": workflowName
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            print("Error: Unable to fetch details for workflow: " + workflowName +
                  ", Error message: " + str(message) + ", response: " + str(response))
            return None
        return response

    def addTriggerTimer(self, trigger_name, trigger_info):
        if "timer_interval_ms" not in trigger_info:
            return False, "Missing parameter for timer trigger: timer_interval_ms"

        return self.addTrigger(trigger_name, trigger_info)

    def addTriggerAMQP(self, trigger_name, trigger_info):

        if "amqp_addr" not in trigger_info:
            return False, "Missing parameter for AMQP trigger: amqp_addr"

        if "routing_key" not in trigger_info:
            return False, "Missing parameter for AMQP trigger: routing_key"

        return self.addTrigger(trigger_name, trigger_info)

    def addTrigger(self, trigger_name, trigger_info):
        '''
        Args:
            trigger_name (string): User provided name for the trigger. Should be unique within this user's account.
            trigger_info (dict): Trigger specific information. {
                trigger_type (string): Type of trigger to associate with a workflow. Currently supported values: "amqp", "timer",
                For "amqp",
                    amqp_addr (string)
                    routing_key (string),
                    exchange (string), "egress_exchange" (default)
                    with_ack (boolean), False (default) - means automatic acks,
                    durable (boolean), False (default),
                    exclusive (boolean), False (default),
                    ignore_message_probability (float, range = [0.0, 100.0)), 0.0 (default),
                For 'timer',
                    timer_interval_ms: specified in milli-seconds.
            }
        Returns:
            (status, status_message)
            status (boolean) - True, if the trigger was created successfully. False, otherwise
            status_message (string) - status message, depending on 'status'
        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for message queue triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "addTrigger",
                "data": {
                    "trigger_name": trigger_name,
                    "trigger_info": trigger_info
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            error_msg = str(message) + ", response: " + str(response)
            print("Error: Unable to create trigger " + trigger_name + " with information: " + str(trigger_info) + ", Error message: " + error_msg)
            return False, error_msg
        return True, response["data"]["message"]


    def addTriggerForWorkflow(self, trigger_name, workflow_name, workflow_state=""):
        '''
        Args:
            trigger_name (string): Name of an existing trigger to a workflow to.
            workflow_name (string): Name of the workflow to add to the trigger.
            workflow_state (string): (Optional) Name of the state within the workflow to invoke from the trigger. If not specified then the entry state will be invoked by default.
        Returns:
            (status, status_message)
            status (boolean) - True, if the workflow was added to the trigger successfully. False, otherwise
            status_message (string) - status message, depending on 'status'
        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for message queue triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        workflow_state_topic = ""
        if type(workflow_state) == type("") and workflow_state is not "" and len(workflow_state) > 0:
            workflow_state_topic = self._sid + "-" + self._wid + "-" + workflow_state

        request = \
            {
                "action": "addTriggerForWorkflow",
                "data": {
                    "trigger_name": trigger_name,
                    "workflow_name": workflow_name,
                    "workflow_state": workflow_state_topic
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            error_msg = str(message) + ", response: " + str(response)
            print("Error: Unable to add trigger " + trigger_name + " for workflow " + workflow_name + ", Error message: " + error_msg)
            return False, error_msg
        return True, response["data"]["message"]


    def deleteTriggerForWorkflow(self, trigger_name, workflow_name):
        '''
        Args:
            trigger_name (string): Name of the trigger from which to remove a workflow.
            workflow_name (string): Name of the workflow to remove from the trigger.
        Returns:
            (status, status_message)
            status (boolean) - True, if the workflow was remove from this trigger successfully. False, otherwise
            status_message (string) - status message or error message, depending on 'status'
        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for message queue triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.
        '''
        request = \
            {
                "action": "deleteTriggerForWorkflow",
                "data": {
                    "trigger_name": trigger_name,
                    "workflow_name": workflow_name
                    }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            error_msg = str(message) + ", response: " + str(response)
            print("Error: Unable to remove workflow: " + workflow_name + " from the trigger: " + trigger_name + ", Error message: " + error_msg)
            return False, error_msg
        return True, response["data"]["message"]

    def deleteTrigger(self, trigger_name):
        '''
        Args:
            trigger_name (string): Name of an existing trigger to delete
        Returns:
            (status, status_message)
            status (boolean) - True, if the trigger was deleted successfully. False, otherwise
            status_message (string) - status message, depending on 'status'
        Raises:
            None

        Note:
            The usage of this function is only possible with a KNIX-specific feature (i.e., support for message queue triggers).
            Using a KNIX-specific feature might make the function incompatible with other platforms.

        '''
        request = \
            {
                "action": "deleteTrigger",
                "data": {
                    "trigger_name": trigger_name
                }
            }

        status, message, response = self._invoke_management_api(request)

        if status == False or response["status"] != 'success':
            error_msg = str(message) + ", response: " + str(response)
            print("Error: Unable to delete trigger " + trigger_name + ", Error message: " + error_msg)
            return False, error_msg
        return True, response["data"]["message"]


    def _invoke_management_api(self, request):
        status = False
        message = ""
        response_data = None

        management_url = self._get_management_endpoint()
        if management_url == "" or management_url == None:
            message = "No management endpoint url found"
            print("[invoke_management_api] Error: " + message)
            return status, message, response_data

        if type(request) != type({}):
            message = "Request must be specified as a dictionary"
            print("[invoke_management_api] Error: " + message)
            return status, message, response_data

        if "data" not in request:
            message = "Request must contain a dictionary named 'data'"
            print("[invoke_management_api] Error: " + message)
            return status, message, response_data

        request["data"]["user"] = {"token": self._usertoken}

        #print("[invoke_management_api] url: " + management_url + ", request: " + str(request))
        r = requests.post(management_url, json=request, verify=False)
        #print("[invoke_management_api] response status: " + str(r.status_code) + ", reason: " + str(r.reason) + ", body: " + str(r.text))

        response = None
        if r.text == None or r.text == "" or r.status_code > 400:
            message = "Received empty response or error status code: " + \
                str(r.status_code) + ", reason: " + \
                str(r.reason) + ", body: " + str(r.text)
            print("[invoke_management_api] Error: " + message)
            response_data = r.text
            return status, message, response

        try:
            response = json.loads(r.text)
        except Exception as e:
            message = "Json parsing error: " + \
                str(e) + ", response body: " + str(r.text)
            print("[invoke_management_api] Error: " + message)
            return status, message, response

        if type(response) == type({}) and "status" in response:
            status = True
            message = "Received a valid response from the management service"
        else:
            message = "Received an incorrectly formed reponse from the management service: response body: " + \
                str(response)
            print("[invoke_management_api] Error: " + message)

        return status, message, response

    def _get_management_endpoint(self):
        # get management endpoints from the datalayer for every request
        #management_data_layer_client = DataLayerClient(locality=1, sid="Management", wid="Management", is_wf_private=True, connect=self._datalayer)
        #management_endpoints = management_data_layer_client.get("management_endpoints")
        # if management_endpoints is None or management_endpoints == "":
        #    return ""
        # else:
        #    management_endpoints = json.loads(management_endpoints)

        # use the management endpoints obtained from the datalayer while deploying the application sandbox
        management_endpoints = self._management_endpoints

        management_url = ""
        if type(management_endpoints) == type([]) and len(management_endpoints) > 0:
            management_url = management_endpoints[random.randint(
                0, len(management_endpoints)-1)]
        return management_url
