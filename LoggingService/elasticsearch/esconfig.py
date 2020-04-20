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

import requests
import os
import socket
import json
import logging
import argparse
import sys
import time

formatstr = '[%(asctime)s] [%(name)s] %(message)s'
loglevel = logging.INFO
logger = None

def test_connect(basicEsUrl):
    ret, response = query_elasticsearch('GET', basicEsUrl + '/')
    if ret == False:
        logger.debug('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger.debug('test_connect response:\n' + json.dumps(response, indent=2))
        if 'cluster_uuid' in response and response['cluster_uuid'] != None:
            msg = 'Connection succeeded: ' + basicEsUrl
            logger.debug(msg)
            return True, msg
        else:
            return False, 'Connection failed: ' + basicEsUrl + ', error = ' + str(response)

def get_index(basicEsUrl, index):
    logger.info("------ get index: " + index + " on: " + basicEsUrl)
    ret, response = query_elasticsearch('GET', basicEsUrl + '/' + index)

    if ret == False:
        logger.info('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger.info('get index response:\n' + json.dumps(response, indent=2))
        if index in response and response[index] != None:
            msg = 'Index exists: ' + index
            logger.debug(msg)
            return True, msg
        elif 'error' in response:
            etype = response['error']['type']
            if etype == 'index_not_found_exception':
                msg = 'Index does not exist: ' + index
                logger.debug(msg)
                return True, msg
            else:
                return False, 'Index get error: ' + etype
        else:
            return False, 'Index get error: ' + str(response)


def init_index(basicEsUrl, index):
    logger.info("------ create index: " + index + " on: " + basicEsUrl)

    data = \
        {
            "mappings": {
                "properties": {
                    "indexed": {"type": "long"},
                    "timestamp": {"type": "long"},
                    "loglevel": {"type": "keyword"},
                    "hostname": {"type": "keyword"},
                    "containername": {"type": "keyword"},
                    "uuid": {"type": "keyword"},
                    "userid": {"type": "keyword"},
                    "workflowname": {"type": "keyword"},
                    "workflowid": {"type": "keyword"},
                    "function": {"type": "keyword"},
                    "asctime": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSS"},
                    "message": {"type": "text"}
                }
            }
        }

    ret, response = query_elasticsearch('PUT', basicEsUrl + '/' + index, data)

    if ret == False:
        logger.info('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger. info('create index response:\n' + json.dumps(response, indent=2))
        if 'acknowledged' in response and response['acknowledged'] == True:
            msg = 'Index created: ' + index
            logger.debug(msg)
            return True, msg
        elif 'error' in response:
            etype = response['error']['type']
            if etype == 'resource_already_exists_exception':
                msg = 'Index already exists: ' + index
                logger.debug(msg)
                return True, msg
            else:
                return False, 'Index creation error: ' + etype
        else:
            return False, 'Index creation error: ' + str(response)

def delete_index(basicEsUrl, index):
    logger.info("------ delete index: " + index + ' on: ' + basicEsUrl)

    ret, response = query_elasticsearch('DELETE', basicEsUrl + '/' + index)

    if ret == False:
        logger.error('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger.info('delete index response:\n' + json.dumps(response, indent=2))
        if 'acknowledged' in response and response['acknowledged'] == True:
            msg = 'Index deleted: ' + index
            logger.debug(msg)
            return True, msg
        elif 'error' in response:
            etype = response['error']['type']
            if etype == 'index_not_found_exception':
                msg = 'Index does not exist: ' + index
                logger.debug(msg)
                return True, msg
            else:
                msg = 'Index deletion error: ' + etype
                logger.error(msg)
                return False, msg
        else:
            msg = 'Index deletion error: ' + str(response)
            logger.error(msg)
            return False, msg

def create_pipeline(basicEsUrl, pipeline):
    logger.info("------ create pipeline: " + pipeline + ' on: ' + basicEsUrl)

    data = \
        {
            "description": "Set a timestamp when a docuement is indexed",
            "processors": [
                {
                    "script" : {
                        "lang" : "painless",
                        "source" : "Date date = new Date();\n" + "ctx." + pipeline +  " = date.getTime();"
                    }
                }
            ]
        }

    ret, response = query_elasticsearch('PUT', basicEsUrl + '/' + '_ingest/pipeline/' + pipeline, data)

    if ret == False:
        logger.error('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger.info('create pipeline response:\n' + json.dumps(response, indent=2))
        if 'acknowledged' in response and response['acknowledged'] == True:
            msg = 'Pipeline created: ' + pipeline
            logger.debug(msg)
            return True, msg
        elif 'error' in response:
            msg = 'Pipeline creation error: ' + response['error']['type']
            logger.error(msg)
            return False, msg
        else:
            msg = 'Pipeline creation error: ' + str(response)
            logger.error(msg)
            return False, msg


def delete_pipeline(basicEsUrl, pipeline):
    logger.info("------ delete pipeline: " + pipeline + ' on: ' + basicEsUrl)

    ret, response = query_elasticsearch('DELETE', basicEsUrl + '/' + '_ingest/pipeline/' + pipeline)

    if ret == False:
        logger.error('query_elasticsearch returned error: ' + response)
        return False, response
    else:
        logger.info('delete pipeline response:\n' + json.dumps(response, indent=2))
        if 'acknowledged' in response and response['acknowledged'] == True:
            msg = 'Pipeline deleted: ' + pipeline
            logger.debug(msg)
            return True, msg
        elif 'error' in response:
            etype = response['error']['type']
            if etype == 'resource_not_found_exception':
                msg = 'Pipeline does not exist: ' + pipeline
                logger.debug(msg)
                return True, msg
            else:
                msg = 'Pipeline deletion error: ' + etype
                logger.error(msg)
                return False, msg
        else:
            msg = 'Pipeline deletion error: ' + str(response)
            logger.error(msg)
            return False, msg


def http_request(http_method, http_url, json_data=None):
    if http_method == 'GET' \
        or http_method == 'POST' \
        or http_method == 'PUT' \
        or http_method == 'DELETE':

        logger.debug('Http method: ' + http_method)
        logger.debug('Http url: ' + http_url)
        logger.debug('Http body:\n' +str(json_data))

        try:
            r = requests.request(method=http_method, url=http_url, json=json_data, timeout=2)

            logger.debug('Http response code: ' + str(r.status_code))
            logger.debug('Http status reason: ' + r.reason)
            logger.debug('Http response body:\n' + r.text)

            if r.status_code >= 500:
                return False, r.reason
            if r.ok == False and r.text == None: 
                return False, r.reason
            return True, r.text

        except Exception as e:
            if type(e).__name__ == 'ConnectionError':
                msg = 'Could not connect to: ' + http_url
                logger.debug(msg)
                return False, msg
            else:
                raise e
    else:
        msg = 'Unknown http method: ' + http_method
        logger.error(msg)
        return False, msg


def query_elasticsearch(http_method, http_url, json_data=None):
    ret, response = http_request(http_method, http_url, json_data)
    if ret == False:
        logger.debug('http_request returned error: ' + response)
        return False, response

    try:
        response = json.loads(response)
        logger.debug('Elasticsearch response:\n' + json.dumps(response, indent=2))
        if 'error' in response:
            logger.debug('Elasticsearch response contains an error: ' + response['error']['type'])
        return True, response
    except Exception as e:
        if type(e).__name__ == 'JSONDecodeError':
            return False, 'Could decode reponse as json. Response:\n' + response
        else:
            raise e

def init_logger(name, loglevel, formatstr, file=None):
    #logging.basicConfig(level=loglevel, format=formatstr, stream=sys.stdout)
    #logger = logging.getLogger()
    #return logger

    # to create a named logger
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)

    # stream handler
    streamhandler = logging.StreamHandler(stream=sys.stdout)
    streamhandler.setFormatter(logging.Formatter(formatstr))
    logger.addHandler(streamhandler)

    # file handler if present
    if file:
        filehandler = logging.FileHandler(file, 'a')
        filehandler.setFormatter(logging.Formatter(formatstr))
        logger.addHandler(filehandler)

    return logger


def main():
    parser = argparse.ArgumentParser(description='Configure mfn elasticsearch', prog='config_elasticsearch.py')
    parser.add_argument('action', type=str, help='<create|delete|get>')
    parser.add_argument('resource', type=str, help='<index|pipeline>')
    parser.add_argument('name', type=str, help='Name of either an index or a pipeline')
    parser.add_argument('-eshost', type=str, metavar='ES_HOST', default=socket.gethostname(), help='Elasticsearch host. Defaults to ' + socket.gethostname() + ':9200.')
    parser.add_argument('-t', '--timeout', type=int, default=5, help='Connection timeout in seconds. Defaults to 30 seconds.')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
    args = parser.parse_args()

    action = args.action
    resource = args.resource
    name = args.name
    debug = args.debug
    eshost = args.eshost
    timeout = args.timeout

    global logger
    global loglevel
    global formatstr
    if debug == True: loglevel = logging.DEBUG
    
    logger = init_logger('ConfigElasticsearch', loglevel, formatstr, None)

    if eshost:
        eshost = eshost.split(':')[0]
    basicEsUrl="http://" + eshost + ":" + str(9200)

    ret = False
    for i in range(timeout):
        ret, value = test_connect(basicEsUrl)
        logger.info(value)
        if ret == False: 
            time.sleep(1)
            continue
        else: 
            break;

    if ret == False:
        logger.error("Connection timeout")
        sys.exit(1)

    ret = False
    if action == 'delete' and resource == 'index':
        ret, value = delete_index(basicEsUrl, name)
        logger.info(value)
    elif action == 'create' and resource == 'index':
        ret, value = init_index(basicEsUrl, name)
        logger.info(value)
    elif action == 'create' and resource == 'pipeline':
        ret, value = create_pipeline(basicEsUrl, name)
        logger.info(value)
    elif action == 'delete' and resource == 'pipeline':
        ret, value = delete_pipeline(basicEsUrl, name)
        logger.info(value)
    elif action == 'get' and resource == 'index':
        ret, value = get_index(basicEsUrl, name)
        logger.info(value)
    elif action == 'connect':
        ret, value = test_connect(basicEsUrl)
        logger.info(value)
    else:
        logger.info("Unsupported action")
    if ret == False:
        sys.exit(1)

if __name__ == "__main__":
    main()