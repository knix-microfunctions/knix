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

-module(workflow_triggers).

-export([test/0, workflow_trigger/1]).

% https://github.com/spreedly/riak-postcommit-hook/blob/master/src/postcommit_hook.erl
% https://github.com/jbrisbin/riak-rabbitmq-commit-hooks/blob/master/src/riak_rabbitmq.erl
% https://riak.com/posts/technical/link-walking-by-example/index.html

-define(TMETA_BUCKET, <<"triggersInfoTable">>).

-define(LOG_PREFIX, "[WORKFLOW_TRIGGERS_v18] ").

workflow_trigger(RiakObject) ->
    try
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] Received object:~p~n", [RiakObject]),
      Action = get_action(RiakObject),
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] Action:~p~n", [Action]),
      BucketReturn = riak_object:bucket(RiakObject),
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] BucketReturn:~p~n", [BucketReturn]),
      {BucketType, Bucket} = case is_tuple(BucketReturn) of
			       true -> BucketReturn;
			       false -> {<<"default">>, BucketReturn}
			     end,
      %{BucketType, Bucket} = riak_object:bucket(RiakObject),
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] BucketType:~p, Bucket:~p~n", [BucketType, Bucket]),
      Key = riak_object:key(RiakObject),
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] Key~p~n", [Key]),
      SplitResult = string:tokens(binary_to_list(Bucket),
				  ";"),
      %io:format(?LOG_PREFIX ++ "[workflow_trigger] SplitResult~p~n", [SplitResult]),
      [Keyspace, Table] = case length(SplitResult) of
			    1 ->
				[binary_to_list(<<"__NOT_DEFINED__">>),
				 binary_to_list(<<"__NOT_DEFINED__">>)];
			    2 -> SplitResult
			  end,
      %[Keyspace, Table] = string:tokens(binary_to_list(Bucket), ";"),
      % Keyspace, Table are lists
      ActionToTake = case list_to_binary(Keyspace) of
		       <<"__NOT_DEFINED__">> -> ignore;
		       _ -> Action
		     end,
      io:format((?LOG_PREFIX) ++
		  "[workflow_trigger] ActionToTake:~p, "
		  "Bucket:~p, BucketType:~p, Keyspace: "
		  "~p, Table: ~p, Key:~p~n",
		[ActionToTake, Bucket, BucketType,
		 list_to_binary(Keyspace), list_to_binary(Table), Key]),
      %io:format(?LOG_PREFIX ++ "Value:~p~n", [Value]),
      % Metadata = json encoded list of dicts
      % each metadata dict = {"urltype": "url", "urls": "http://...", "wfname": "abcd"}
      %                 or = {"urltype": "topic", "urls": "workflow_topic", "wfname": "abcd"}
      Metadata = case ActionToTake of
		   delete -> none;
		   ignore -> none;
		   _ -> get_trigger_metadata(Keyspace, Table)
		 end,
      % Wfmeta = [meta1, meta2, ...]  = [{url1,wfname1,urltype1}, {url2,wfname2,urltype2}, ...]
      Wfmeta = case Metadata of
		 none -> none;
		 _ -> get_wf_meta(Metadata)
	       end,
      % Publishresults = [true, false, ...]
      Publishresults = case Wfmeta of
			 none -> none;
			 _ ->
			     Value = riak_object:get_value(RiakObject),
			     EncodedMessage = generate_trigger_message(Key,
								       Value,
								       Table),
			     [publish_message(EncodedMessage, Meta)
			      || Meta <- Wfmeta]
		       end,
      case Publishresults of
	none ->
	    io:format((?LOG_PREFIX) ++
			"[workflow_trigger] No message published. "
			"No associated workflows found for Bucket "
			"~p~n",
		      [Bucket]);
	_ ->
	    io:format((?LOG_PREFIX) ++
			"[workflow_trigger] Publishresults:~p~n",
		      [Publishresults])
      end
    catch
      _:Error ->
	  {error, Error},
	  io:format((?LOG_PREFIX) ++
		      "[workflow_trigger] Error: ~p~n",
		    [Error])
    end.

