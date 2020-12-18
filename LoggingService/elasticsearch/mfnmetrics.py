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
import re

NGINX_INDEX= 'mfnnx'
COMPONENT_INDEXES= 'mfnfe,mfnqs,mfnnx'

def get_metric_logs_from_all_components(workflow_id, eshost, esport=9200, uuids=None, proxies=None, debugReadFromFile=False):
    # Form elasticsearch query
    status, request = form_query(uuids)
    if status == False:
        logging.info("Error while forming query data: " + request)
        return False, request

    # Execute the query
    if debugReadFromFile == False:
        status, output = query_elasticsearch(workflow_id, eshost, esport, request, proxies)
        if status == False:
            logging.debug("query_elasticsearch error: " + output)
            return False, output
        with open('esresult.json', 'w') as fp:
            json.dump(output, fp, indent=2)
        logging.debug('Written esresult.json')
    else:
        with open('esresult.json', 'r') as fp:
            status = True
            output = json.load(fp)
            logging.debug("# WARNING: read output from esresults.json")
            logging.debug(json.dumps(output, indent=2))

    # process output
    all_uuid_metrics = {}
    for hit in output:
        metric = None
        status = False
        index = hit['_index']
        if index == 'mfnfe':
            status, output = handleFrontendLogline(hit)
        elif index == 'mfnqs':
            status, output = handleQueueServiceLogline(hit)
        elif index == 'mfnwf-' + workflow_id:
            status, output = handleWorkflowTraceLogline(hit)
        elif index == 'mfnnx':
            status, output = handleNginxLogline(hit)
        else:
            return False, "Unknown value in the _index field for the hit:\n" + json.dumps(hit, indent=2)

        if status == False:
            logging.debug("Error while parsing logline. " + output + "  Logline: " + json.dumps(hit))
            if 'RegularExpressionNotMatched' in output:
                logging.debug("Ignoring logline")
                continue
            else:
                return False, output

        # add the metric to a map whose keys are the execution ids and the value will be the metric info collected till now
        logline_uuid = output[0]
        logline_metrics = output[1]
        status, msg = add_metric(all_uuid_metrics, logline_uuid, logline_metrics, index)
        if status == False:
            logging.debug("Error: " + msg)
            return False, msg

    #return True, all_uuid_metrics
    intermediate_uuid_metrics = {}
    for uuid in all_uuid_metrics:
        logging.debug("Processing uuid: " + uuid)
        status, output = compute_overheads(all_uuid_metrics[uuid], uuid)
        if status == False:
            logging.debug("Ignoring uuid: " + uuid + ": " + output)
            continue
        else:
            intermediate_uuid_metrics[uuid] = output

    final_uuid_metrics = []
    for uuid in uuids:
        if uuid in intermediate_uuid_metrics:
            final_uuid_metrics.append(intermediate_uuid_metrics[uuid])

    return True, final_uuid_metrics


def add_metric(all_uuid_metrics, uuid, metrics, component):
    if uuid not in all_uuid_metrics:
        all_uuid_metrics[uuid] = \
        {
            'uuid': None,
            'timestamp': None,
            'nx_diff': 0,
            'nx_size': 0,
            'fe_diff': 0,
            'fe_reqdiff': 0,
            'fe_resdiff': 0,
            'fe_unknown': 0,
            'fe_req_size': None,
            'fe_res_size': None,
            'fe_start': 0,
            'fe_reqend': 0,
            'fe_resstart': 0,
            'fe_end': 0,
            'fe_req_timestamps': [],
            'fe_res_timestamps': [],
            'qs_diff': 0,
            'qs_reqdiff': 0,
            'qs_resdiff': 0,
            'qs_unknown': 0,
            'qs_req_size': 0,
            'qs_res_size': 0,
            'qs_start': 0,
            'qs_reqend': 0,
            'qs_resstart': 0,
            'qs_end': 0,
            'qs_req_timestamps': [],
            'qs_res_timestamps': [],
            'wf_diff': 0,
            'wf_usum': 0,
            'wf_exitsize': None,
            'wf_start': 0,
            'wf_end': 0,
            'wf_num': 0,
            'wf_names': 0,
            'wf_timestamps': [],
            'wf_fdiff': 0,
            'wf_fstart': 0,
            'wf_fend': 0,
            'wf_udiff': 0,
            'wf_ustart': 0,
            'wf_uend': 0,
            'fe_timestamps_list': [],
            'qs_timestamps_list': [],
            'wf_timestamps_list': [],
        }

    uuid_metrics = all_uuid_metrics[uuid]
    for metric_name in metrics:
        if metric_name not in uuid_metrics:
            logging.debug("Ignoring unknown metric: " + metric_name + " for component: " + component)
            continue
        if uuid_metrics[metric_name] == None:
            uuid_metrics[metric_name] = metrics[metric_name]
            continue
        if uuid_metrics[metric_name] != None:
            if type(uuid_metrics[metric_name]) == type([]):
                uuid_metrics[metric_name].append(metrics[metric_name])
                continue
            else:
                return False, "Not expecting more than one value per uuid for the metric: " + metric_name
    return True, ""


