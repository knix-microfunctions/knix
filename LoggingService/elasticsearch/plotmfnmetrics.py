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

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import argparse
import logging
import sys
import json

bar_spacing_factor = 2
barHeight = 0.6
timestamp_label_spacing = 0.1 #milliseconds
timestamp_label_height_factor = 0.4
timestamp_label_color = '#aaaaaa'
timestamp_labels = {
    "t_start_fork": "a",
    "t_start_pubutils": "b",
    "t_start_dlcbackup": "c",
    "t_start_dlcbackup_err": "c'",
    "t_start_dlcbackup_err_flag": "ce",
    "t_start_decapsulate": "d",
    "t_start_chdir": "e",
    "t_start_decodeinput": "f",
    "t_start_inputpath": "g",
    "t_start_sessutils": "h",
    "t_start_sapi": "i",
    "t_start": "j",
    "t_end": "k",
    "t_start_resultpath": "l",
    "t_start_outputpath": "m",
    "t_start_encodeoutput": "n",
    "t_start_branchterminal": "o",
    "t_start_pub": "p",
    "t_start_encapsulate": "q",
    "t_start_resultmap": "r",
    "t_start_storeoutput": "s",
    "t_start_generatenextlist": "t",
    "t_start_pubnextlist": "u",
    "t_pub_output": "v",
    "t_pub_localqueue": "w",
    "t_pub_exittopic": "x",

    "tfe_entry": "A",
    "tfe_sendlq": "E",
    #"tfe_sentlq": "G",
    "tfe_recvdlq": "H",
    "tfe_exit": "I",
    #"tfe_getparams": "",
    #"tfe_encapsulate": "",
    #"tfe_readrequest": "",
    #"tfe_schedulewait": "F",
    #"tfe_getuserdata": "",
    #"tfe_decapsulate": "",
    #"tfe_getmetadata": "",
    #"tfe_writepayload": "",
    #"tfe_beforeasync": "N",
    #"tfe_afterasync": "O",

    #"tqs_localize": "1",
    #"tqs_createmsg": "2",
    #"tqs_addmsg": "3",
    #"tqs_afteraddmsg": "",
    #"tqs_msgthread": "5",
    #"tqs_checkpublish": "6",
    #"tqs_objectMapper": "7",
    #"tqs_gqsend": "8",
    #"tqs_aftergqsend": "9"
}
#    "t_start_backtrigger": "y",
#    "t_end_fork": "z"
#}

def roundList(l):
    ret = []
    for n in l:
        ret.append(round(n*1.0,5))
    return ret

