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

import yaml

def convert(s):
    try:
        return float(s)
    except:
        pass
    if s.endswith("m"):
        return float(s[:-1])/1_000.0
    if s.endswith("i"):
        if s.endswith("ki"):
            return float(s[:-2])/1_000_000.0
        elif s.endswith("Mi"):
            return float(s[:-2])/1_000.0
        elif s.endswith("Gi"):
            return float(s[:-2])
    raise Exception("Can't convert resource amount: "+s)

with open("microfunctions/values.yaml","r") as f:
    values = yaml.load(f)


comp = [
    {
        "name": "Riak",
        "num": values["riak"]["replicas"],
        "container": {
            "server": values["riak"]["resources"]
        },
        "storage": {}
    },
    {
        "name": "Elasticsearch",
        "num": 1,
        "container": {
            "server": values["elastic"]["resources"]
        },
        "storage": {}
    },
    {
        "name": "Datalayer",
        "num": 3,
        "container": {
            "datalayer": values["datalayer"]["resources"]
        },
        "storage": {}
    },
    {
        "name": "Management",
        "num": 1,
        "container": {
            "init job": values["manager"]["setup"]["resources"],
            "sandbox": values["manager"]["sandbox"]["resources"]
        },
        "storage": {}
    },
    {
        "name": "Nginx",
        "num": values["nginx"]["Replicas"],
        "container": {
            "server": values["nginx"]["resources"]
        },
        "storage": {}
    }]

print("| Service       | Pods | Containers  | CPU<br>request / limit | RAM<br>request / limit | PersistentVolume |")
print("| ------------- | ---- | ----------- |:----------------------:|:----------------------:| ----------------:|")
total = {'requests':{'cpu':0,'memory':0},'limits':{'cpu':0,'memory':0},'storage':0}
for component in comp:
    res = component["container"]
    print("| "+component["name"]+
    " | "+str(component["num"])+
    " | "+"<br>".join(res.keys())+
    " | "+"<br>".join([str(v["requests"]["cpu"])+" / "+str(v["limits"]["cpu"]) for v in res.values()])+
    " | "+"<br>".join([str(v["requests"]["memory"])+" / "+str(v["limits"]["memory"]) for v in res.values()])+
    " | "+"<br>".join([str(k+": "+v) for (k,v) in component["storage"].items()])+
    " | ")
    for l in ('requests','limits'):
        for t in ('cpu','memory'):
            total[l][t] += float(component["num"]) * sum([convert(v[l][t]) for v in res.values()])
    total['storage'] += float(component["num"]) * sum([convert(v) for v in component["storage"].values()])

print("| TOTAL |  | "+
    " | " +str(round(total["requests"]["cpu"],3))+" / "+str(round(total["limits"]["cpu"],3))+ "CPUs"+
    " | " +str(round(total["requests"]["memory"],3))+" / "+str(round(total["limits"]["memory"],3))+ "GB RAM"+
    " | " +str(round(total["storage"],3))+ "GB persistent storage"+
    " | ")
