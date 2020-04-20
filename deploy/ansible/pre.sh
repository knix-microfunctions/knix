#!/bin/sh
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


# This file is to be run target machine in case appropriate pre-reqs are not installed, such as python, python-dev.

# 1. Set appropriate proxies (/etc/profile, /etc/bash.bashrc, and /etc/apt/apt.conf)

# 2a. Install docker-ce:
#   https://docs.docker.com/install/linux/docker-ce/ubuntu/
#   https://docs.docker.com/install/linux/docker-ce/debian/
# 2b. Enable sudo-less access to docker commands - add remote user to the docker group
#   e.g.  sudo usermod -a -G docker paditya
# 2c. Set docker proxies
#   /etc/systemd/system/docker.service.d/http-proxy.conf

# 3. Install python, python-dev, and python-pip
sudo apt-get update
sudo apt-get install python3 python3-dev python3-pip

# 4. Install ansible on host machine
#    https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html
