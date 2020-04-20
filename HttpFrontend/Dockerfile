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

FROM openjdk:8-jdk-stretch

RUN apt-get update
RUN apt-get -y --no-install-recommends install apt-utils dstat vim \
	telnet net-tools grep sudo bmon netcat tcpdump

RUN groupadd -o -g 101 -r mfn && useradd -b /opt -d /opt/mfn -u 101 -m -r -g mfn mfn
USER mfn

RUN mkdir -p /opt/mfn/frontend/logs
COPY target/frontend.jar /opt/mfn/frontend/
WORKDIR /opt/mfn/frontend

CMD ["java","-jar","frontend.jar"]
