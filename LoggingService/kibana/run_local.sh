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

set -ex
# set the following kibana settings via evn variables
# elasticsearch.hosts: [ "http://elasticsearch:9200" ]
# elasticsearch.username: elastic
# elasticsearch.password: changeme

cat <<END >> .env
HTTP_PROXY=$HTTP_PROXY
HTTPS_PROXY=$HTTPS_PROXY
FTP_PROXY=$FTP_PROXY
http_proxy=$http_proxy
https_proxy=$https_proxy
ftp_proxy=$ftp_proxy
no_proxy=$no_proxy
NO_PROXY=$NO_PROXY
ELASTICSEARCH_HOSTS=http://$(hostname):9200
END

docker run -i --rm --name kibana --env-file .env -p 5601:5601 --add-host=$(hostname):$(hostname -i) docker.elastic.co/kibana/kibana:7.2.0 $1