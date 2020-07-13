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

# If not coordinator, join it to form a cluster
# TODO: restart of coordinator node may leave it outside the cluster
if [[ -z "$($RIAK_ADMIN cluster status | grep $COORDINATOR_NODE)" ]]; then
  echo "Connecting to cluster coordinator $COORDINATOR_NODE"
  SERVICE_PORT=$(env|grep 'RK_.*_SERVICE_PORT_HTTP'|sed 's/.*=//')
  curl -s http://$COORDINATOR_NODE:${SERVICE_PORT:-8098} >/dev/null
  if [[ -z "$($RIAK_ADMIN cluster join riak@$COORDINATOR_NODE | grep 'Success')" ]]; then
    echo "[ERROR] Riak cluster join $COORDINATOR_NODE failed."
    exit 1
  else
    if [[ ! -z "($RIAK_ADMIN cluster status | grep ${HOSTNAME} | grep 'joining')" ]]; then
      if [[ -z "$($RIAK_ADMIN cluster plan | grep 'There are no staged changes')" ]]; then
        while [[ -z "$($RIAK_ADMIN ringready|grep '^TRUE')" ]]; do
          echo "Waiting for ring status to become ready"
          sleep 1
        done
        count=5
        while [ $count -gt 0 ]; do
          if [[ ! -z "($RIAK_ADMIN cluster commit | grep 'Cluster changes committed')" ]]; then
            echo "Cluster changes committed successfully."
            break
          fi
          count=$(( $count - 1 ))
          sleep 5
        done
        if [ $count -le 0 ]; then
          echo "[ERROR] Riak cluster commit failed."
	  exit 1
        fi
      fi
    fi
  fi
fi