get_trigger_metadata(Keyspace, Table) ->
    try MetadataBucket =
	    string:concat(string:concat(Keyspace, ";"),
			  binary_to_list(?TMETA_BUCKET)),
	MetadataKey = Table,
	%io:format(?LOG_PREFIX ++ "[get_trigger_metadata] Looking up Metadata Key:~p, Bucket:~p~n", [list_to_binary(MetadataKey), list_to_binary(MetadataBucket)]),
	{ok, C} = riak:local_client(),
	PerBucketMetaObj = case
			     C:get(list_to_binary(MetadataBucket),
				   list_to_binary(MetadataKey))
			       of
			     {ok, PBMO} -> PBMO;
			     {_, StoreError} ->
				 io:format((?LOG_PREFIX) ++
					     "[get_trigger_metadata] Metadata not "
					     "found, Error: ~p, Key:~p, Bucket:~p~n",
					   [StoreError,
					    list_to_binary(MetadataKey),
					    list_to_binary(MetadataBucket)]),
				 none
			   end,
	Metadata = case PerBucketMetaObj of
		     none -> none;
		     _ ->
			 ValueMeta = riak_object:get_value(PerBucketMetaObj),
			 %io:format(?LOG_PREFIX ++ "[get_trigger_metadata] Metadata Value:~p~n", [ValueMeta]),
			 ValueMeta
		   end,
	Metadata
    catch
      _:Error ->
	  {error, Error},
	  io:format((?LOG_PREFIX) ++
		      "[get_trigger_metadata] Error: ~p~n",
		    [Error]),
	  none
    end.

get_wf_meta(Metadata) ->
    %io:format(?LOG_PREFIX ++ "[get_wf_meta] Metadata ~p~n", [Metadata]),
    try MetadataList = jiffy:decode(Metadata),
	Meta = [{proplists:get_value(<<"urls">>, X),
		 proplists:get_value(<<"wfname">>, X),
		 proplists:get_value(<<"urltype">>, X)}
		|| {X} <- MetadataList],
	case length(Meta) of
	  0 -> none;
	  _ -> Meta
	end
    catch
      _:Error ->
	  {error, Error},
	  io:format((?LOG_PREFIX) ++ "[get_wf_meta] Error: ~p~n",
		    [Error]),
	  none
    end.

publish_message(EncodedMessage, Meta) ->
    {Urls, Wfname, Urltype} = Meta,
    case length(Urls) of
      0 -> false;
      _ ->
	  io:format((?LOG_PREFIX) ++
		      "[publish_message] Urltype:~p, Urls:~p, "
		      "Wfname:~p~n",
		    [Urltype, Urls, Wfname]),
	  case Urltype of
	    <<"url">> -> publish_http_message(Urls, EncodedMessage);
	    _ -> false
	  end
    end.

publish_http_message(Urls, EncodedMessage) ->
    %PostBody = jiffy:encode(Message),
    try Url = lists:nth(crypto:rand_uniform(1,
					    length(Urls) + 1),
			Urls),
	PostBody = EncodedMessage,
	io:format((?LOG_PREFIX) ++
		    "[publish_http_message] Url:~p~n",
		  [Url]),
	{ErlangStatus, ReqResult} = httpc:request(post,
						  {binary_to_list(Url), [],
						   "application/json",
						   PostBody},
						  [], []),
	case ErlangStatus of
	  error ->
	      io:format((?LOG_PREFIX) ++
			  "[publish_http_message] Could not publish. "
			  "Error:~p~n",
			[ReqResult]),
	      false;
	  ok ->
	      {{HttpProtocol, HttpStatus, ReasonPhrase}, Headers,
	       Body} =
		  ReqResult,
	      io:format((?LOG_PREFIX) ++
			  "[publish_http_message] Result: HttpStatus:~p "
			  " ReasonPhrase:~p  Body:~p~n",
			[HttpStatus, ReasonPhrase, Body]),
	      true
	end
    catch
      _:Error ->
	  {error, Error},
	  io:format((?LOG_PREFIX) ++
		      "[publish_http_message] Error: ~p~n",
		    [Error]),
	  false
    end.