def compute_overheads(metrics, uuid):
    metrics['uuid'] = uuid

    # Frontend timestamps
    ftreq = metrics['fe_req_timestamps']
    ftres = metrics['fe_res_timestamps'][0]

    metrics['fe_start'] = metrics['timestamp'] = ftres['tfe_entry']
    metrics['fe_reqend'] = ftres['tfe_sendlq']
    metrics['fe_resstart'] = ftres['tfe_rcvdlq']
    metrics['fe_end'] = ftres['tfe_exit']

    metrics['fe_reqdiff'] = metrics['fe_reqend'] - metrics['fe_start']
    metrics['fe_resdiff'] = metrics['fe_end'] - metrics['fe_resstart']
    metrics['fe_diff'] = metrics['fe_end'] -  metrics['fe_start']

    ft_list = []
    if ftreq is not None:
        for tname in ftreq:
            ft_list.append([ftreq[tname], tname])
    if ftres is not None:
        for tname in ftres:
            ft_list.append([ftres[tname], tname])
    ft_list.sort(key=lambda tup: tup[0])
    metrics['fe_timestamps_list'] = ft_list

    qt_list = []
    '''
    # Queueservice timestamps
    qtreq = metrics['qs_req_timestamps']
    qtres = metrics['qs_res_timestamps']

    metrics['qs_start'] = qtreq['tqs_localize']
    metrics['qs_reqend'] = qtreq['tqs_addmsg']
    metrics['qs_resstart'] = qtres['tqs_msgthread']
    metrics['qs_end'] = qtres['tqs_gqsend']

    metrics['qs_reqdiff'] = metrics['qs_reqend'] - metrics['qs_start']
    metrics['qs_resdiff'] = metrics['qs_end'] - metrics['qs_resstart']
    metrics['qs_diff'] = metrics['qs_end'] -  metrics['qs_start']

    for tname in qtreq:
        qt_list.append([qtreq[tname], tname])
    for tname in qtres:
        qt_list.append([qtres[tname], tname])
    qt_list.sort(key=lambda tup: tup[0])
    '''
    metrics['qs_timestamps_list'] = qt_list

    try:
        wft = metrics['wf_timestamps']
        wft.sort(key=lambda tup: tup[0])

        wf_num = len(wft)
        wf_timestamps_list = []
        wf_names = []
        wf_timestamps = []
        wf_fdiff = []
        wf_fstart = []
        wf_fend = []
        wf_udiff = []
        wf_ustart = []
        wf_uend = []
        wf_usum = 0.0
        wf_end = None

        for i in range(wf_num):
            # each ft = [fork_start_time, function_name, wf_timestamp_map]
            ft = wft[i]
            fname = ft[1]
            ftmap = ft[2]

            wf_names.append(fname)
            wf_timestamps.append(ftmap)
            wf_fstart.append(ftmap['t_start_fork'])
            wf_fend.append(ftmap['t_end_fork'])
            wf_ustart.append(ftmap['t_start'])
            wf_uend.append(ftmap['t_end'])
            wf_fdiff.append(ftmap['t_end_fork'] - ftmap['t_start_fork'])
            udiff = ftmap['t_end'] - ftmap['t_start']
            wf_udiff.append(udiff)
            wf_usum = wf_usum + udiff

            if 't_pub_exittopic' in ftmap:
                if wf_end != None:
                    return False, "Multiple worflow exit timestamps found for uuid: " + uuid
                wf_end = ftmap['t_pub_exittopic']

            for tstamp in ftmap:
                wf_timestamps_list.append([ftmap[tstamp], tstamp])

        metrics['wf_start'] = wf_fstart[0]

        if wf_end == None or metrics['wf_exitsize'] == None:
            return False, "No workflow exit timestamp found for execution id: " + uuid
        metrics['wf_end'] = wf_end

        metrics['wf_diff'] = metrics['wf_end'] - metrics['wf_start']
        metrics['wf_usum'] = wf_usum
        wf_timestamps_list.sort(key=lambda tup: tup[0])
        metrics['wf_timestamps_list'] = wf_timestamps_list
        metrics['wf_num'] = wf_num
        metrics['wf_names'] = wf_names
        metrics['wf_timestamps'] = wf_timestamps
        metrics['wf_fdiff'] = wf_fdiff
        metrics['wf_fstart'] = wf_fstart
        metrics['wf_fend'] = wf_fend
        metrics['wf_udiff'] = wf_udiff
        metrics['wf_ustart'] = wf_ustart
        metrics['wf_uend'] = wf_uend

        metrics['fe_unknown'] = metrics['fe_diff'] - (metrics['fe_reqdiff'] + metrics['fe_resdiff'] + metrics['qs_diff'])
        '''
        metrics['qs_unknown'] = metrics['qs_diff'] - (metrics['qs_reqdiff'] + metrics['qs_resdiff'] + metrics['wf_diff'])

        if metrics['nx_diff'] > metrics['fe_diff'] \
                and metrics['fe_diff'] > metrics['qs_diff'] \
                and metrics['qs_diff'] > metrics['wf_diff'] \
                and metrics['fe_unknown'] >= 0.0 \
                and metrics['qs_unknown'] >= 0.0:
            return True, metrics
        else:
            return False, "subcomponent diff greater than component diff for uuid: " + uuid + " metrics: " + str(metrics)
        '''
        return True, metrics
    except Exception as e:
        return False, "Exception while computing overheads: " + str(e)


