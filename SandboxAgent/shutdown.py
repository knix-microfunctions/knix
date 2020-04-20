#!/usr/bin/python

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

import json
import logging
import os
import sys

import requests

sys.path.insert(1, os.path.join(sys.path[0], '../FunctionWorker/python'))
from LocalQueueClient import LocalQueueClient
from LocalQueueClientMessage import LocalQueueClientMessage


def find_queue(logger):
    queue = os.getenv("MFN_QUEUE")
    if 'KUBERNETES_SERVICE_HOST' in os.environ and "MFN_HOSTNAME" in os.environ:
        # On K8s, sandboxes are run with MFN_HOSTNAME = kubernetes node name
        # Find host-local queue and datalayer endpoints
        with open('/var/run/secrets/kubernetes.io/serviceaccount/token','r') as f:
            token=f.read()
        with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace','r') as f:
            namespace=f.read()
        nodename = os.getenv("MFN_HOSTNAME")
        k8sport = os.getenv('KUBERNETES_SERVICE_PORT_HTTPS')

        # Find queue endpoint
        resp = requests.get(
            'https://kubernetes.default:'+k8sport+'/api/v1/namespaces/'+namespace+'/endpoints/'+queue.split('.',1)[0],
            headers={"Authorization": "Bearer "+token,"Accept": "application/json"},
            verify='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
            proxies={"https":""})
        try:
            resp.raise_for_status()
            qeps = resp.json()
            for addr in qeps["subsets"][0]["addresses"]:
                if addr["nodeName"] == nodename:
                    print("Found our queue at "+addr["ip"])
                    queue = addr["ip"]+":"+str(qeps["subsets"][0]["ports"][0]["port"])
                    break
        except (requests.exceptions.HTTPError, KeyError) as e:
            logger.error(resp.text, e)
    return queue


if __name__ == "__main__":
    logger = logging.getLogger()
    queue = find_queue(logger)
    sandboxid = os.getenv("SANDBOXID")
    print("Send shutdown message to sandboxagent")
    shutdown_message = {}
    shutdown_message["action"] = "shutdown"

    lqcm_shutdown = LocalQueueClientMessage(key="0l", value=json.dumps(shutdown_message))

    local_queue_client = LocalQueueClient(connect=queue)
    sandboxagent_topic = "instructions_"+sandboxid
    ack = local_queue_client.addMessage(sandboxagent_topic, lqcm_shutdown, True)
    while not ack:
        ack = local_queue_client.addMessage(sandboxagent_topic, lqcm_shutdown, True)
