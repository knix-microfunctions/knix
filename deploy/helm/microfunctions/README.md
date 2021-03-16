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

* Kubernetes 1.18

* Helm 3.5.2

* Knative 0.21

## Chart Details

This chart will do the following:

* Deployment of an Nginx server that serves as storage frontend and hosts the web GUI

* StatefulSet of 3 Riak nodes that serve as global data storage

* Deployment of a standalone Elasticsearch server to collect tracing data

* StatefulSet of caches to serve datalayer access locally

* Start the Management MicroFunctions workflow as a Knative service (created through a job)

## Installing the Chart

Our helm chart by default installs container images from a [private registry](https://github.com/kubernetes-sigs/kubespray/tree/master/roles/kubernetes-apps/registry). To build the components and push images to a private registry at localhost:5000 (use kube forwarder), use the following commands:
```
[user@vm knix]# make -C Sandbox push
[user@vm knix]# make -C ManagementService push
[user@vm knix]# make -C DataLayerService push
[user@vm knix]# make -C riak push
[user@vm knix]# make -C GUI push
[user@vm knix]# make -C TriggersFrontend push
```

The push target in deploy/helm/Makefile can be used to build and push all container images:
```
[user@vm knix]# make -C deploy/helm push
```

The `REGISTRY` environment variable can be used to have make tag and push container images to a custom registry, e.g. `$ REGISTRY=my-registry.com make -C deploy/helm push` or it can be modified in ./docker.mk.

To deploy the Helm chart with a release name `mfn` to the default namespace from the Helm chart sources, use:
```
[user@vm knix]# helm install --name mfn deploy/helm/microfunctions/
```

The deploy target in deploy/helm/Makefile can be used to build and push container images and deploy the Helm package in one step:
```
[user@vm knix]# cd deploy/helm
[user@vm knix]# make deploy
```

* a namespace can be chosen with --namespace my-ns

* the --debug option will provide detailed output of what is being deployed

* The variable `imageRepo` can be set to pull containers from a custom registry, e.g. `--set imageRepo=my-registry.com`

* The variables `httpProxy` and `httpsProxy` can be set to pass proxy environment variables to all workflow sandboxes run by the platform, e.g. `--set httpProxy=http://my-proxy.corporate.com`

* Further variables concerning container resource requests and limits can be overwritten. Please see deploy/helm/microfunctions/values.yaml for more configuration options. 

## Connecting to the web GUI

Nginx is exposed through the Service nx-<deployment name> (e.g. nx-mfn) by default on a NodePort 32180 (optionally, nginx can be configured with an SSL port).
There's no Ingress created by default.

## Choosing a custom container repository

We're not hosting docker containers, so this Helm chart uses `registry.kube-system.svc.cluster.local` as the default container repository. Container images for each of the components are built and pushed individually and can be created globally from the source root:

```
[user@vm knix]# docker login my-registry.com
[user@vm knix]# REGISTRY=my-registry.com make push
[user@vm knix]# helm install --name mfn --set imageRepo=myregistry.com deploy/helm/MicroFunctions.tgz
```

## Resource requirements

| Component          | Pods | Containers        | CPU<br>request / limit | RAM<br>request / limit | PersistentVolume       |
| ------------------ | ---- | ----------------- |:----------------------:|:----------------------:| ----------------------:|
| Deployment nx-mfn  |    1 | nginx             |    0.1 /   0.5         |    1.0 /   1.0         |    0.0 /   0.0         | 
| Deployment tf-mfn  |    3 | triggers-frontend |    6.0 /  12.0         |    3.0 /  24.0         |    0.0 /   0.0         | 
| StatefulSet dl-mfn |    3 | datalayer         |   12.0 /  12.0         |   24.0 /  24.0         |    0.0 /   0.0         | 
| StatefulSet es-mfn |    1 | elasticsearch     |    2.0 /   4.0         |    2.0 /   4.0         |    0.0 /   0.0         | 
| StatefulSet rk-mfn |    3 | riak              |   12.0 /  12.0         |   24.0 /  24.0         |    0.0 /   0.0         | 
| Deployment wf-management  |    1 | sandbox             |    2 /   4         |    2.0 /   4.0         |    0.0 /   0.0         | 
| Workflows  |    1 | sandbox             |    1 /   1         |    1.0 /   2.0         |    0.0 /   0.0         | 
disk |

Resource requirements can be edited modifying the respective `resources` requests and limits in the Helm chart values:
 - `manager.setup.resources` controls the job that runs only once to start our management service as a KNIX workflow
 - `manager.managementSandbox.resources` configures the size of the management service's sandboxes
 - `manager.sandbox.resources` sets the default resources used with every workflow sandbox that is being deployed
 - `datalayer.resources`, `riak.resources`, `nginx.resources` and `triggersFrontend.resources` sets the resource request limits of those components, respectively

To resize the __riak__ deployment, it's also crucial to adapt the Riak JVM and cache memory settings. Pay attention to these settings when resizing Riak pods:
``` yaml
riak:
  # Has to fit in the memory configuration alongside Riak (default setting claims half the pod memory)
  LevelDbMaximumMemory: 4294967296
  AntiEntropy: "passive"
  # Should be <= resources.limits.cpu
  ErlangSchedulersTotal: 4
  ErlangSchedulersOnline: 4
``` 