def form_query(uuids=None):
    if uuids == None:
        return False, "No execution id specified"

    if type(uuids) != type([]):
        return False, "execution id(s) should be a list"

    num_ids = len(uuids)
    num_records = num_ids*50

    '''
    the data structure that we are trying to create = should_contain_uuid_list
        "should": [
            { "match": { "message": "848bdf22e50f11e9b3ec0242087f5bec"}},
            { "match": { "message": "8efdab59e50f11e9b3ec0242087f5bec"}},
            { "match": { "message": "a0d6e9f3e50f11e9b3ec0242087f5bec"}},
            {
                "bool": {
                    "should": [
                        { "match": { "uuid": "848bdf22e50f11e9b3ec0242087f5bec"}},
                        { "match": { "uuid": "8efdab59e50f11e9b3ec0242087f5bec"}},
                        { "match": { "uuid": "a0d6e9f3e50f11e9b3ec0242087f5bec"}}
                    ]
                }
            }
        ]
    '''

    should_contain_uuid_list = \
    [
        {
            "bool": {
                "should": []
            }
        }
    ]
    sub_list_should_contain_uuid_list = []

    for uuid in uuids:
        should_contain_uuid_list.append({ "match": { "message": uuid}})
        sub_list_should_contain_uuid_list.append({ "match": { "uuid": uuid}})
    should_contain_uuid_list[0]["bool"]["should"] = sub_list_should_contain_uuid_list

    request = \
    {
        "sort": {"indexed": {"order" : "desc"}},
        "query":{
            "bool":{
                "filter": [
                    {
                        "bool": {
                            "should": should_contain_uuid_list
                        }
                    },
                    {
                        "bool": {
                            "should": [
                                { "match": { "message": "ReceivedUserRequest"}},
                                { "match": { "message": "ResumedUserSession"}},
                                { "match": { "message": "NewReqGQ"}},
                                { "match": { "message": "PubToGQ"}},
                                { "match": { "message": "__mfn_tracing"}},
                                { "match": { "request": "workflow"}}
                            ]
                        }
                    }
                ],
                "must_not": [
                    { "match": { "message": "RecoveryManager"}},
                    { "match": { "message": "__mfn_backup"}},
                    { "match": { "message": "MFN_FRONTEND_INSTRUCTS"}}
                ]
            }
        },
        "size": num_records
    }

    logging.debug("Query data:\n" + json.dumps(request, indent=2))
    return True, request

def handleFrontendLogline(hit):
    # The two possible log lines for an execution id
    # "[ReceivedUserRequest] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [115] [TimestampMap] [{"tfe_dopost":1571739686872,"tfe_encapsulate":1571739686882,"tfe_readrequest":1571739686878,"tfe_schedulewait":1571739686889,"tfe_sendkafka":1571739686889,"tfe_genuuid":1571739686878,"tfe_afterkafka":1571739686906,"tfe_getparams":1571739686872}] [TReadRequest] [0] [TGetParams] [6] [EntryTopic] [Management-Management-ManagementServiceEntry] [ResultTopic] [MFN_RESULTS_paarijaat-debian-vm] [Request] {\"action\":\"getFunctions\",\"data\":{\"user\":{\"token\":\"93088225fa8403a1f8787da91e8e0e97db20fa352325bf84122b6 [...]"
    # "[ResumedUserSession] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [793] [TimestampMap] [{"tfe_getuserdata":1571739687248,"tfe_beforeasync":1571739687248,"tfe_decapsulate":1571739687248,"tfe_consumeresult":1571739687248,"tfe_getmetadata":1571739687248,"tfe_writepayload":1571739687248,"tfe_afterasync":1571739687251}] [LatencyRoundtrip] [376] [Response] {\"__mfnuserdata\": \"{\\\"status\\\": \\\"success\\\", \\\"data\\\": {\\\"functions\\\": [{\\\"name\\\": \\\"function1\\\", \\\"run [...]"
    regex = r"^\[(?P<logtype>[^\]]+)\] \[ExecutionId\] \[(?P<uuid>[^\]]+)\] \[Size\] \[(?P<size>[^\]]+)\] \[TimestampMap\] \[(?P<tmap>[^\]]+)\] (?P<message>.*)?$"
    try:
        source = hit['_source']
        message = source['message']
        matches = re.search(regex, message)
        if matches == None:
            return False, "RegularExpressionNotMatched: Frontend logline did not match regular expression. Logline: " + message
        logtype = matches.group('logtype')
        uuid = matches.group('uuid')
        size = int(matches.group('size'))
        tmap = json.loads(matches.group('tmap'))
    except Exception as e:
        return False, "Frontend logline regular expression matching error: " + str(e)

    metric = {}
    ttype = ''
    if logtype == 'ReceivedUserRequest':
        metric['fe_req_size'] = size
        ttype = 'req'
    elif logtype == 'ResumedUserSession':
        metric['fe_res_size'] = size
        ttype = 'res'
    else:
        return False, "Frontend logline unknown: logtype (" + logtype + "). Logline: " + message

    fe_timestamp_list = []
    for tname in tmap.keys():
        if tname.find('tfe_',0) == 0:
            fe_timestamp_list.append([float(tmap[tname]), tname])
    fe_timestamp_list.sort(key=lambda tup: tup[0])

    fe_timestamp_map = {}
    for tstamp in fe_timestamp_list:
        fe_timestamp_map[tstamp[1]] = tstamp[0]

    if ttype == 'req':
        metric['fe_req_timestamps'] = fe_timestamp_map
    else:
        metric['fe_res_timestamps'] = fe_timestamp_map

    logging.debug("Parsed Frontend logline: " + json.dumps(metric))
    return True, (uuid, metric)
    '''
    {
        "_index": "mfnfe",
        "_type": "_doc",
        "_id": "GCb88m0BeUWyxtePXOB-",
        "_score": null,
        "_source": {
            "indexed": 1571739688062,
            "message": "[ReceivedUserRequest] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [115] [TimestampMap] [{\"tfe_dopost\":1571739686872,\"tfe_encapsulate\":1571739686882,\"tfe_readrequest\":1571739686878,\"tfe_schedulewait\":1571739686889,\"tfe_sendkafka\":1571739686889,\"tfe_genuuid\":1571739686878,\"tfe_afterkafka\":1571739686906,\"tfe_getparams\":1571739686872}] [TReadRequest] [0] [TGetParams] [6] [EntryTopic] [Management-Management-ManagementServiceEntry] [ResultTopic] [MFN_RESULTS_paarijaat-debian-vm] [Request] {\"action\":\"getFunctions\",\"data\":{\"user\":{\"token\":\"93088225fa8403a1f8787da91e8e0e97db20fa352325bf84122b6 [...]",
            "component": "fe_paarijaat-debian-vm",
            "@timestamp": "2019-10-22T12:21:26.907Z",
            "loglevel": "INFO",
            "asctime": "2019-10-22 12:21:26.907",
            "class": "org.microfunctions.http_frontend.HttpFrontendServlet",
            "timestamp": 1571739686907
        },
        "sort": [
        1571739688062
        ]
    },
    {
        "_index": "mfnfe",
        "_type": "_doc",
        "_id": "HCb88m0BeUWyxtePaOAE",
        "_score": null,
        "_source": {
            "indexed": 1571739691012,
            "message": "[ResumedUserSession] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [793] [TimestampMap] [{\"tfe_getuserdata\":1571739687248,\"tfe_beforeasync\":1571739687248,\"tfe_decapsulate\":1571739687248,\"tfe_consumeresult\":1571739687248,\"tfe_getmetadata\":1571739687248,\"tfe_writepayload\":1571739687248,\"tfe_afterasync\":1571739687251}] [LatencyRoundtrip] [376] [Response] {\"__mfnuserdata\": \"{\\\"status\\\": \\\"success\\\", \\\"data\\\": {\\\"functions\\\": [{\\\"name\\\": \\\"function1\\\", \\\"run [...]",
            "component": "fe_paarijaat-debian-vm",
            "@timestamp": "2019-10-22T12:21:27.252Z",
            "loglevel": "INFO",
            "asctime": "2019-10-22 12:21:27.252",
            "class": "org.microfunctions.http_frontend.HttpFrontendServer",
            "timestamp": 1571739687252
        },
        "sort": [
        1571739691012
        ]
    }
    '''

