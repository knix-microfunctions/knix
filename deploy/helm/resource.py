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
import subprocess

def find(node,obj):
    if isinstance(node,dict):
        for k in node:
            n = node.get(k)
            if k == obj:
                yield n
            else:
                for res in find(n,obj):
                    yield res
    elif isinstance(node, list):
        for n in node:
            for res in find(n,obj):
                yield res

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

docs = yaml.load_all(subprocess.check_output(["helm","template","mfn","microfunctions/"]))

total = {
    "pods": 0,
    "requests": {
        "cpu": 0,
        "memory": 0,
        "storage": 0
    },
    "limits": {
        "cpu": 0,
        "memory": 0,
        "storage": 0
    }
}
components = []
for doc in docs:
    if doc is None:
        continue
    if doc["kind"] == "Job":
        continue
    name = doc["kind"] + " " + doc["metadata"]["name"]
    comp = {}
    comp['name'] = name

    for l in ('requests','limits'):
        comp[l] = {}
        for t in ('cpu','memory','storage'):
            comp[l][t] = 0.0

    repl = next(find(doc,"replicas"),1)
    comp['replicas'] = repl

    comp['containers'] = []
    for ctrs in find(doc,"containers"):
        for ctr in ctrs:
            comp['containers'].append(ctr['name'])
            if not "resources" in ctr:
                continue
            r=ctr['resources']
            for l in ('requests','limits'):
                if not l in r: continue
                for t in ('cpu','memory','storage'):
                    if not t in r[l]: continue
                    res = repl * convert(r[l][t])
                    comp[l][t] += res

    if len(comp['containers']) > 0:
        components.append(comp)
        total['pods']+=comp['replicas']
        for l in ('requests','limits'):
            if not l in comp: continue
            for t in ('cpu','memory','storage'):
                if not t in comp[l]: continue
                total[l][t] += comp[l][t]

print("| Component          | Pods | Containers        | CPU<br>request / limit | RAM<br>request / limit | PersistentVolume       |")
print("| ------------------ | ---- | ----------------- |:----------------------:|:----------------------:| ----------------------:|")
for comp in components:
    line = "| %-18s |" % comp['name']
    line += " %4d | " % comp['replicas']
    line += "%-17s" % "<br>".join(comp['containers'])+" | "
    for t in ('cpu','memory','storage'):
        line += " %5.1f / %5.1f         | " % (comp['requests'][t], comp['limits'][t])
    print(line)

line = "| TOTAL              | %4d |                   |" % total['pods']
line += "  %5.1f / %5.1f CPUs    |  %5.1f / %5.1f GB RAM  |  %5.1f / %5.1f GB disk |" % tuple([total[l][t] for t in ('cpu','memory','storage') for l in ('requests','limits')])
print(line)
