%   Copyright 2020 The KNIX Authors
%
%   Licensed under the Apache License, Version 2.0 (the "License");
%   you may not use this file except in compliance with the License.
%   You may obtain a copy of the License at
%
%       http://www.apache.org/licenses/LICENSE-2.0
%
%   Unless required by applicable law or agreed to in writing, software
%   distributed under the License is distributed on an "AS IS" BASIS,
%   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
%   See the License for the specific language governing permissions and
%   limitations under the License.

-module(mfn_counter_triggers).

-export([counter_trigger/1,test/0]).

-define(CMETA_BUCKET, <<"counterTriggersInfoTable">>).
-define(LOG_PREFIX, "[COUNTER_TRIGGERS_v10] ").

counter_trigger(RiakObject) ->
    try
        %io:format(?LOG_PREFIX ++ "[counter_trigger] Received object:~p~n", [RiakObject]),
        Action = get_action(RiakObject),
        %io:format(?LOG_PREFIX ++ "[counter_trigger] Action:~p~n", [Action]),
        BucketReturn = riak_object:bucket(RiakObject),
        %io:format(?LOG_PREFIX ++ "[counter_trigger] BucketReturn:~p~n", [BucketReturn]),
        {BucketType, Bucket} = case is_tuple(BucketReturn) of
            true -> BucketReturn;
            false -> {<<"counters">>, BucketReturn}
        end,

        %Action = get_action(RiakObject),
        %{BucketType, Bucket} = riak_object:bucket(RiakObject),
        CounterName = riak_object:key(RiakObject),
        {{_, CounterValue}, _} = riak_kv_crdt:value(RiakObject, riak_dt_pncounter),

        SplitResult = string:tokens(binary_to_list(Bucket), ";"),
        %io:format(?LOG_PREFIX ++ "[counter_trigger] SplitResult~p~n", [SplitResult]),
        [Keyspace, Table] = case length(SplitResult) of
            1 -> [binary_to_list(<<"__NOT_DEFINED__">>), binary_to_list(<<"__NOT_DEFINED__">>)];
            2 -> SplitResult
        end,
        %[Keyspace, Table] = string:tokens(binary_to_list(Bucket), ";"),  
        % Keyspace, Table are lists

        ActionToTake = case list_to_binary(Keyspace) of
            <<"__NOT_DEFINED__">> -> ignore;
            _ -> Action
        end,

        % Keyspace and Table are lists
        io:format(?LOG_PREFIX ++ "[counter_trigger] ActionToTake:~p, Bucket:~p, BucketType:~p, Keyspace: ~p, Table: ~p, CounterName:~p, CounterValue:~p~n", [ActionToTake, Bucket, BucketType, list_to_binary(Keyspace), list_to_binary(Table), CounterName, CounterValue]),

        Metadata = case ActionToTake of
            delete -> none;
            ignore -> none;
                 _ -> get_counter_metadata(Keyspace, CounterName)
        end,
        io:format(?LOG_PREFIX ++ "CounterMetadata:~p~n", [Metadata]),
        
        ShouldTrigger = case Metadata of
            none -> handle_nometadata();
               _ -> should_trigger(CounterValue, Metadata)
        end,

        case ShouldTrigger of
          true -> 
            HeaderAction = "Post-Parallel",
            {HeaderActionData, Endpoint} = generate_header_action_data(CounterValue, Metadata),
            io:format(?LOG_PREFIX ++ "HeaderActionData:~p~n", [HeaderActionData]),
            Url = string:concat(binary_to_list(Endpoint), "?async=1"),
            publish_http_message(Url, HeaderAction, HeaderActionData);
          false -> 
            io:format(?LOG_PREFIX ++ "Not Triggering counter~n");
          none -> 
            io:format(?LOG_PREFIX ++ "Metadata not found. Not triggering counter~n")
        end

    catch
        _:Error -> {error, Error},
        io:format(?LOG_PREFIX ++ "[counter_trigger] Error: ~p~n", [Error])
    end.

