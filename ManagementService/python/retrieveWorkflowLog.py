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
import base64
import requests
import os

elasticsearch = os.getenv("MFN_ELASTICSEARCH", os.getenv("MFN_HOSTNAME")).split(':')[0]

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False

    email = data["email"]

    if "workflow" in data:
        workflow = data["workflow"]
        sapi.log(json.dumps(workflow))
        if "id" in workflow:
            print("Connecting to elasticsearch host: " + elasticsearch)
            num_lines = 100
            if "num_lines" in workflow:
                num_lines = int(workflow["num_lines"])
            status, result = get_workflow_log(workflow["id"], elasticsearch, 9200, num_lines)
            if status == True:
                total_log = '\n'.join(result) + '\n'
                #print('last log line: ' + result[-1])
                total_log = base64.b64encode(total_log.encode()).decode()
                wf = {}
                wf["log"] = total_log
                response_data["workflow"] = wf
                success = True
            else:
                err_str = "Couldn't retrieve log; " + result
                print(err_str)
                response_data["message"] = err_str
        else:
            response_data["message"] = "Couldn't retrieve log; malformed input."
    else:
        response_data["message"] = "Couldn't retrieve log; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.add_dynamic_workflow({"next": "ManagementServiceExit", "value":response})

    sapi.log(response["status"])

    return {}


def get_workflow_log(workflowid, es_host, es_port, num_last_entries=150):
    index="mfnwf"
    url="http://"+es_host+":" + str(es_port)

    #print("------ search all documents where workflow = <workflowid>")
    data = \
    {
        "_source":["timestamp", "asctime", "loglevel", "uuid", "function", "message"],
        "sort" : [
                {"timestamp": {"order" : "desc"}}
            ],
        "query":{
            "bool":{
                "must_not": [{"match": {"message": "[__mfn_tracing]"}}],
                "filter":[
                            { "match": {"workflowid": workflowid}}
                        ]
            }
        },
        "size": num_last_entries
    }

    try:
        r=requests.get(url+"/"+index+'/_search', json=data, proxies={"http":None})
        response = r.json()
        #print(str(response))
        if 'hits' in response:
            outlog = []
            if response['hits']['total']['value'] > 0:
                for hit in reversed(response['hits']['hits']):
                    source=hit['_source']
                    #print("DEBUG: " + str(source))
                    hit_str = '[%s] [%s] [%s] [%s] %s' % (source['asctime'], source['loglevel'], source['uuid'], source['function'], source['message'])
                    outlog.append(hit_str)
            return True, outlog
        elif 'error' in response:
            etype = response['error']['type']
            return False, etype
        else:
            return False, 'Unknown error'
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            return False, 'Could not connect to: ' + url
        else:
            raise e

