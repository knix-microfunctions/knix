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

# Install (as root)
# Base
RUN apt-get update --fix-missing
RUN apt-get -y --no-install-recommends install build-essential
RUN apt-get -y --no-install-recommends install netbase unzip file libmagic1

# Python
RUN apt-get -y --no-install-recommends install python3 python3-dev
RUN apt-get -y --no-install-recommends install python3-pip
RUN apt-get -y --no-install-recommends install zlib1g libssl1.0 libsasl2-2 ca-certificates

RUN /usr/bin/python3 -m pip install --upgrade pip

RUN /usr/bin/python3 -m pip install setuptools
RUN /usr/bin/python3 -m pip install thrift>=0.12.0
RUN /usr/bin/python3 -m pip install anytree
RUN /usr/bin/python3 -m pip install ujsonpath
RUN /usr/bin/python3 -m pip install requests
RUN /usr/bin/python3 -m pip install retry
# remove warnings from anytree package
RUN /usr/bin/python3 -m pip install fastcache
# Needed for multi-language support (currently just Java)
RUN /usr/bin/python3 -m pip install thriftpy2

# Add components (as mfn)
RUN groupadd -o -g 1000 -r mfn && useradd -d /opt/mfn -u 1000 -m -r -g mfn mfn
RUN mkdir /opt/mfn/logs

RUN /usr/bin/python3 -m pip install redis
ADD build/redis-server.tar.gz /opt/mfn/
ADD frontend/frontend /opt/mfn/frontend
ADD build/SandboxAgent.tar.gz /opt/mfn/
ADD build/FunctionWorker.tar.gz /opt/mfn/
ADD build/LoggingService.tar.gz /opt/mfn/

RUN chown mfn:mfn -R /opt/mfn
USER mfn
WORKDIR /opt/mfn
CMD ["python3", "/opt/mfn/SandboxAgent/sandboxagent.py"]
