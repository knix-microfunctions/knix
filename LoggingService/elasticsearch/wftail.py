#!/usr/bin/python3

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

import argparse
import os
import requests
import json
import socket
import logging
import time
import sys
import signal

WORKFLOW_INDEX = 'mfnwf'

def get_workflow_log(eshost, esport=9200, workflowname=None, workflowid=None, userid=None, uuid=None, timestamp=None, indexedTimestamp=None, num_last_entries=150, alllogs=None, proxies=None):
    url="http://"+eshost+":" + str(esport)
    logging.debug("Url: " + url)
    data = \
    {
        #"_source": ["indexed", "timestamp", "asctime", "loglevel", "uuid", "function", "message", "workflowname", "workflowid", "userid"],
        "sort": [
                {"timestamp": {"order" : "desc"}}
            ],
        "seq_no_primary_term": True,
        "size": num_last_entries,
        "query":{
            "bool":{
                "filter": [],
                "must_not": []
            }
        }
    }

    filters = []
    if workflowname:
        filters.append({"match": {"workflowname": workflowname }})

    if workflowid:
        filters.append({"match": {"workflowid": workflowid }})

    if userid:
        filters.append({"match": {"userid": userid }})

    if uuid:
        filters.append({"match": {"uuid": uuid }})

    if timestamp:
        filters.append({"range": { "timestamp": { "gt": timestamp }}})

    if indexedTimestamp:
        filters.append({"range": { "indexed": { "gt": indexedTimestamp }}})

    data["query"]["bool"]["filter"] = filters

    must_not = []
    if alllogs == False:
        must_not.append({"match": {"message": "[__mfn_progress]"}})
        must_not.append({"match": {"message": "[__mfn_tracing]"}})
        #must_not.append({"match": {"message": "[FunctionWorker]"}})
        #must_not.append({"match": {"message": "[StateUtils]"}})

    data["query"]["bool"]["must_not"] = must_not

    logging.debug("Query data:\n" + json.dumps(data, indent=2))


    try:
        r=requests.get(url+"/"+WORKFLOW_INDEX+'/_search', json=data, proxies=proxies)

        logging.debug('Http response code: ' + str(r.status_code))
        logging.debug('Http status reason: ' + r.reason)
        logging.debug('Http response body:\n' + r.text)

        if r.status_code >= 500:
            return False, r.reason
        if r.ok == False and r.text == None:
            return False, r.reason

        response = json.loads(r.text)
        logging.debug("Query reponse:\n" + json.dumps(response, indent=2))

        if 'hits' in response:
            outlog = []
            if response['hits']['total']['value'] > 0:
                for hit in reversed(response['hits']['hits']):
                    source=hit['_source']
                    outlog.append(source)
            return True, outlog
        elif 'error' in response:
            etype = response['error']['type']
            return False, etype
        else:
            return False, 'Unknown error'
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            return False, 'Could not connect to: ' + url
        elif type(e).__name__ == 'JSONDecodeError':
            return False, 'Could decode reponse as json. Response\n' + r.text
        else:
            raise e

def printlog(outlog):
    for log in outlog:
        log_str = '[%d] [%d] [%s] [%s] [%s] [%s] [%s] [%s] [%s] %s' % (log['indexed'], log['timestamp'], log['asctime'], log['loglevel'], log['userid'], log['workflowid'], log['uuid'], log['workflowname'], log['function'], log['message'])
        logging.info(log_str)


