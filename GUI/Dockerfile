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

FROM docker.io/nginx

RUN apt-get update
RUN apt-get -y --no-install-recommends install vim curl iputils-ping telnet unzip tcpdump

# Configure running container as user nginx
RUN sed -i 's/\(^user.*\)/# \1 - container already runs as user nginx/' /etc/nginx/nginx.conf
RUN sed -i 's/pid.*/pid        \/opt\/mfn\/nginx\/nginx.pid;/' /etc/nginx/nginx.conf
RUN chown nginx:nginx /var/cache/nginx

RUN mkdir -p /opt/mfn/nginx; chown nginx:nginx /opt/mfn/nginx
USER nginx
WORKDIR /opt/mfn/nginx
RUN mkdir /opt/mfn/nginx/logs
ADD . /opt/mfn/nginx/gui

# run nginx proxy and the SAND gui
CMD ["nginx", "-g", "daemon off;"]