def handleQueueServiceLogline(hit):
    # The two possible log lines for an execution id
    # "[NewReqGQ] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [398] [TimestampMap] [{"tqs_addmsg":1571739686919,"tqs_localize":1571739686909,"tqs_afteraddmsg":1571739686986,"tqs_createmsg":1571739686909}] [topic] [Management-Management-ManagementServiceEntry] [partition] 2 [offset] 251 [value] {\"__mfnmetadata\":{\"__result_topic\":\"MFN_RESULTS_paarijaat-debian-vm\",\"__execution_id\":\"b4aa051af4b511e9929a024259760599\",\"__async_execution\":false,\"__function_execution_id\":\"b4aa051af4b511e9929a024259760599\",\"__timestamp_frontend_entry\":1571739686872},\"__m"
    # "[PubToGQ] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [793] [TimestampMap] [{"tqs_aftergqsend":1571739687305,"tqs_msgthread":1571739687209,"tqs_checkpublish":1571739687211,"tqs_gqsend":1571739687236}] [topic] [MFN_RESULTS_paarijaat-debian-vm] [value] {\"__mfnuserdata\": \"{\\\"status\\\": \\\"success\\\", \\\"data\\\": {\\\"functions\\\": [{\\\"name\\\": \\\"function1\\\", \\\"runtime\\\": \\\"Python 2.7\\\", \\\"modified\\\": 1571053662.269648, \\\"id\\\": \\\"1bbb7c4011557fafdb56449d922dc889\\\"}, {\\\"name\\\": \\\"function2\\\", \\\"runtime\\\": \\\"Python 2.7\\"
    regex = r"^\[(?P<logtype>[^\]]+)\] \[ExecutionId\] \[(?P<uuid>[^\]]+)\] \[Size\] \[(?P<size>[^\]]+)\] \[TimestampMap\] \[(?P<tmap>[^\]]+)\] (?P<message>.*)?$"
    try:
        source = hit['_source']
        message = source['message']
        matches = re.search(regex, message)
        if matches == None:
            return False, "RegularExpressionNotMatched: Queueservice logline did not match regular expression. Logline: " + message
        logtype = matches.group('logtype')
        uuid = matches.group('uuid')
        size = int(matches.group('size'))
        tmap = json.loads(matches.group('tmap'))
    except Exception as e:
        return False, "Queueservice logline regular expression matching error: " + str(e)

    metric = {}
    ttype = ''
    if logtype == 'NewReqGQ':
        metric['qs_req_size'] = size
        ttype = 'req'
    elif logtype == 'PubToGQ' and 'MFN_RESULTS_' in matches.group('message'):
        metric['qs_res_size'] = size
        ttype = 'res'

    else:
        return False, "Queueservice logline unknown: logtype (" + logtype + "). Logline: " + message

    qs_timestamp_list = []
    for tname in tmap.keys():
        if tname.find('tqs_',0) == 0:
            qs_timestamp_list.append([float(tmap[tname]), tname])
    qs_timestamp_list.sort(key=lambda tup: tup[0])

    qs_timestamp_map = {}
    for tstamp in qs_timestamp_list:
        qs_timestamp_map[tstamp[1]] = tstamp[0]
    if ttype == 'req':
        metric['qs_req_timestamps'] = qs_timestamp_map
    else:
        metric['qs_res_timestamps'] = qs_timestamp_map

    logging.debug("Parsed Queueservice logline: " + json.dumps(metric))
    return True, (uuid,metric)
    '''
    {
        "_index": "mfnqs",
        "_type": "_doc",
        "_id": "ESb88m0BeUWyxtePXOBe",
        "_score": null,
        "_source": {
            "indexed": 1571739688027,
            "message": "[NewReqGQ] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [398] [TimestampMap] [{\"tqs_addmsg\":1571739686919,\"tqs_localize\":1571739686909,\"tqs_afteraddmsg\":1571739686986,\"tqs_createmsg\":1571739686909}] [topic] [Management-Management-ManagementServiceEntry] [partition] 2 [offset] 251 [value] {\"__mfnmetadata\":{\"__result_topic\":\"MFN_RESULTS_paarijaat-debian-vm\",\"__execution_id\":\"b4aa051af4b511e9929a024259760599\",\"__async_execution\":false,\"__function_execution_id\":\"b4aa051af4b511e9929a024259760599\",\"__timestamp_frontend_entry\":1571739686872},\"__m",
            "component": "qs_paarijaat-debian-vm",
            "@timestamp": "2019-10-22T12:21:26.986Z",
            "loglevel": "INFO",
            "asctime": "2019-10-22 12:21:26.986",
            "class": "org.microfunctions.queue.coordination.QueueShoveler",
            "timestamp": 1571739686986
        },
        "sort": [
        1571739688027
        ]
    },
    {
        "_index": "mfnqs",
        "_type": "_doc",
        "_id": "FCb88m0BeUWyxtePXOBe",
        "_score": null,
        "_source": {
            "indexed": 1571739688029,
            "message": "[PubToGQ] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [793] [TimestampMap] [{\"tqs_aftergqsend\":1571739687305,\"tqs_msgthread\":1571739687209,\"tqs_checkpublish\":1571739687211,\"tqs_gqsend\":1571739687236}] [topic] [MFN_RESULTS_paarijaat-debian-vm] [value] {\"__mfnuserdata\": \"{\\\"status\\\": \\\"success\\\", \\\"data\\\": {\\\"functions\\\": [{\\\"name\\\": \\\"function1\\\", \\\"runtime\\\": \\\"Python 2.7\\\", \\\"modified\\\": 1571053662.269648, \\\"id\\\": \\\"1bbb7c4011557fafdb56449d922dc889\\\"}, {\\\"name\\\": \\\"function2\\\", \\\"runtime\\\": \\\"Python 2.7\\",
            "component": "qs_paarijaat-debian-vm",
            "@timestamp": "2019-10-22T12:21:27.305Z",
            "loglevel": "INFO",
            "asctime": "2019-10-22 12:21:27.305",
            "class": "org.microfunctions.queue.coordination.MessageHandlerThread",
            "timestamp": 1571739687305
        },
        "sort": [
        1571739688029
        ]
    }
    '''