publish_http_message(Url, HeaderAction, HeaderActionData) ->
    io:format(?LOG_PREFIX ++ "[publish_http_message] Url:~p~n", [Url]),
    
    io:format(?LOG_PREFIX ++ "[publish_http_message] Request:~p~n", [{Url, [{"X-MFN-Action", HeaderAction}, {"X-MFN-Action-Data", binary_to_list(HeaderActionData)}], "application/json", ""}]),
    {ErlangStatus, ReqResult} = httpc:request(post, {Url, [{"X-MFN-Action", HeaderAction}, {"X-MFN-Action-Data", binary_to_list(HeaderActionData)}], "application/json", ""}, [], []),
    case ErlangStatus of
        error -> 
            io:format(?LOG_PREFIX ++ "[publish_http_message] Could not publish. Error:~p~n", [ReqResult]),
            false;
        ok ->
            {{HttpProtocol, HttpStatus, ReasonPhrase}, Headers, Body} = ReqResult,
            io:format(?LOG_PREFIX ++ "[publish_http_message] Result: HttpStatus:~p  ReasonPhrase:~p  Body:~p~n", [HttpStatus, ReasonPhrase, Body]),
            true
    end.

generate_header_action_data(CounterValue, CounterMetadataObject) -> 
    {CounterMetadata} = CounterMetadataObject,
    FunctionTopic = proplists:get_value(<<"FunctionTopic">>,CounterMetadata),
    ExecutionId = proplists:get_value(<<"ExecutionId">>,CounterMetadata),
    WorkflowInstanceMetadataStorageKey = proplists:get_value(<<"WorkflowInstanceMetadataStorageKey">>,CounterMetadata),
    Endpoint = proplists:get_value(<<"Endpoint">>,CounterMetadata),
    Action = proplists:get_value(<<"__state_action">>,CounterMetadata),
    AsyncExec = proplists:get_value(<<"__async_execution">>,CounterMetadata),
    Header = {[{<<"Key">>,ExecutionId}, {<<"Topic">>,FunctionTopic}, {<<"__state_action">>,Action}, {<<"__async_execution">>,AsyncExec}, {<<"CounterValue">>,CounterValue}, {<<"WorkflowInstanceMetadataStorageKey">>,WorkflowInstanceMetadataStorageKey}]},
    HeaderEncoded = jiffy:encode(Header),
    {HeaderEncoded, Endpoint}.


get_counter_metadata(Keyspace, CounterName) ->
    try
        MetadataBucket = string:concat(string:concat(Keyspace, ";"), binary_to_list(?CMETA_BUCKET)),
        MetadataKey = string:concat(binary_to_list(CounterName), "_metadata"),

        io:format(?LOG_PREFIX ++ "[get_trigger_metadata] Looking up Metadata Key:~p, Bucket:~p~n", [list_to_binary(MetadataKey), list_to_binary(MetadataBucket)]),
        
        {ok, C} = riak:local_client(),
        PerCounterMetaObj = case C:get(list_to_binary(MetadataBucket), list_to_binary(MetadataKey)) of
            {ok, PCMO} -> PCMO;
            {_, UpdateError} -> 
                io:format(?LOG_PREFIX ++ "[get_counter_metadata] Error: ~p~n", [UpdateError]),
                none
        end,

        Metadata = case PerCounterMetaObj of
            none -> none;
            _ -> 
                ValueMeta  = riak_object:get_value(PerCounterMetaObj),
                io:format(?LOG_PREFIX ++ "[get_trigger_metadata] Metadata Value:~p~n", [ValueMeta]),
                MetadataObject = jiffy:decode(ValueMeta),
                MetadataObject
        end,
        Metadata
    catch
        _:Error -> {error, Error},
        io:format(?LOG_PREFIX ++ "[get_counter_metadata] Error: ~p~n", [Error]),
        none
    end.


