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
rm -rf fluent-bit
if [ -f ./fluent-bit-1.2.2.tar.gz ]
then
    echo "using existing fluent-bit-1.2.2.tar.gz"
else
    echo "Downloading fluent-bit-1.2.2.tar.gz"
    wget -N --no-check-certificate https://fluentbit.io/releases/1.2/fluent-bit-1.2.2.tar.gz
fi
docker build --build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy -t fluent-bit-1.2.2-build .
docker run -i --rm --name fluent-bit-1.2.2-sandbox -v $(pwd):/fluent-bit-build fluent-bit-1.2.2-build /bin/bash -c "cp -r /fluent-bit /fluent-bit-build/. && chmod -R 777 /fluent-bit-build/fluent-bit" 
./package-fluent-bit.sh
