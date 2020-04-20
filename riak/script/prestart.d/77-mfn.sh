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

DIR="/usr/lib/riak/lib/mfn_counter_triggers"
FILE="mfn_counter_triggers.erl"

# Compile triggers
echo "Compiling triggers in ${DIR}/${FILE}"
cd ${DIR}
$(dpkg -L riak|grep /erlc$) ${FILE}
chmod 664 ${FILE%.erl}.beam
cd -


DIR="/usr/lib/riak/lib/workflow_triggers"
FILE="workflow_triggers.erl"

# Compile triggers
echo "Compiling triggers in ${DIR}/${FILE}"
cd ${DIR}
$(dpkg -L riak|grep /erlc$) ${FILE}
chmod 664 ${FILE%.erl}.beam
cd -