should_trigger(CounterValue, CounterMetadataObject) ->
  {CounterMetadata} = CounterMetadataObject,
  Klist = proplists:get_value(<<"Klist">>,CounterMetadata),
  MatchList = [X || X <- Klist, CounterValue == X],
  case length(MatchList) of
    1 -> true;
    _ -> false
  end.

get_action(Object) ->
    Metadata = riak_object:get_metadata(Object),
    case dict:find(<<"X-Riak-Deleted">>, Metadata) of
        {ok, "true"} -> delete;
        _ -> update
    end.

handle_delete() -> 
    io:format(?LOG_PREFIX ++ "[handle_delete] Ignoring delete~n"),
    none.

handle_nometadata() ->
    io:format(?LOG_PREFIX ++ "[handle_nometadata] No Metadata found~n"),
    none.


test() ->
    io:format(?LOG_PREFIX ++ "Test~n"),
    Action = update, 
    Bucket = <<"storage_sandATsand;counterTriggersTable">>, 
    BucketType = <<"mfn_counter_trigger">>, 
    [Keyspace, Table] = string:tokens(binary_to_list(Bucket), ";"),
    CounterName = <<"8370cf93c9f96e9581d5760ee77ef1d7-8370cf93c9f96e9581d5760ee77ef1d7-LaunchParallel_006530d7741b11ea82cf0242ac110003_counter">>, 
    CounterValue = 3,
    io:format(?LOG_PREFIX ++ "[counter_trigger] Action:~p, Bucket:~p, BucketType:~p, Keyspace: ~p, Table: ~p, CounterName:~p, CounterValue:~p~n", [Action, Bucket, BucketType, list_to_binary(Keyspace), list_to_binary(Table), CounterName, CounterValue]),  

    Metadata = case Action of
        delete -> handle_delete();
                _ -> get_counter_metadata(Keyspace, CounterName)
    end,
    io:format(?LOG_PREFIX ++ "CounterMetadata:~p~n", [Metadata]),

    Metadata = {[{<<"__state_action">>,
                                         <<"post_parallel_processing">>},
                                        {<<"__async_execution">>,false},
                                        {<<"WorkflowInstanceMetadataStorageKey">>,
                                         <<"8370cf93c9f96e9581d5760ee77ef1d7-8370cf93c9f96e9581d5760ee77ef1d7-LaunchParallel_006530d7741b11ea82cf0242ac110003_workflow_metadata">>},
                                        {<<"CounterValue">>,0},
                                        {<<"Klist">>,[3]},
                                        {<<"TotalBranches">>,3},
                                        {<<"ExecutionId">>,
                                         <<"006530d7741b11ea82cf0242ac110003">>},
                                        {<<"FunctionTopic">>,
                                         <<"8370cf93c9f96e9581d5760ee77ef1d7-8370cf93c9f96e9581d5760ee77ef1d7-LaunchParallel">>},
                                        {<<"Endpoint">>,
                                         <<"http://10.0.2.15:32780">>}]},
    ShouldTrigger = case Metadata of
        none -> handle_nometadata();
            _ -> should_trigger(CounterValue, Metadata)
    end,

    case ShouldTrigger of
        true -> 
            HeaderAction = "Post-Parallel",
            {HeaderActionData, Endpoint} = generate_header_action_data(CounterValue, Metadata),
            io:format(?LOG_PREFIX ++ "HeaderActionData:~p~n", [HeaderActionData]),
            Url = string:concat(binary_to_list(Endpoint), "?async=1"),
            publish_http_message(Url, HeaderAction, HeaderActionData);
        false -> 
            io:format(?LOG_PREFIX ++ "Not Triggering counter~n");
        none -> 
            io:format(?LOG_PREFIX ++ "Metadata not found. Not triggering counter~n")
    end.

    