def handleWorkflowTraceLogline(hit):
    # The one possible log line for each function in the workflow. So there could be more than one log line for an execution id (example below is a chain)
    # '[__mfn_tracing] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [986] [TimestampMap] [{"t_start_fork": 1571739687042.7546, "t_start_pubutils": 1571739687044.0874, "t_start_backdatalayer": 1571739687044.9763, "t_start_backdatalayer_r": 1571739687049.6255, "t_start_decapsulate": 1571739687055.0776, "t_start_chdir": 1571739687055.2263, "t_start_decodeinput": 1571739687055.3474, "t_start_inputpath": 1571739687055.374, "t_start_sessutils": 1571739687055.3857, "t_start_sapi": 1571739687055.3875, "t_start": 1571739687055.4817, "t_end": 1571739687206.275, "t_start_resultpath": 1571739687206.275, "t_start_outputpath": 1571739687206.283, "t_start_encodeoutput": 1571739687206.2866, "t_start_branchterminal": 1571739687206.316, "t_pub_start": 1571739687206.3228, "t_start_pub": 1571739687206.3228, "t_start_encapsulate": 1571739687206.5505, "t_start_resultmap": 1571739687206.5754, "t_start_storeoutput": 1571739687206.7979, "t_start_generatenextlist": 1571739687206.8994, "t_start_pubnextlist": 1571739687206.9102, "t_pub_output": 1571739687206.914, "t_pub_exittopic": 1571739687207.1194, "exitsize": 986, "t_start_backtrigger": 1571739687212.4636, "t_pub_end": 1571739687218.1326, "t_end_pub": 1571739687218.1326, "t_end_fork": 1571739687218.1326, "function_instance_id": "b4aa051af4b511e9929a024259760599_0_Management-Management-getFunctions"}] [b4aa051af4b511e9929a024259760599_0_Management-Management-getFunctions]'
    # '[__mfn_tracing] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [0] [TimestampMap] [{"t_start_fork": 1571739686986.8462, "t_start_pubutils": 1571739686988.2312, "t_start_backdatalayer": 1571739686988.434, "t_start_backdatalayer_r": 1571739686989.3364, "t_start_decapsulate": 1571739686993.1328, "t_start_chdir": 1571739686993.3489, "t_start_decodeinput": 1571739686993.4695, "t_start_inputpath": 1571739686993.4968, "t_start_sessutils": 1571739686993.5105, "t_start_sapi": 1571739686993.5146, "t_start": 1571739686993.5974, "t_end": 1571739687011.1548, "t_start_resultpath": 1571739687011.1548, "t_start_outputpath": 1571739687011.1646, "t_start_encodeoutput": 1571739687011.176, "t_start_branchterminal": 1571739687011.1855, "t_pub_start": 1571739687011.1938, "t_start_pub": 1571739687011.1938, "t_start_encapsulate": 1571739687011.64, "t_start_resultmap": 1571739687011.7385, "t_start_storeoutput": 1571739687012.518, "t_start_generatenextlist": 1571739687041.171, "t_start_pubnextlist": 1571739687041.191, "t_pub_output": 1571739687041.1938, "t_pub_localqueue": 1571739687041.3213, "t_start_backtrigger": 1571739687045.6545, "t_pub_end": 1571739687048.2244, "t_end_pub": 1571739687048.2244, "t_end_fork": 1571739687048.2244, "function_instance_id": "b4aa051af4b511e9929a024259760599_Management-Management-ManagementServiceEntry"}] [b4aa051af4b511e9929a024259760599_Management-Management-ManagementServiceEntry]'
    regex = r"^\[(?P<logtype>[^\]]+)\] \[ExecutionId\] \[(?P<uuid>[^\]]+)\] \[Size\] \[(?P<size>[^\]]+)\] \[TimestampMap\] \[(?P<tmap>[^\]]+)\] (?P<message>.*)?$"
    try:
        source = hit['_source']
        message = source['message']
        matches = re.search(regex, message)
        if matches == None:
            return False, "RegularExpressionNotMatched Workflow logline: " + message
        logtype = matches.group('logtype')
        uuid = matches.group('uuid')
        size = int(matches.group('size'))
        tmap = json.loads(matches.group('tmap'))
    except Exception as e:
        return False, "Workflow logline regular expression matching error: " + str(e)

    metric = {}
    forkt = 0.0
    if logtype == '__mfn_tracing':
        forkt = tmap['t_start_fork']
        if 'exitsize' in tmap:
            metric['wf_exitsize'] = tmap['exitsize']
    else:
        return False, "Workflow logline unknown logtype (" + logtype + "). Logline: " + message

    wf_timestamp_list = []
    for tname in tmap.keys():
        if tname.find('t_',0) == 0:
            wf_timestamp_list.append([float(tmap[tname]), tname])
    wf_timestamp_list.sort(key=lambda tup: tup[0])

    wf_timestamp_map = {}
    for tstamp in wf_timestamp_list:
        wf_timestamp_map[tstamp[1]] = tstamp[0]

    metric['wf_timestamps'] = [forkt, tmap['function_instance_id'], wf_timestamp_map]

    logging.debug("Parsed workflow logline: " + json.dumps(metric))
    return True, (uuid,metric)
    '''
    {
        "t_start_fork": 1571739687042.7546,
        "t_start_pubutils": 1571739687044.0874,
        "t_start_backdatalayer": 1571739687044.9763,
        "t_start_backdatalayer_r": 1571739687049.6255,
        "t_start_decapsulate": 1571739687055.0776,
        "t_start_chdir": 1571739687055.2263,
        "t_start_decodeinput": 1571739687055.3474,
        "t_start_inputpath": 1571739687055.374,
        "t_start_sessutils": 1571739687055.3857,
        "t_start_sapi": 1571739687055.3875,
        "t_start": 1571739687055.4817,
        "t_end": 1571739687206.275,
        "t_start_resultpath": 1571739687206.275,
        "t_start_outputpath": 1571739687206.283,
        "t_start_encodeoutput": 1571739687206.2866,
        "t_start_branchterminal": 1571739687206.316,
        "t_pub_start": 1571739687206.3228,
        "t_start_pub": 1571739687206.3228,
        "t_start_encapsulate": 1571739687206.5505,
        "t_start_resultmap": 1571739687206.5754,
        "t_start_storeoutput": 1571739687206.7979,
        "t_start_generatenextlist": 1571739687206.8994,
        "t_start_pubnextlist": 1571739687206.9102,
        "t_pub_output": 1571739687206.914,
        "t_pub_exittopic": 1571739687207.1194,
        "t_pub_localqueue": 1571739687041.3213,
        "exitsize": 986,
        "t_start_backtrigger": 1571739687212.4636,
        "t_pub_end": 1571739687218.1326,
        "t_end_pub": 1571739687218.1326,
        "t_end_fork": 1571739687218.1326,
        "function_instance_id": "b4aa051af4b511e9929a024259760599_0_Management-Management-getFunctions"
    }
    {
        "_index": "mfnwf",
        "_type": "_doc",
        "_id": "Gib88m0BeUWyxtePZOAW",
        "_score": null,
        "_source": {
        "containername": "a2ffd534edab",
        "workflowname": "Management",
        "indexed": 1571739690005,
        "message": "[__mfn_tracing] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [986] [TimestampMap] [{\"t_start_fork\": 1571739687042.7546, \"t_start_pubutils\": 1571739687044.0874, \"t_start_backdatalayer\": 1571739687044.9763, \"t_start_backdatalayer_r\": 1571739687049.6255, \"t_start_decapsulate\": 1571739687055.0776, \"t_start_chdir\": 1571739687055.2263, \"t_start_decodeinput\": 1571739687055.3474, \"t_start_inputpath\": 1571739687055.374, \"t_start_sessutils\": 1571739687055.3857, \"t_start_sapi\": 1571739687055.3875, \"t_start\": 1571739687055.4817, \"t_end\": 1571739687206.275, \"t_start_resultpath\": 1571739687206.275, \"t_start_outputpath\": 1571739687206.283, \"t_start_encodeoutput\": 1571739687206.2866, \"t_start_branchterminal\": 1571739687206.316, \"t_pub_start\": 1571739687206.3228, \"t_start_pub\": 1571739687206.3228, \"t_start_encapsulate\": 1571739687206.5505, \"t_start_resultmap\": 1571739687206.5754, \"t_start_storeoutput\": 1571739687206.7979, \"t_start_generatenextlist\": 1571739687206.8994, \"t_start_pubnextlist\": 1571739687206.9102, \"t_pub_output\": 1571739687206.914, \"t_pub_exittopic\": 1571739687207.1194, \"exitsize\": 986, \"t_start_backtrigger\": 1571739687212.4636, \"t_pub_end\": 1571739687218.1326, \"t_end_pub\": 1571739687218.1326, \"t_end_fork\": 1571739687218.1326, \"function_instance_id\": \"b4aa051af4b511e9929a024259760599_0_Management-Management-getFunctions\"}] [b4aa051af4b511e9929a024259760599_0_Management-Management-getFunctions]",
        "uuid": "b4aa051af4b511e9929a024259760599",
        "userid": "admin@management",
        "hostname": "paarijaat-debian-vm",
        "@timestamp": "2019-10-22T10:21:27.218Z",
        "loglevel": "INFO",
        "function": "getFunctions",
        "asctime": "2019-10-22 10:21:27.218",
        "workflowid": "Management",
        "timestamp": 1571739687218452
        },
        "sort": [
        1571739690005
        ]
    },
    {
        "_index": "mfnwf",
        "_type": "_doc",
        "_id": "GSb88m0BeUWyxtePZOAW",
        "_score": null,
        "_source": {
        "containername": "a2ffd534edab",
        "workflowname": "Management",
        "indexed": 1571739690004,
        "message": "[__mfn_tracing] [ExecutionId] [b4aa051af4b511e9929a024259760599] [Size] [0] [TimestampMap] [{\"t_start_fork\": 1571739686986.8462, \"t_start_pubutils\": 1571739686988.2312, \"t_start_backdatalayer\": 1571739686988.434, \"t_start_backdatalayer_r\": 1571739686989.3364, \"t_start_decapsulate\": 1571739686993.1328, \"t_start_chdir\": 1571739686993.3489, \"t_start_decodeinput\": 1571739686993.4695, \"t_start_inputpath\": 1571739686993.4968, \"t_start_sessutils\": 1571739686993.5105, \"t_start_sapi\": 1571739686993.5146, \"t_start\": 1571739686993.5974, \"t_end\": 1571739687011.1548, \"t_start_resultpath\": 1571739687011.1548, \"t_start_outputpath\": 1571739687011.1646, \"t_start_encodeoutput\": 1571739687011.176, \"t_start_branchterminal\": 1571739687011.1855, \"t_pub_start\": 1571739687011.1938, \"t_start_pub\": 1571739687011.1938, \"t_start_encapsulate\": 1571739687011.64, \"t_start_resultmap\": 1571739687011.7385, \"t_start_storeoutput\": 1571739687012.518, \"t_start_generatenextlist\": 1571739687041.171, \"t_start_pubnextlist\": 1571739687041.191, \"t_pub_output\": 1571739687041.1938, \"t_pub_localqueue\": 1571739687041.3213, \"t_start_backtrigger\": 1571739687045.6545, \"t_pub_end\": 1571739687048.2244, \"t_end_pub\": 1571739687048.2244, \"t_end_fork\": 1571739687048.2244, \"function_instance_id\": \"b4aa051af4b511e9929a024259760599_Management-Management-ManagementServiceEntry\"}] [b4aa051af4b511e9929a024259760599_Management-Management-ManagementServiceEntry]",
        "uuid": "b4aa051af4b511e9929a024259760599",
        "userid": "admin@management",
        "hostname": "paarijaat-debian-vm",
        "@timestamp": "2019-10-22T10:21:27.048Z",
        "loglevel": "INFO",
        "function": "ManagementServiceEntry",
        "asctime": "2019-10-22 10:21:27.048",
        "workflowid": "Management",
        "timestamp": 1571739687048592
        },
        "sort": [
        1571739690004
        ]
    },
    '''