def main():
    parser = argparse.ArgumentParser(description='Tail logs of microfunctions workflow(s) (queried from elasticsearch)', prog='wftail.py')
    parser.add_argument('-wname', '--workflowname', type=str, metavar='WORKFLOW_NAME', help='Tail logs for specific workflow name.')
    parser.add_argument('-wid', '--workflowid', type=str, metavar='WORKFLOW_ID', help='Tail logs for specific workflow id.')
    parser.add_argument('-uid', '--userid', type=str, metavar='USER_ID', help='Limit logs to workflows of a specific user.')
    parser.add_argument('-eid', '--eid', type=str, metavar='EXECUTION_UUID', help='Limit logs to a specific execution id.')
    parser.add_argument('-eshost', '--eshost', type=str, metavar='ES_HOST', default=socket.gethostname(), help='Elasticsearch host. Defaults to ' + socket.gethostname() + ':9200.')
    parser.add_argument('-n', '--num', type=int, metavar='NUMBER_OF_LINES', default=40, help='Number of last log lines to print. Defaults to 40')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
    parser.add_argument('-f', '--follow', action='store_true', help='Continuously follow logs (using elasticsearch generated timestamps at the time of ingesting logs).')
    parser.add_argument('-ft', '--followtimestamp', action='store_true', help='Continuously follow logs (using function generated timestamps).')
    parser.add_argument('-ts', '--timestamp', type=int, metavar='LAST_TIMESTAMP', default=None, help='Starting timestamp for log entries. This should be the function generated timestamp. Defaults to None')
    parser.add_argument('-a', '--all', action='store_true', help='Print all log lines, i.e., do not ignore mfn internal debug statements.')
    parser.add_argument('-p', '--proxy', action='store_true', help='Explicitly pass proxy information to the python requests package. Defaults to false. http_proxy and https_proxy are read from the environment variables.')

    args = parser.parse_args()

    workflowname = args.workflowname
    workflowid = args.workflowid
    userid = args.userid
    uuid = args.eid
    eshost = args.eshost
    if eshost:
        eshost = eshost.split(':')[0]
    num = args.num
    debug = args.debug
    followindexed = args.follow
    followtimestamp = args.followtimestamp
    timestamp = args.timestamp
    alllogs = args.all
    proxy = args.proxy

    formatstr = '%(message)s'
    if debug == True:
        logging.basicConfig(stream=sys.stdout, format=formatstr, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout, format=formatstr, level=logging.INFO)

    follow = False
    if followindexed == True or followtimestamp == True:
        follow = True

    follow_mode = 'not following'
    if follow == True:
        follow_mode = 'indexed timestamps'
        if followtimestamp == True and followindexed == False:
            follow_mode = 'function timestamps'

    http_proxy = os.getenv("http_proxy", None)
    https_proxy = os.getenv("https_proxy", None)
    proxies = {
        "http": http_proxy,
        "https": https_proxy,
    }

    logging.debug("Workflow Name: " + str(workflowname))
    logging.debug("Workflow Id: " + str(workflowid))
    logging.debug("User Id: " + str(userid))
    logging.debug("Execution uuid: " + str(uuid))
    logging.debug("Number of last log lines: " + str(num))
    logging.debug("Elasticsearch host: " + str(eshost)+ ':9200')
    logging.debug("Starting timestamp: " + str(timestamp))
    logging.debug("Follow mode: " + follow_mode)
    logging.debug("Print all log lines: " + str(alllogs))
    logging.debug("Proxies: " + str(proxies))
    logging.debug("Explicitly pass proxy to python 'requests' package: " + str(proxy))

    if proxy == False:
        proxies = None

    lastTimestamp = timestamp
    lastIndexedTimestamp = None
    while True:
        status, result = get_workflow_log(eshost, esport=9200,
                                                workflowname=workflowname,
                                                workflowid=workflowid,
                                                userid=userid, uuid=uuid,
                                                timestamp=lastTimestamp,
                                                indexedTimestamp=lastIndexedTimestamp,
                                                num_last_entries=num,
                                                alllogs=alllogs,
                                                proxies=proxies)
        if status == True:
            printlog(result)
        else:
            logging.error(result)

        if not follow:
            break;

        if len(result) == 0:
            continue

        if follow_mode == 'indexed timestamps':
            maxIndexedTimestamp = 0
            for log in result:
                if 'indexed' not in log:
                    logging.exception("Timestamp when a log entry was indexed not found ('indexed' field)." \
                        + "Please use the config_elasticsearch.py script to recreate 'mfnwf' index and to create the 'indexed' pipeline." \
                        + "Run following commands:\n (e.g. inside /opt/mfn/elasticsearch):" \
                        + "\tpython3 ./config_elasticsearch.py delete index mfnwf\n" \
                        + "\tpython3 ./config_elasticsearch.py create index mfnwf\n" \
                        + "\tpython3 ./config_elasticsearch.py create pipeline indexed\n")
                if log['indexed'] > maxIndexedTimestamp: maxIndexedTimestamp = log['indexed']
            logging.debug("maxIndexedTimestamp=" + str(maxIndexedTimestamp))
            lastIndexedTimestamp = maxIndexedTimestamp
            lastTimestamp = None
        else:
            lastTimestamp = int(result[-1]["timestamp"])
            logging.debug("lastTimestamp=" + str(lastTimestamp))
            lastIndexedTimestamp = None

        if follow:
            num = 1000
            time.sleep(1.0)

def signal_handler(signal, frame):
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
