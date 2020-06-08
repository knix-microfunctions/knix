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

#
# Cluster start script to bootstrap a Riak cluster.
#
set -ex

if [[ -x /usr/sbin/riak ]]; then
  export RIAK=/usr/sbin/riak
else
  export RIAK=$RIAK_HOME/bin/riak
fi
export RIAK_CONF=/etc/riak/riak.conf
export USER_CONF=/etc/riak/user.conf
export RIAK_ADVANCED_CONF=/etc/riak/advanced.config
if [[ -x /usr/sbin/riak-admin ]]; then
  export RIAK_ADMIN=/usr/sbin/riak-admin
else
  export RIAK_ADMIN=$RIAK_HOME/bin/riak-admin
fi
export SCHEMAS_DIR=/etc/riak/schemas/

# Set ports for PB and HTTP
export PB_PORT=${PB_PORT:-8087}
export HTTP_PORT=${HTTP_PORT:-8098}

# Use ping to discover our HOSTNAME because it's easier and more reliable than other methods
HOSTNAME=$(hostname -f)
export HOST=$(hostname -i)

# CLUSTER_NAME is used to name the nodes and is the value used in the distributed cookie
export CLUSTER_NAME=${CLUSTER_NAME:-riak}

# The COORDINATOR_NODE is the first node in a cluster to which other nodes will eventually join
export COORDINATOR_NODE=${COORDINATOR_NODE:-$HOSTNAME}
export COORDINATOR_NODE_HOST=$(python -c 'import socket; print(socket.gethostbyname("'${COORDINATOR_NODE}'") or "127.0.0.1");')

export ERLANG_DISTRIBUTION_PORT_RANGE_MINIMUM=${ERLANG_DISTRIBUTION_PORT_RANGE_MINIMUM:-6000}
export ERLANG_DISTRIBUTION_PORT_RANGE_MAXIMUM=${ERLANG_DISTRIBUTION_PORT_RANGE_MAXIMUM:-6999}
export LOG_CONSOLE_LEVEL=${LOG_CONSOLE_LEVEL:-debug}
export BITCASK_MERGE_POLICY=${BITCASK_MERGE_POLICY:-always}
export BITCASK_MERGE_CHECK_INTERVAL=${BITCASK_MERGE_CHECK_INTERVAL:-10m}
export BITCASK_MERGE_TRIGGERS_FRAGMENTATION=${BITCASK_MERGE_TRIGGERS_FRAGMENTATION:-60}
export BITCASK_MERGE_TRIGGERS_DEAD_BYTES=${BITCASK_MERGE_TRIGGERS_DEAD_BYTES:-128MB}
export BITCASK_MERGE_THRESHOLDS_FRAGMENTATION=${BITCASK_MERGE_THRESHOLDS_FRAGMENTATION:-40}
export BITCASK_MERGE_THRESHOLDS_DEAD_BYTES=${BITCASK_MERGE_THRESHOLDS_DEAD_BYTES:-32MB}
export BITCASK_MERGE_THRESHOLDS_SMALL_FILE=${BITCASK_MERGE_THRESHOLDS_SMALL_FILE:-20MB}
export BITCASK_MAX_FILE_SIZE=${BITCASK_MAX_FILE_SIZE:-500MB}

# Run all prestart scripts
PRESTART=$(find /etc/riak/prestart.d -name *.sh -print | sort)
for s in $PRESTART; do
  . $s
done

WAIT_FOR_ERLANG=${WAIT_FOR_ERLANG:-45}
# Start the node and wait until fully up
WAIT_FOR_ERLANG=${WAIT_FOR_ERLANG} ${RIAK} start
$RIAK_ADMIN wait-for-service riak_kv

# Run all poststart scripts
POSTSTART=$(find /etc/riak/poststart.d -name *.sh -print | sort)
for s in $POSTSTART; do
  . $s
done

# Trap SIGTERM and SIGINT and tail the log file indefinitely
tail -n 1024 -f /var/log/riak/console.log &
PID=$!
trap "/usr/lib/riak/shutdown.sh" SIGTERM SIGINT
wait $PID