def plotmtrics(metrics, title, xmax):
    count=len(metrics)
    # Values of each group
    uc_diff = []
    wf_diff = []
    qs_diff = []
    fe_diff = []
    nx_diff = []
    fe_start = []
    fe_reqend_offset = []
    qs_start = []
    qs_reqend_offset = []
    wf_start = []
    wf_ustart_offset = []
    for metric in metrics:
        uc_diff.append(metric['wf_udiff'])
        wf_diff.append(metric['wf_diff'])
        qs_diff.append(metric['qs_diff'])
        fe_diff.append(metric['fe_diff'])
        nx_diff.append(metric['nx_diff'])

        offset = 0.0
        fe_start.append(metric['fe_start'])
        diff = metric['fe_reqdiff']
        fe_reqend_offset.append(offset + diff)
        offset = offset + diff

        qs_start.append(metric['qs_start'])
        diff = metric['qs_reqdiff']
        qs_reqend_offset.append(offset + diff)
        offset = offset + diff

        wf_start.append(metric['wf_start'])
        ustart_offset_list = []
        for ustart in metric['wf_ustart']:
            diff = ustart-metric['wf_start']
            ustart_offset_list.append(offset + diff)
        wf_ustart_offset.append(ustart_offset_list)

    # Heights of bars1 + bars2
    #gw_overhead = roundList(np.subtract(gw_diff, uc_diff).tolist())
    #gw_overhead = roundList(gw_diff)
    #fe_reqend_diff = roundList(np.subtract(fe_reqend, fe_start).tolist())
    #qs_reqend_diff = roundList(np.subtract(qs_reqend, fe_start).tolist())
    #fe_overhead = roundList(np.subtract(fe_diff, qs_diff).tolist())
    #nx_overhead = roundList(np.subtract(nx_diff, fe_diff).tolist())

    # The position of the bars on the y-axis
    r = [i for i in range(count)]
    r2 = [bar_spacing_factor*i for i in r] # these are the actual positions
    names = [str(i+1) for i in r]

    lightgreen='#2c7f2e'
    lightgreen2='#2bc652'
    darkgreen='#2d7f5e'
    darkred='#910c07'
    darkorange='#915007'

    uc_color = 'yellow'
    gw_color = darkorange
    qs_color = 'orange'
    fe_color = 'teal'
    nx_color  = lightgreen2

    rc('font', weight='bold')
    plt.figure(num=None, figsize=(16, 9), dpi=80, facecolor='w', edgecolor='k')
    rc('axes', axisbelow=True)
    mticker.Locator.MAXTICKS = 500

    # plot bars. Usercode is plotted here with zero length to make it show up in legend just once
    zeroleft = np.zeros(len(metrics)).tolist()
    #plt.barh(y=r2, width=zeroleft, left=zeroleft, color=uc_color, edgecolor='white', height=barHeight, label='Usercode')
    plt.barh(y=r2, width=nx_diff, left=zeroleft, color=nx_color, edgecolor='white', height=barHeight, label='Nginx')
    plt.barh(y=r2, width=fe_diff, left=zeroleft, color=fe_color, edgecolor='white', height=barHeight, label='Frontend')
    plt.barh(y=r2, width=qs_diff, left=fe_reqend_offset, color=qs_color, edgecolor='white', height=barHeight, label='QueueService')
    plt.barh(y=r2, width=wf_diff, left=qs_reqend_offset, color=gw_color, edgecolor='white', height=barHeight, label='FunctionWorker')
    #plt.barh(y=r2, width=uc_diff, left=wf_ustart_offset, color=uc_color, edgecolor='white', height=barHeight, label='UserCode')

    timestamp_h1 = [-barHeight/2.0, -barHeight/2.0]
    timestamp_h2 = [-timestamp_label_height_factor*barHeight, -timestamp_label_height_factor*barHeight]

    for e in range(count):
        metric = metrics[e]

        plt.barh(y=r2[e], width=uc_diff[e], left=wf_ustart_offset[e], color=uc_color, edgecolor='white', height=barHeight, label='UserCode')

        # plot work flow timestamps vertical lines
        wf_tname = []
        wf_tvalue = []
        for timestamp in metric['wf_timestamps_list']:
            tname = timestamp[1]
            if tname in timestamp_labels:
                wf_tvalue.append(qs_reqend_offset[e] + (timestamp[0]-metric['wf_start']))
                wf_tname.append(timestamp[1])
        plt.vlines(wf_tvalue, (r2[e])-barHeight/2.0, (r2[e])+barHeight/2.0, colors='w', linestyles='solid', linewidth=0.6)

        # plot timestamp labels with arrows
        for i in range(len(wf_tvalue)):
            plt.vlines(0, 0, 0, colors='k', linestyles='solid', linewidth=0.1, label=str(timestamp_labels[wf_tname[i]]))
            if i < len(wf_tvalue)-1:
                next_val = wf_tvalue[i+1]
            else:
                next_val = float('inf')
            if i ==0 or next_val-wf_tvalue[i] >= timestamp_label_spacing:
                h1 = timestamp_h1[i % len(timestamp_h1)]
                h2 = timestamp_h2[i % len(timestamp_h2)]
                if timestamp_labels[wf_tname[i]] != '':
                    plt.vlines(wf_tvalue[i], (r2[e])+h1, (r2[e])+h1+h2, colors=timestamp_label_color, linestyles='solid', linewidth=0.5)
                    plt.text(wf_tvalue[i], (r2[e])+h1+h2, str(timestamp_labels[wf_tname[i]]), ha='left', color=timestamp_label_color, fontsize=8)


        # plot frontend timestamps vertical lines
        fe_tname = []
        fe_tvalue = []
        for timestamp in metric['fe_timestamps_list']:
            tname = timestamp[1]
            if tname in timestamp_labels:
                fe_tvalue.append(timestamp[0]-metric['fe_start'])
                fe_tname.append(timestamp[1])
        plt.vlines(fe_tvalue, (r2[e])-barHeight/2.0, (r2[e])+barHeight/2.0, colors='w', linestyles='solid', linewidth=0.6)

        # plot timestamp labels with arrows
        for i in range(len(fe_tvalue)):
            plt.vlines(0, 0, 0, colors='k', linestyles='solid', linewidth=0.1, label=str(timestamp_labels[fe_tname[i]]))
            if i < len(fe_tvalue)-1:
                next_val = fe_tvalue[i+1]
            else:
                next_val = float('inf')
            if i ==0 or next_val-fe_tvalue[i] >= timestamp_label_spacing:
                h1 = timestamp_h1[i % len(timestamp_h1)]
                h2 = timestamp_h2[i % len(timestamp_h2)]
                if timestamp_labels[fe_tname[i]] != '':
                    plt.vlines(fe_tvalue[i], (r2[e])+h1, (r2[e])+h1+h2, colors=timestamp_label_color, linestyles='solid', linewidth=0.5)
                    plt.text(fe_tvalue[i], (r2[e])+h1+h2, str(timestamp_labels[fe_tname[i]]), ha='left', color=fe_color, fontsize=8)


        # plot QueueService timestamps vertical lines
        qs_tname = []
        qs_tvalue = []
        for timestamp in metric['qs_timestamps_list']:
            tname = timestamp[1]
            if tname in timestamp_labels:
                qs_tvalue.append(fe_reqend_offset[e] + (timestamp[0]-metric['qs_start']))
                qs_tname.append(timestamp[1])
        plt.vlines(qs_tvalue, (r2[e])-barHeight/2.0, (r2[e])+barHeight/2.0, colors='w', linestyles='solid', linewidth=0.6)

        # plot timestamp labels with arrows
        for i in range(len(qs_tvalue)):
            plt.vlines(0, 0, 0, colors='k', linestyles='solid', linewidth=0.1, label=str(timestamp_labels[qs_tname[i]]))
            if i < len(qs_tvalue)-1:
                next_val = qs_tvalue[i+1]
            else:
                next_val = float('inf')
            if i ==0 or next_val-qs_tvalue[i] >= timestamp_label_spacing:
                h1 = timestamp_h1[i % len(timestamp_h1)]
                h2 = timestamp_h2[i % len(timestamp_h2)]
                if timestamp_labels[qs_tname[i]] != '':
                    plt.vlines(qs_tvalue[i], (r2[e])+h1, (r2[e])+h1+h2, colors=timestamp_label_color, linestyles='solid', linewidth=0.5)
                    plt.text(qs_tvalue[i], (r2[e])+h1+h2, str(timestamp_labels[qs_tname[i]]), ha='left', color=qs_color, fontsize=8)


    plt.yticks(r2, names, fontweight='bold')
    plt.ylabel("Execution")
    plt.xlabel("Milliseconds")
    plt.title(title, loc='Center', fontsize=12)
    plt.tight_layout(pad=0.5)
    axes = plt.gca()

    if xmax > 0:
        axes.set_xlim([0,xmax])

    start, end = axes.get_xlim()
    if end-start < 500:
        axes.xaxis.set_ticks(np.arange(start, end, 5))
        for label in axes.xaxis.get_ticklabels()[1::2]:
            label.set_visible(False)

    axes.xaxis.grid(b=True, which="major", color='lightgray', linestyle='solid')
    axes.xaxis.grid(b=True, which="minor", color='lightgray', linestyle='dotted')
    axes.yaxis.set_ticks(np.arange(0, bar_spacing_factor*len(metrics), bar_spacing_factor))
    axes.invert_yaxis()
    #axes.legend(ncol=1, bbox_to_anchor=(1, 1), loc='upper right', fontsize='small')
    legend_lines = [Line2D([0], [0], color=uc_color, lw=4, label='UserCode'),
                    Line2D([0], [0], color=gw_color, lw=4, label='FunctionWorker'),
                    Line2D([0], [0], color=qs_color, lw=4, label='QueueService'),
                    Line2D([0], [0], color=fe_color, lw=4, label='Frontend'),
                    Line2D([0], [0], color=nx_color, lw=4, label='Nginx')
                ]
    for (name,short) in timestamp_labels.items():
        legend_lines.append(Line2D([0], [0], color=timestamp_label_color, lw=0, label=short + ' = ' + name))
    legend_lines.append(Line2D([0], [0], color=timestamp_label_color, lw=0, label='[label shown if diff>'+str(timestamp_label_spacing) + 'ms]'))

    axes.legend(handles=legend_lines, ncol=1, bbox_to_anchor=(1, 1), loc='upper right', fontsize='small')
    plt.minorticks_on()

    # Show graphic
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Generate plots for overhead metrics', prog='plotmfnmetrics.py')
    parser.add_argument('metricsfile', type=str, help='Json file to read metrics from')
    parser.add_argument('-t', '--title', type=str, default='MFn execution latency breakdown', help='Title for the plot')
    parser.add_argument('-x', '--xmax', type=int, default=-1, help='Max x-axis range')
    args = parser.parse_args()

    metricsfile = args.metricsfile
    title = args.title
    xmax = args.xmax

    formatstr = '%(message)s'
    logging.basicConfig(format=formatstr, level=logging.INFO, stream=sys.stdout)

    logging.info("Using file: " + str(metricsfile))
    with open(metricsfile) as f:
        metrics=json.load(f)
    logging.info("Num metrics: " + str(len(metrics)))
    logging.info("X-axis range: " + str(xmax))
    plotmtrics(metrics, title, xmax)

if __name__ == "__main__":
    main()
