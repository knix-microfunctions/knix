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

#if [[ ! -z "$($RIAK_ADMIN cluster status | grep $COORDINATOR_NODE_HOST)" && "$COORDINATOR_NODE_HOST" == "$HOST" ]]; then
if [[ ${COORDINATOR_NODE} == ${HOSTNAME}* || ${HOSTNAME} == ${COORDINATOR_NODE}* ]]; then
# we are the coordinator and have to set up the following bucket-types once
$RIAK_ADMIN bucket-type create mfn_counter_trigger '{"props":{"postcommit":[{"mod":"mfn_counter_triggers","fun":"counter_trigger"}],"datatype":"counter"}}' || echo ""
$RIAK_ADMIN bucket-type activate mfn_counter_trigger || echo ""
$RIAK_ADMIN bucket-type create triggers '{"props":{"postcommit":[{"mod":"workflow_triggers","fun":"workflow_trigger"}]}}' || echo ""
$RIAK_ADMIN bucket-type activate triggers || echo ""
$RIAK_ADMIN bucket-type create strong '{"props":{"consistent":true}}' || echo ""
$RIAK_ADMIN bucket-type activate strong || echo ""
$RIAK_ADMIN bucket-type create counters '{"props":{"datatype":"counter"}}' || echo ""
$RIAK_ADMIN bucket-type activate counters || echo ""
$RIAK_ADMIN bucket-type create sets '{"props":{"datatype":"set"}}' || echo ""
$RIAK_ADMIN bucket-type activate sets || echo ""
$RIAK_ADMIN bucket-type create maps '{"props":{"datatype":"map"}}' || echo ""
$RIAK_ADMIN bucket-type activate maps || echo ""
fi
