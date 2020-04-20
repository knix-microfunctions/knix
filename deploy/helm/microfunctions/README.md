<!--
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->
# MicroFunctions Helm Chart

## Tested with:

* Kubernetes 1.17.5

* Helm 3.1.2

* Knative 0.13.0

## Chart Details

This chart will do the following:

* Deployment of an Nginx server that serves as storage frontend and hosts the web GUI

* StatefulSet of 3 Riak nodes that serve as global data storage

* Deployment of a standalone Elasticsearch server to collect tracing data

* StatefulSet of caches to serve datalayer access locally

* Start the Management MicroFunctions workflow as a Knative service (created through a job)

## Installing the Chart

To install the chart with the release name `mfn1` in the default namespace:

```
$ helm install --name mfn1 https://github.com/knix-microfunctions/knix/releases/download/0.8.0/MicroFunctions-0.8.0.tgz
```

To remove the deployment named mfn1:

```
$ helm delete --purge mfn1
```

* a namespace can be chosen with --namespace my-ns

* the --debug option will provide detailed output of what is being deployed

## Connecting to the web GUI

Nginx is exposed through the Service nx-<release name> (e.g. nx-mfn1-test) by default on port 20080 (optionally, nginx can be configured with an SSL port).
There's no default Ingress created.

## Resource requirements

| Service       | Pods | Containers  | CPU<br>request / limit | RAM<br>request / limit | PersistentVolume |
| ------------- | ---- | ----------- |:----------------------:|:----------------------:| ----------------:|
| Riak | 3 | server | 1 / 1 | 1Gi / 2Gi |  | 
| Elasticsearch | 1 | server | 100m / 500m | 2Gi / 2Gi |  | 
| Datalayer | 3 | datalayer | 100m / 500m | 200Mi / 500Mi |  | 
| Management | 1 | init job<br>sandbox | 100m / 200m<br>1 / 1 | 1Gi / 1Gi<br>1Gi / 2Gi |  | 
| Nginx | 1 | server<br>frontend | 100m / 500m<br>100m / 500m | 1Gi / 1Gi<br>1Gi / 1Gi |  | 
| TOTAL |  |  | 4.7 / 7.2CPUs | 9.6 / 14.5GB RAM | 0.0GB persistent storage | 