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

RING_SIZE=$(awk -F'=' '/ring_size/{print $2}' $RIAK_CONF | sed 's/[ ]//')
CLUSTER_CONVERGENCE=${CLUSTER_CONVERGENCE:-standard}

if [[ ! -e $RIAK_ADVANCED_CONF ]]; then

cat <<END >$RIAK_ADVANCED_CONF
[
END

if [[ "fast" == "$CLUSTER_CONVERGENCE" ]]; then
cat <<END >>$RIAK_ADVANCED_CONF
  {riak_core, [
    {vnode_parallel_start, $RING_SIZE},
    {forced_ownership_handoff, $RING_SIZE},
    {handoff_concurrency, $RING_SIZE}
  ]},
END
fi

cat <<END >>$RIAK_ADVANCED_CONF
].
END
fi
