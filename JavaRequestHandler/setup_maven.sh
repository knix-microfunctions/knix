#!/bin/bash
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

SHOULD_MV_INIT=$1

cd /opt/mfn/JavaRequestHandler
mkdir -p maven/repository

cp sandbox-mvn-settings_original.xml $@.tmp
sandbox_http_proxy=${http_proxy:-${HTTP_PROXY}}
sandbox_https_proxy=${https_proxy:-${HTTPS_PROXY}}
sandbox_noproxy=$(echo $no_proxy|sed 's/,/|/g')

if [ "$http_proxy" != "" ];
then
    proto=${http_proxy%://*}
    port=${http_proxy##*:}
    port=${port%/*}
    host=${http_proxy#*://}
    host=${host%:*}
    sed "s#<proxy><id>http</id>.*#<proxy><id>http</id><active>true</active><protocol>$proto</protocol><host>$host</host><port>${port:-80}</port><nonProxyHosts>$sandbox_noproxy</nonProxyHosts></proxy>#" -i $@.tmp
else
    sed "s#<proxy><id>http</id>.*##" -i $@.tmp
fi

if [ "$https_proxy" != "" ];
then
    proto=${https_proxy%://*}
    port=${https_proxy##*:}
    port=${port%/*}
    host=${https_proxy#*://}
    host=${host%:*}
    sed "s#<proxy><id>https</id>.*#<proxy><id>https</id><active>true</active><protocol>$proto</protocol><host>$host</host><port>${port:-80}</port><nonProxyHosts>$sandbox_noproxy</nonProxyHosts></proxy>#" -i $@.tmp
else
    sed "s#<proxy><id>https</id>.*##" -i $@.tmp
fi

mv $@.tmp maven/sandbox-mvn-settings.xml

if [ "$SHOULD_MV_INIT" == "True" ]
then
    mv init-mvn.pom.xml maven/init-mvn.pom.xml
fi

cd ..
