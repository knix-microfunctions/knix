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
# Overview

The **KNIX MicroFunctions** platform can also be installed using Ansible.

* pre.sh: basic pre-requisites for the machines, where KNIX MicroFunctions is going to be installed

* Makefile: single file to run all necessary steps for the installation

* run.sh: script to install a single component with the corresponding .yaml file

* *.yaml: Ansible playbooks for respective components

* local_inventory.sh: set up the inventory file to use the current local machine (useful for development purposes)

* Ansible.cfg.sample, inventory.cfg.sample: sample Ansible configuration and inventory files (modify according to your needs)

* settings.json: configuration file for the Ansible installation with the following default values:

  - "mfn_server_installation_folder": "/opt/mfn"
  - "nginx_http_listen_port": "80"
  - "nginx_https_listen_port": "443"
  - "set_http_proxy": "false"
  - "management_service_exposed_port": "8082"
