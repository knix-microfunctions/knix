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

if [ -e ./riak/start.sh ]
then
    echo "Starting riak"
    ./riak/start.sh; sleep 2
fi

if [ -e ./elasticsearch/start.sh ]
then
    echo "Starting elasticsearch"
    ./elasticsearch/start.sh; sleep 2
fi

if [ -e ./fluentbit/start.sh ]
then
    echo "Starting fluent-bit"
    ./fluentbit/start.sh; sleep 2
fi

if [ -e ./datalayer/start.sh ]
then
    echo "Starting datalayer"
    ./datalayer/start.sh; sleep 2
fi

if [ -e ./sandbox/available_hosts.sh ]
then
    echo "Running available_hosts.sh"
    ./sandbox/available_hosts.sh; sleep 2
fi

if [ -e ./management/start.sh ]
then
    echo "Starting Management sandbox..."
    ./management/start.sh; sleep 2
fi

if [ -e ./nginx/start.sh ]
then
    echo "Starting nginx"
    ./nginx/start.sh; sleep 2
fi

if [ -e ./triggers_frontend/start.sh ]
then
    echo "Starting triggers frontend"
    ./triggers_frontend/start.sh; sleep 2
fi

echo "KNIX Started"
