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

# KNIX ansible installation

Setup KNIX on localhost, or a single remote host, or a cluster of hosts.
Tested on the following operating systems on the target machines: 
- Ubuntu 16.04, 18.04, 20.04
- Xubuntu 18.04, 20.04
- Debian 9

## Prerequisites: on host machine

1. Install ansible on host machine

    <https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html>

2. Install dependencies required by ansible

    ```bash
    # for python2
    sudo pip install netaddr
    ```
or:

    ```bash
    # for python3
    sudo pip3 install netaddr
    ```

## Prerequisites: on target machines

1. You can ssh into the target machines/VMs without a password. If not then run (on host machine):

    ```bash
    ssh-keygen
    ssh-copy-id -i ~/.ssh/id_rsa your-username@your-target-hostname
    ```

2. The login user (in step 1) on the target machines has been added to the sudoer group

3. Appropriate proxies (/etc/profile, /etc/bash.bashrc, and /etc/apt/apt.conf) are set on target machines

4. `python3`, `python3-dev`, `python3-pip` are installed on each of the target machines

    ```bash
    sudo apt-get update
    sudo apt-get install python3 python3-dev python3-pip
    ```

5. docker-ce is installed on target machines

    * Install docker-ce:
    <https://docs.docker.com/install/linux/docker-ce/ubuntu/>
    <https://docs.docker.com/install/linux/docker-ce/debian/>

    * Enable sudo-less access to docker commands - add remote user to the docker group

        ```bash
        sudo usermod -a -G docker your-username
        #newgrp docker (if you don't want to log out and in to activate the change to group)
        ```

    * Set docker proxies by updating `/etc/systemd/system/docker.service.d/http-proxy.conf`

6. Hostname of the target machine resolves to the correct IP.

7. Remove any old installation of KNIX

    ```bash
    cd /opt/knix
    ./stop-all.sh
    ./purge-riak.sh
    cd ..
    sudo rm -rf knix
    ```

*Note: If you find something wrong or missing, please consider opening an issue on [GitHub](https://github.com/knix-microfunctions/knix) and/or letting us know in our [Slack workspace](https://knix.slack.com). Thank you!*


## Installation Steps (to be executed on host machine)

1. Create an `ansible.cfg` file

    ``` bash
    mv ansible.cfg.sample ansible.cfg
    ```

2. Create an `inventory.cfg`

    ```bash
    mv inventory.cfg.sample inventory.cfg
    ```

    * For a localhost setup

        ```bash
        ./local_inventory.sh
        ```

    * For a remote host setup (single host or cluster)

        ```bash
        vi inventory.cfg

        # For a single remote host installation, the hostname should be added to all groups.

        # For a cluster of hosts (preferably 3 or more), all host names must be added to [riak] group.
        #  Hosts with a NVIDIA GPU should be added to group [gpu_workstations] so that they can be used by KNIX workflow deployments.
        #  Only one host name (referred to as the <nginx-hostname>) should be added for other groups [elasticsearch], [management], [triggers_frontend], and [nginx].
        ```

3. Update `settings.json`
    * `mfn_server_installation_folder`: folder where KNIX will be installed
    * `start_at_boot`: whether KNIX services should be started at system start up
    * `riak_leveldb_maximum_memory`: total memory (in bytes) assigned to each Riak storage node's LevelDB backend
    * `nginx_http_listen_port`: http port the ngix server, serving the KNIX GUI, will listen on
    * `nginx_https_listen_port`: https port the ngix server, serving the KNIX GUI, will listen on
    * `management_service_exposed_port`: http port management service of KNIX will listen on

4. Checks connectivity to target machines and collects & cache facts about the remote machines

    ```bash
    ansible all -m setup
    ```

5. Run the installation script: (it will ask for SUDO password on the target machine)

    ```bash
    make
    ```

6. After installation, open a browser and access `http://<nginx-hostname>:<nginx_http_listen_port>/`