get_action(RiakObject) ->
    %io:format(?LOG_PREFIX ++ "[get_action] Getting metadata~n"),
    Metadata = riak_object:get_metadata(RiakObject),
    %io:format(?LOG_PREFIX ++ "[get_action] extracted metadata:~p~n", [Metadata]),
    case dict:find(<<"X-Riak-Deleted">>, Metadata) of
      {ok, "true"} -> delete;
      _ -> store
    end.

handle_delete() ->
    io:format((?LOG_PREFIX) ++ "Ignoring delete~n"), none.

handle_ignore() ->
    io:format((?LOG_PREFIX) ++
		"Ignoring - Bucket name does not contain "
		"a ;~n"),
    none.

handle_nometadata() ->
    io:format((?LOG_PREFIX) ++
		"[handle_nometadata] No Metadata found~n"),
    none.

generate_trigger_message(Key, Value, Table) ->
    Message = {[{<<"trigger_type">>, <<"storage">>},
		{<<"key">>, Key},
		{<<"source">>, list_to_binary(Table)}]},
    MessageEncoded = jiffy:encode(Message),
    MessageEncoded.

generate_mfn_message(Value, Executionid, Resulttopic) ->
    Metadata = {[{<<"__result_topic">>, Resulttopic},
		 {<<"__execution_id">>, Executionid},
		 {<<"__function_execution_id">>, Executionid},
		 {<<"__async_execution">>, true}]},
    Message = {[{<<"__mfnuserdata">>, Value},
		{<<"__mfnmetadata">>, Metadata}]},
    MessageEncoded = jiffy:encode(Message),
    {MessageEncoded, Executionid}.

publish_kafka_message(Topic, Key, Value) ->
    io:format((?LOG_PREFIX) ++
		"[NOT implemented publish_kafka_message] "
		"Topic:~p, Execid:~p~n",
	      [Topic, Key]),
    true.

mfn_uuid() -> list_to_binary(uuid_to_string(uuid())).

uuid() ->
    uuid(crypto:rand_uniform(1, round(math:pow(2, 48))) - 1,
	 crypto:rand_uniform(1, round(math:pow(2, 12))) - 1,
	 crypto:rand_uniform(1, round(math:pow(2, 32))) - 1,
	 crypto:rand_uniform(1, round(math:pow(2, 30))) - 1).

uuid(R1, R2, R3, R4) ->
    <<R1:48, 4:4, R2:12, 2:2, R3:32, R4:30>>.

uuid_to_string(U) ->
    lists:flatten(io_lib:format("~8.16.0b~4.16.0b~4.16.0b~2.16.0b~2.16.0b~12.1"
				"6.0b",
				uuid_parts(U))).

uuid_parts(<<TL:32, TM:16, THV:16, CSR:8, CSL:8,
	     N:48>>) ->
    [TL, TM, THV, CSR, CSL, N].

test() ->
    io:format((?LOG_PREFIX) ++ "~n"),
    Execid = mfn_uuid(),
    EncodedMessage = generate_trigger_message(<<"key1">>,
					      <<"value1">>, <<"table1">>),
    io:format((?LOG_PREFIX) ++
		"Trigger Message to publish, json encoded:~p~n",
	      [EncodedMessage]),
    publish_http_message([<<"http://httpbin.org/post">>],
			 EncodedMessage),
    Metadata = {[{<<"__execution_id">>,
		  <<"983fe4a006db11ea82b0ee39e5d2b111">>},
		 {<<"__function_execution_id">>,
		  <<"983fe4a006db11ea82b0ee39e5d2b111">>},
		 {<<"__async_execution">>, true}]},
    Message = {[{<<"__mfnuserdata">>, <<"[10]">>},
		{<<"__mfnmetadata">>, Metadata}]},
    MessageEncoded = jiffy:encode(Message),
    io:format((?LOG_PREFIX) ++ " ~p~n", [Message]),
    io:format((?LOG_PREFIX) ++ " ~p~n", [MessageEncoded]),
    io:format((?LOG_PREFIX) ++ "Execid ~p~n", [Execid]).

