# Important Disclaimer

**KNIX** started as a research project at Nokia Bell Labs and was open-sourced afterwards.
In the meantime, the serverless landscape has drastically changed and improved.
We try to maintain the codebase and provide support with issues; however, our research priorities and focus have since changed, limiting our time devoted to the maintenance of the repo.
Please be aware of this situation.

# Overview

![](logo/KNIX_logo_horizontal.jpg)

**KNIX MicroFunctions** is an open source serverless computing platform for Knative as well as bare metal or virtual machine-based environments.
It combines container-based resource isolation with a light-weight process-based execution model that significantly improves resource efficiency and decreases the function startup overhead.


Compared with existing serverless computing platforms, **KNIX MicroFunctions** has the following advantages:

* Low function startup latency & high resource efficiency
* Fast locality-aware storage access
* Python and Java function runtimes
* Workflow support and compatibility with [Amazon States Language (ASL)](https://states-language.net/spec.html)
* Support for long-running functions for continuous data processing applications
* Powerful web UI, SDK and CLI for effective serverless application development

# Screenshots

![](GUI/app/pages/docs/intro/mfn.gif?raw=true)

![](GUI/app/pages/docs/intro/wf_exec.gif?raw=true)


# Installation

This section covers installing KNIX.

### Installing KNIX MicroFunctions on Kubernetes

KNIX can be installed using helm charts, assuming you have a Kubernetes cluster and Knative running.

Please refer to the Helm package deployment [README](deploy/helm/microfunctions/README.md).

### Installing KNIX MicroFunctions on Bare Metal or Virtual Machines

KNIX MicroFunctions can also be installed using Ansible playbooks on bare metal or virtual machines. You'll need a user with sudo access.

Please refer to the installation [README](deploy/ansible/README.md).

# Hosted Service

More info on hosted services for hands-on experimentation with the **KNIX MicroFunctions** platform can be found at: [https://knix.io](https://knix.io).

# Getting Involved

We encourage you to participate in this open source project. We welcome pull requests, bug reports, ideas, code reviews, or any kind of positive contribution.

Before you attempt to make a contribution please read the [Code of Conduct](./CODE_OF_CONDUCT.md).

* [View current Issues](https://github.com/knix-microfunctions/knix/issues) or [view current Pull Requests](https://github.com/knix-microfunctions/knix/pulls).

* Join our Slack workspace [https://knix.slack.com](https://join.slack.com/t/knix/shared_invite/zt-dm7agzna-8~cVsYqAMKenxFhFDARjvw) which has 'users' and 'dev' channels.

* (Optionally) subscribe to [knix-users mailing list](https://groups.google.com/forum/#!forum/knix-users) and/or [knix-dev mailing list](https://groups.google.com/forum/#!forum/knix-dev).

# License

[Apache License 2.0](https://github.com/knix-microfunctions/knix/blob/master/LICENSE)

