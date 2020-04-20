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

FROM ubuntu:18.04 as builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
      make \
      wget \
      unzip \
      libssl1.0.0 \
      libssl1.0-dev \ 
      libasl-dev \
      libsasl2-dev \
      pkg-config \
      libsystemd-dev \
      zlib1g-dev \
      flex \
      bison \
      tar \
      mtools \
      git \
      ca-certificates \
      automake \
      autoconf \
      libncurses5-dev

RUN set -ex && \
    mkdir -p /usr/local/bin && \
    cd /usr/local/bin && \
    wget --no-check-certificate https://raw.githubusercontent.com/kerl/kerl/master/kerl && \
    chmod a+x kerl && \
    mkdir /build && \
    cd /build

RUN set -ex && \
    cd /build && \
    kerl build git https://github.com/basho/otp.git OTP_R16B02_basho10 R16B02-basho10 && \
    kerl install R16B02-basho10 /build/erlang/R16B02-basho10 && \
    . /build/erlang/R16B02-basho10/activate

RUN set -ex && \
    . /build/erlang/R16B02-basho10/activate && \
    cd /build && \
    git clone https://github.com/davisp/jiffy.git && \
    cd jiffy && \
    ./rebar compile && \
    cd .. && \
    chmod -R 777 jiffy && \
    tar --exclude .git -cvzf jiffy.tgz jiffy && \
    chmod 777 jiffy.tgz
