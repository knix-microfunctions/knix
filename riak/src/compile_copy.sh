#!/bin/sh
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

set -x

sudo mkdir -p /usr/lib/riak/lib/mfn_counter_triggers
sudo cp mfn_counter_triggers.erl /usr/lib/riak/lib/mfn_counter_triggers/.
cd /usr/lib/riak/lib/mfn_counter_triggers
sudo /usr/lib/riak/erts-5.10.3/bin/erlc mfn_counter_triggers.erl
sudo chmod 775 mfn_counter_triggers.erl
sudo chmod 775 mfn_counter_triggers.beam
cd -

sudo mkdir -p /usr/lib/riak/lib/workflow_triggers
sudo cp workflow_triggers.erl /usr/lib/riak/lib/workflow_triggers/.
cd /usr/lib/riak/lib/workflow_triggers
sudo /usr/lib/riak/erts-5.10.3/bin/erlc workflow_triggers.erl
sudo chmod 775 workflow_triggers.erl
sudo chmod 775 workflow_triggers.beam
cd -