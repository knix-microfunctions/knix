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

set -ex
#python3 ./esconfig.py get index mfnwf -eshost $(hostname) -t 2 -d
#python3 ./esconfig.py delete index mfnwf -eshost $(hostname) -t 1
#python3 ./esconfig.py create index mfnwf -eshost $(hostname) -t 1
#python3 ./esconfig.py create pipeline indexed -eshost $(hostname) -t 1


if [ 1 = 1 ]
then
    until curl http://$(hostname):9200/
    do
        sleep 1
    done

    #curl -XDELETE http://$(hostname):9200/mfnwf
    #echo "mfnwf index deleted"

    #curl --header "Content-Type: application/json" \
    #    --request PUT \
    #    --data '
    #    {
    #        "mappings": {
    #            "properties": {
    #                "indexed": {"type": "long"},
    #                "timestamp": {"type": "long"},
    #                "loglevel": {"type": "keyword"},
    #                "hostname": {"type": "keyword"},
    #                "containername": {"type": "keyword"},
    #                "uuid": {"type": "keyword"},
    #                "userid": {"type": "keyword"},
    #                "workflowname": {"type": "keyword"},
    #                "workflowid": {"type": "keyword"},
    #                "function": {"type": "keyword"},
    #                "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
    #                "message": {"type": "text"}
    #            }
    #        }
    #    }' \
    #    http://$(hostname):9200/mfnwf
    #echo "mfnwf index created"



    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '
        {
            "description": "Set a timestamp when a docuement is indexed",
            "processors": [
                {
                    "script" : {
                        "lang" : "painless",
                        "source" : "Date date = new Date();\n ctx.indexed = date.getTime();"
                    }
                }
            ]
        }' \
        http://$(hostname):9200/_ingest/pipeline/indexed
    echo "indexed pipeline created"



    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '
        {
            "mappings": {
                "properties": {
                    "indexed": {"type": "long"},
                    "timestamp": {"type": "long"},
                    "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
                    "loglevel": {"type": "keyword"},
                    "class": {"type": "keyword"},
                    "component": {"type": "keyword"},
                    "message": {"type": "text"}
                }
            }
        }' \
        http://$(hostname):9200/mfnfe
    echo "mfnfe index created"



    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '
        {
            "mappings": {
                "properties": {
                    "indexed": {"type": "long"},
                    "timestamp": {"type": "long"},
                    "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
                    "loglevel": {"type": "keyword"},
                    "class": {"type": "keyword"},
                    "component": {"type": "keyword"},
                    "message": {"type": "text"}
                }
            }
        }' \
        http://$(hostname):9200/mfnqs
    echo "mfnqs index created"



    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '
        {
            "mappings": {
                "properties": {
                    "indexed": {"type": "long"},
                    "timestamp": {"type": "long"},
                    "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
                    "loglevel": {"type": "keyword"},
                    "class": {"type": "keyword"},
                    "component": {"type": "keyword"},
                    "message": {"type": "text"}
                }
            }
        }' \
        http://$(hostname):9200/mfndl
    echo "mfndl index created"



    # strict_date_time_no_millis = yyyy-MM-dd'T'HH:mm:ssZZ
    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '
        {
            "mappings": {
                "properties": {
                    "indexed": {"type": "long"},
                    "timestamp": {"type": "double"},
                    "asctime": {"type": "date", "format": "strict_date_time_no_millis"},
                    "remoteaddr": {"type": "keyword"},
                    "remoteuser": {"type": "keyword"},
                    "request": {"type": "text"},
                    "status": {"type": "short"},
                    "bodybytes": {"type": "integer"},
                    "referer": {"type": "text"},
                    "useragent": {"type": "text"},
                    "uuid": {"type": "keyword"},
                    "component": {"type": "keyword"},
                    "message": {"type": "text"}
                }
            }
        }' \
        http://$(hostname):9200/mfnnx
    echo "mfnnx index created"

    curl --header "Content-Type: application/json" \
        --request PUT \
        --data '{"index.blocks.read_only_allow_delete": null}' \
        http://$(hostname):9200/_all/_settings
    echo "indices made writable"

fi
