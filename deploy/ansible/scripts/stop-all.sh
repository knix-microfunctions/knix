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


if [ -e ./nginx/stop.sh ]
then
    echo "Stopping nginx"
    ./nginx/stop.sh; sleep 2
fi

if [ -e ./management/stop.sh ]
then
    echo "Stopping Management sandbox..."
    ./management/stop.sh; sleep 2
fi

if [ -e ./datalayer/stop.sh ]
then
    echo "Stopping datalayer"
    ./datalayer/stop.sh; sleep 2
fi

if [ -e ./fluentbit/stop.sh ]
then
    echo "Stopping fluent-bit"
    ./fluentbit/stop.sh; sleep 2
fi

if [ -e ./elasticsearch/stop.sh ]
then
    echo "Stopping elasticsearch"
    ./elasticsearch/stop.sh; sleep 2
fi

if [ -e ./riak/stop.sh ]
then
    echo "Stopping riak"
    ./riak/stop.sh; sleep 2
fi

echo "MFN Stopped"
