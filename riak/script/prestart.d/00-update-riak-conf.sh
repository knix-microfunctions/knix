#!/bin/bash
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

# Add standard config items
sed -i -r 's/^nodename .*$//' $RIAK_CONF
sed -i -r 's/^distributed_cookie .*$//' $RIAK_CONF
sed -i -r 's/^listener\.protobuf\.internal .*$//' $RIAK_CONF
sed -i -r 's/^listener\.http\.internal .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.distribution\.port_range\.minimum .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.distribution\.port_range\.maximum .*$//' $RIAK_CONF
sed -i -r 's/^log\.console\.level .*$//' $RIAK_CONF
sed -i -r 's/^storage_backend .*$//' $RIAK_CONF
sed -i -r 's/^leveldb\.maximum_memory\.percent .*$//' $RIAK_CONF
sed -i -r 's/^leveldb\.maximum_memory .*$//' $RIAK_CONF
sed -i -r 's/^anti_entropy .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.schedulers\.total .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.schedulers\.online .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.schedulers\.force_wakeup_interval .*$//' $RIAK_CONF
sed -i -r 's/^erlang\.schedulers\.compaction_of_load .*$//' $RIAK_CONF


cat <<END >>$RIAK_CONF
nodename = riak@$HOSTNAME
distributed_cookie = $CLUSTER_NAME
listener.protobuf.internal = 0.0.0.0:$PB_PORT
listener.http.internal = 0.0.0.0:$HTTP_PORT
erlang.distribution.port_range.minimum = $ERLANG_DISTRIBUTION_PORT_RANGE_MINIMUM
erlang.distribution.port_range.maximum = $ERLANG_DISTRIBUTION_PORT_RANGE_MAXIMUM
log.console.level = $LOG_CONSOLE_LEVEL
storage_backend = $STORAGE_BACKEND
leveldb.maximum_memory = $LEVEL_DB_MAXIMUM_MEMORY
anti_entropy = $ANTI_ENTROPY
erlang.schedulers.total = $ERLANG_SCHEDULERS_TOTAL
erlang.schedulers.online = $ERLANG_SCHEDULERS_ONLINE
erlang.schedulers.force_wakeup_interval = $ERLANG_SCHEDULERS_FORCE_WAKEUP_INTERVAL
erlang.schedulers.compaction_of_load = $ERLANG_SCHEDULERS_COMPACTION_OF_LOAD
END

# Maybe add user config items
if [ -s $USER_CONF ]; then
  cat $USER_CONF >>$RIAK_CONF
fi
