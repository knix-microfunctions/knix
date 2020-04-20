# Overview

**KNIX MicroFunctions** is an open source serverless computing platform for Knative as well as bare metal or virtual machine-based environments.
It combines container-based resource isolation with a light-weight process-based execution model that significantly improves resource efficiency and decreases the function startup overhead.


Compared with existing serverless computing platforms, **KNIX MicroFunctions** has the following advantages:

* Low function startup latency & high resource efficiency
* Fast locality-aware storage access
* Python and Java function runtimes
* Workflow support and compatibility with Amazon States Language (ASL)
* Support for long-running functions for continuous data processing applications
* Powerful web UI, SDK and CLI for effective serverless application development

# Screenshots

![](GUI/app/pages/docs/intro/mfn.gif?raw=true)

![](GUI/app/pages/docs/intro/wf_exec.gif?raw=true)   


# Installation

This section covers installing KNIX.

### Installing KNIX MicroFunctions on Kubernetes

To install KNIX, you’ll need a running Kubernetes cluster with Knative and root privileges to install KNIX into its own namespace. In particular, KNIX has been tested with the following:

* [Kubernetes:](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) version 1.17.5 with storage class for persistent volume claims
* [Helm:](https://github.com/kubernetes/helm) version 3.1.2
* [Knative:](https://knative.dev) version 0.13.0

KNIX can be installed using helm charts. Assuming you have a Kubernetes cluster and Knative running, simply run the following command:

```bash
# Install KNIX
# This assumes that you do not have a KNIX deployment yet.
helm install --name mfn1 <helm-chart-url>
```
To remove the deployment named mfn1:

```bash
helm delete --purge mfn1
```
A namespace can be chosen with --namespace my-ns. The --debug option will provide detailed output of what is being deployed.

### Installing KNIX MicroFunctions on Bare Metal or Virtual Machines

KNIX MicroFunctions can also be installed using Ansible playbooks on bare metal or virtual machines. You'll need a user with sudo access.

Please refer to the installation [README](https://github.com/knix-microfunctions/knix/blob/master/deploy/ansible/README.md).

### Connecting to the KNIX web GUI to create functions and workflows
Nginx is exposed through the Service nx- (e.g. nx-mfn-test) by default on port 20080 (optionally, nginx can be configured with an SSL port).
There's no default Ingress created.



# Hosted Service

Nokia Bell Labs provides a hosted service for hands-on experimentation with the **KNIX MicroFunctions** platform. Please find more details at [https://bell-labs.com/knix](https://bell-labs.com/knix).

# Getting Involved

We encourage you to participate in this open source project. We welcome pull requests, bug reports, ideas, code reviews, or any kind of positive contribution.

Before you attempt to make a contribution please read the [Code of Conduct](https://github.com/knix-microfunctions/knix/CODE_OF_CONDUCT.md).

* [View current Issues](https://github.com/knix-microfunctions/knix/issues) or [view current Pull Requests](https://github.com/knix-microfunctions/knix/pulls).

* Join our Slack workspace [https://knix.slack.com](https://join.slack.com/t/knix/shared_invite/zt-dm7agzna-8~cVsYqAMKenxFhFDARjvw)

* Subscribe to our developer mailing list 'knix-dev@list.nokia.com': Please [send an email](mailto:listserv@list.nokia.com) to listserv@list.nokia.com with 'subscribe knix-dev FirstName LastName' in the message body.

# License

[Apache License 2.0](https://github.com/knix-microfunctions/knix/blob/master/LICENSE)

