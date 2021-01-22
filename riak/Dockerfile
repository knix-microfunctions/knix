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

FROM centos:centos8 as builder

ENV CENTOS_FRONTEND=noninteractive

RUN dnf install -y http://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm

RUN dnf update -y && dnf group install -y "Development Tools"

RUN dnf install -y \

#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#      build-essential \
      epel-release \
      cmake \
      make \
      wget \
      unzip \
#      libssl1.0.0 \
#      libssl1.0-dev \ 
      openssl \
      openssl-devel \
      cyrus-sasl-lib \
#      libasl-dev \
#      libsasl2-dev \
#      pkg-config \
#      libsystemd-dev \
      zlib-devel \
#      zlib1g-dev \
      flex \
      bison \
      tar \
      mtools \
      git \
      ca-certificates \
      automake \
      autoconf \
      ncurses-devel gcc gcc-c++ glibc-devel make ncurses-devel openssl-devel autoconf java-1.8.0-openjdk-devel git wget  pam-devel perl-Digest-SHA erlang

#RUN set -ex && \
#    mkdir -p /usr/local/bin && \
#    cd /usr/local/bin && \
#    wget --no-check-certificate https://raw.githubusercontent.com/kerl/kerl/master/kerl && \
#    chmod a+x kerl && \
#    mkdir /build && \
#    cd /build

#RUN set -ex && \
#    cd /build && \
#    #ls -l && \
#    #cd OTP_R16B02_basho10 && \
#    #./otp_build autoconf && \
#    #./configure && make && sudo make install && \
#    export KERL_CONFIGURE_OPTIONS="--with-ssl=/usr/include/openssl" && \
#    kerl build git https://github.com/basho/otp.git OTP_R16B02_basho10 R16B02-basho10 && \
#    kerl install R16B02-basho10 /build/erlang/R16B02-basho10 && \
#    . /build/erlang/R16B02-basho10/activate

RUN set -ex && \
#    . /build/erlang/R16B02-basho10/activate && \
    mkdir /build && \
    cd /build && \
    git clone https://github.com/davisp/jiffy.git && \
    cd jiffy && \
    ./rebar compile && \
    cd .. && \
    chmod -R 777 jiffy && \
    tar --exclude .git -cvzf jiffy.tgz jiffy && \
    chmod 777 jiffy.tgz 