def handleNginxLogline(hit):
    # The one possible log line for each execution id
    # "[rt=0.394 uct=0.000 uht=0.396 urt=0.396]"
    regex = r"^\[rt=(?P<rt>[^ ]*) uct=(?P<uct>[^ ]*) uht=(?P<uht>[^ ]*) urt=(?P<urt>[^ ]*)\]$"
    try:
        source = hit['_source']
        message = source['message']
        matches = re.search(regex, message)
        if matches == None:
            return False, "RegularExpressionNotMatched: Nginx logline did not match regular expression. Logline: " + message
        urt = float(matches.group('urt'))*1000.0
        uct = float(matches.group('uct'))*1000.0
        uuid = source['uuid']
        timestamp = float(source['timestamp']*1000.0)
        size = int(source['bodybytes'])
    except Exception as e:
        return False, "Nginx logline regular expression matching error: " + str(e) + "  Logline: " + str(source)

    metric = {}
    metric['nx_diff'] = urt+uct
    metric['nx_size'] = size
    return True, (uuid,metric)
    '''
    The one possible log line for an execution id. This log line is generated after the execution finishes
    {
        "_index": "mfnnx",
        "_type": "_doc",
        "_id": "Gyb88m0BeUWyxtePZ-D_",
        "_score": null,
        "_source": {
        "remoteaddr": "10.0.2.2",
        "request": "POST /workflow/management/management/ManagementServiceEntry HTTP/1.1",
        "referer": "http://192.168.56.1:8888/index.html",
        "indexed": 1571739691006,
        "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
        "message": "[rt=0.394 uct=0.000 uht=0.396 urt=0.396]",
        "uuid": "b4aa051af4b511e9929a024259760599",
        "remoteuser": "-",
        "component": "nx_paarijaat-debian-vm",
        "@timestamp": "2019-10-22T10:21:27.000Z",
        "bodybytes": "261",
        "asctime": "2019-10-22T12:21:27+02:00",
        "timestamp": 1571739687.255,
        "status": "200"
        },
        "sort": [
        1571739691006
        ]
    },
    '''

