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

MFN_ELASTICSEARCH = os.getenv("MFN_ELASTICSEARCH", os.getenv("MFN_HOSTNAME"))
ELASTICSEARCH_HOST = MFN_ELASTICSEARCH.split(':')[0]
try:
    ELASTICSEARCH_PORT = MFN_ELASTICSEARCH.split(':')[1]
except:
    ELASTICSEARCH_PORT = 9200

ELASTICSEARCH_URL = "http://" + ELASTICSEARCH_HOST + ":" + str(ELASTICSEARCH_PORT)

def handle(value, sapi):
    assert isinstance(value, dict)
    data = value

    response = {}
    response_data = {}

    success = False

    email = data["email"]

    if "workflow" in data:
        workflow = data["workflow"]
        if "id" in workflow:
            workflows = sapi.get(email + "_list_workflows", True)
            if workflows is not None and workflows != "":
                workflows = json.loads(workflows)
                if workflow["id"] in workflows.values():
                    #  concatenate all logs according to their types
                    total_log = ''
                    total_progress = ''
                    total_exceptions = 'total_exception'

                    print("Connecting to elasticsearch host: " + ELASTICSEARCH_URL)

                    num_lines = 500
                    if "num_lines" in workflow:
                        num_lines = int(workflow["num_lines"])

                    filters = get_log_filters(workflow)
                    status, result, progress_result, timestamp = get_workflow_log(workflow["id"], filters, num_lines)
                    if status:
                        total_log = '\n'.join(result) + '\n'
                        #print('last log line: ' + result[-1])
                        total_progress = '\n'.join(progress_result) + '\n'

                        total_log = base64.b64encode(total_log.encode()).decode()
                        total_progress = base64.b64encode(total_progress.encode()).decode()
                        total_exceptions = base64.b64encode(total_exceptions.encode()).decode()

                        wf = {}
                        wf["log"] = total_log
                        wf["progress"] = total_progress
                        wf["exceptions"] = total_exceptions
                        if timestamp is None and "ts_earliest" in workflow:
                            timestamp = workflow["ts_earliest"]
                        wf["timestamp"] = timestamp
                        response_data["workflow"] = wf
                        success = True
                    else:
                        err_str = "Couldn't retrieve log; " + result
                        print(err_str)
                        response_data["message"] = err_str

                else:
                    response_data["message"] = "Couldn't retrieve log; no such workflow."
            else:
                response_data["message"] = "Couldn't retrieve log; no such workflow."
        else:
            response_data["message"] = "Couldn't retrieve log; malformed input."
    else:
        response_data["message"] = "Couldn't retrieve log; malformed input."

    if success:
        response["status"] = "success"
    else:
        response["status"] = "failure"

    response["data"] = response_data

    sapi.log(response["status"])

    return response

def get_log_filters(workflow):
    filters = []

    # workflow id must always be present
    filters.append({ "match": {"workflowid": workflow["id"]}})
    #filters.append({"term":  { "workflowid": workflow["id"] }})

    if "ts_earliest" in workflow:
        #print("earliest ts: " + str(workflow["ts_earliest"]))
        filters.append({ "range": {"timestamp": { "gt": workflow["ts_earliest"]}}})
        #filters.append({"range": {"timestamp": {"gt": timestamp }}})

    if "ts_latest" in workflow:
        filters.append({ "range": {"timestamp": { "lt": workflow["ts_latest"]}}})

    return filters

def get_workflow_log(workflowid, filters, num_last_entries=150):
    index = "mfnwf-" + workflowid
    #print(filters)
    #print("------ search all documents where workflow = <workflowid>")
    data = \
    {
        "_source":["timestamp", "asctime", "loglevel", "uuid", "function", "message"],
        "sort" : [
            {"timestamp": {"order" : "desc"}}
            ],
        "query":{
            "bool":{
                "must_not": [{"match": {"message": "[__mfn_tracing]"}}, {"match": {"message": "[__mfn_backup]"}}],
                "filter": filters
            }
        },
        "size": num_last_entries
    }

    print(data)

    try:
        r = requests.get(ELASTICSEARCH_URL + "/" + index + '/_search', json=data, proxies={"http":None})
        response = r.json()
        #print(str(response))
        if 'hits' in response:
            outlog = []
            progresslog = []
            timestamp = None
            if response['hits']['total']['value'] > 0:
                for hit in reversed(response['hits']['hits']):
                    source = hit['_source']
                    #print("DEBUG: " + str(source))
                    msg = ""
                    if "message" in source:
                        msg = source['message']
                    if msg.find("[__mfn_progress]") == 0:
                        hit_str = '[%s] [%s] [%s] [%s] %s' % (source['asctime'], source['loglevel'], source['uuid'], source['function'], msg)
                        progresslog.append(hit_str)
                    else:
                        hit_str = '[%s] [%s] [%s] [%s] [%s] %s' % (source['timestamp'], source['asctime'], source['loglevel'], source['uuid'], source['function'], msg)
                        outlog.append(hit_str)
                    timestamp = int(source["timestamp"])
            return True, outlog, progresslog, timestamp
        elif 'error' in response:
            etype = response['error']['type']
            return False, etype, None, None
        else:
            return False, 'Unknown error', None, None
    except Exception as e:
        if type(e).__name__ == 'ConnectionError':
            return False, 'Could not connect to: ' + ELASTICSEARCH_URL, None, None
        else:
            raise e
