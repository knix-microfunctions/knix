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

FROM ubuntu:18.04
RUN apt-get update
RUN apt-get update --fix-missing

RUN apt-get -y --no-install-recommends install build-essential
RUN apt-get -y --no-install-recommends install netbase unzip file libmagic1
#RUN apt-get -y --no-install-recommends install netcat

RUN apt-get -y --no-install-recommends install python3 python3-dev
RUN apt-get -y --no-install-recommends install python3-pip

RUN /usr/bin/python3 -m pip install --upgrade pip

RUN /usr/bin/python3 -m pip install setuptools
RUN /usr/bin/python3 -m pip install thrift==0.11.0
RUN /usr/bin/python3 -m pip install anytree
RUN /usr/bin/python3 -m pip install ujsonpath
RUN /usr/bin/python3 -m pip install requests
RUN /usr/bin/python3 -m pip install retry
RUN /usr/bin/python3 -m pip install docker

RUN groupadd -o -g 1000 -r mfn && useradd -b /opt -d /opt/mfn -u 1000 -m -r -g mfn mfn
ADD management_deployment_package.tar.gz /opt/mfn/ManagementService/
RUN chown mfn:mfn -R /opt/mfn/ManagementService/
USER mfn

WORKDIR /opt/mfn/ManagementService
CMD ["python3", "/opt/mfn/ManagementService/management_init.py", "start"]