def query_elasticsearch(wid, eshost, esport, request, proxies):
    url="http://"+eshost+":" + str(esport)
    logging.debug("Url: " + url)

    try:
        r=requests.get(url+"/"+COMPONENT_INDEXES+ ",mfnwf-" + wid + '/_search', json=request, proxies=proxies)

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
            if response['hits']['total']['value'] > 0:
                return True, response['hits']['hits']
            else:
                return False, "No hits found"
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
    logging.info(json.dumps(outlog, indent=2))
    #for log in outlog:
    #    log_str = '[%d] [%s] [%s] [%s] %s' % (log['indexed'], str(log['timestamp']), log['asctime'], log['uuid'], log['message'])
    #    logging.info(log_str)


def main():
    parser = argparse.ArgumentParser(description='Generate overhead metrics and timestamps for microfunctions workflow executions', prog='mfnmetrics.py')
    parser.add_argument('-wid', '--wid', metavar='WORKFLOW_ID', help='Workflow id to determine the index.')
    parser.add_argument('-eid', '--eid', nargs='+', metavar='EXECUTION_UUIDS', help='Generate metric for specific execution id(s).')
    parser.add_argument('-eidfile', '--eidfile', type=str, help="Read execution ids from the given file (with 1 uuid per line); overrides -eid option")
    parser.add_argument('-eshost', '--eshost', type=str, metavar='ELASTICSEARCH_HOST', default=socket.gethostname(), help='Elasticsearch host. Defaults to ' + socket.gethostname() + ':9200.')
    #parser.add_argument('-n', '--num', type=int, metavar='NUMBER_OF_EXECUTIONS', default=10, help='Number of last executions to consider. Defaults to 10. Applies only when -eid option is not used')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
    #parser.add_argument('-f', '--follow', action='store_true', help='Continuously monitor new executions and generate metrics.')
    parser.add_argument('-p', '--proxy', action='store_true', help='Explicitly pass proxy information to the python requests package. Defaults to false. http_proxy and https_proxy are read from the environment variables.')
    parser.add_argument('-rf', '--readfile', action='store_true', help='Read json input from esresult.json, instead of contacting elasticsearch. DEV Debugging only.')

    args = parser.parse_args()

    workflow_id = args.wid

    eidfilename = args.eidfile
    if eidfilename is None:
        uuids = args.eid
    else:
        uuids = []
        with open(eidfilename, "r") as f:
            lines = f.readlines()
        for line in lines:
            uuids.append(line.strip())
    eshost = args.eshost
    if eshost:
        eshost = eshost.split(':')[0]
    #num = args.num
    debug = args.debug
    #followindexed = args.follow
    proxy = args.proxy
    debugReadFromFile = args.readfile

    formatstr = '%(message)s'
    if debug == True:
        logging.basicConfig(format=formatstr, level=logging.DEBUG, stream=sys.stdout)
    else:
        logging.basicConfig(format=formatstr, level=logging.INFO, stream=sys.stdout)

    http_proxy = os.getenv("http_proxy", None)
    https_proxy = os.getenv("https_proxy", None)
    proxies = {
        "http": http_proxy,
        "https": https_proxy,
    }

    logging.debug("Workflow id: " + str(workflow_id))
    logging.debug("Execution uuid(s): " + str(uuids))
    logging.debug("Elasticsearch host: " + str(eshost)+ ':9200')
    logging.debug("Proxies: " + str(proxies))
    logging.debug("Explicitly pass proxy to python 'requests' package: " + str(proxy))

    if proxy == False:
        proxies = None

    status, result = get_metric_logs_from_all_components(workflow_id, eshost, esport=9200, uuids=uuids, proxies=proxies, debugReadFromFile=debugReadFromFile)
    if status == True:
        printlog(result)
    else:
        logging.error(result)

def signal_handler(signal, frame):
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
