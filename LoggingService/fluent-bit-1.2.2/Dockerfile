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

# Fluent Bit version
ENV FLB_MAJOR 1
ENV FLB_MINOR 2
ENV FLB_PATCH 2
ENV FLB_VERSION 1.2.2

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
      make \
      wget \
      unzip \
      libssl1.0-dev \
      libasl-dev \
      libsasl2-dev \
      pkg-config \
      libsystemd-dev \
      zlib1g-dev \
      flex \
      bison \
      tar

RUN mkdir -p /fluent-bit/bin /fluent-bit/conf /tmp/src/
COPY ./fluent-bit-1.2.2.tar.gz /tmp/src/fluent-bit-1.2.2.tar.gz
RUN tar -zxvf /tmp/src/fluent-bit-1.2.2.tar.gz -C /tmp/src/
RUN rm -rf /tmp/src/fluent-bit-1.2.2/build/*

WORKDIR /tmp/src/fluent-bit-1.2.2/build/
RUN cmake -DFLB_BINARY=On \
          -DFLB_JEMALLOC=On \
          -DFLB_BUFFERING=On \
          -DFLB_LUAJIT=On \
          -DFLB_BACKTRACE=On \
          -DFLB_TLS=On \
          -DFLB_DEBUG=Off \
          -DFLB_TRACE=Off \
          -DFLB_SHARED_LIB=Off \
          -DFLB_EXAMPLES=Off \
          -DFLB_HTTP_SERVER=Off \
          -DFLB_IN_SYSTEMD=Off \
          -DFLB_OUT_KAFKA=Off ..

RUN make -j $(getconf _NPROCESSORS_ONLN)
RUN install bin/fluent-bit /fluent-bit/bin/

# Configuration files
RUN cd .. && cp conf/fluent-bit.conf \
     conf/parsers.conf \
     conf/plugins.conf \
     /fluent-bit/conf/



# This is image is used for mfn sandboxes
FROM ubuntu:18.04

# These are already included in mfn sandboxes
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      netbase \
      unzip \
      file \
      libmagic1

#COPY --from=builder /usr/lib/x86_64-linux-gnu/*sasl* /usr/lib/x86_64-linux-gnu/
#COPY --from=builder /usr/lib/x86_64-linux-gnu/libz* /usr/lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/libz* /lib/x86_64-linux-gnu/
#COPY --from=builder /usr/lib/x86_64-linux-gnu/libssl.so* /usr/lib/x86_64-linux-gnu/
#COPY --from=builder /usr/lib/x86_64-linux-gnu/libcrypto.so* /usr/lib/x86_64-linux-gnu/
# These below are all needed for systemd
#COPY --from=builder /lib/x86_64-linux-gnu/libsystemd* /lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/libselinux.so* /lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/liblzma.so* /lib/x86_64-linux-gnu/
#COPY --from=builder /usr/lib/x86_64-linux-gnu/liblz4.so* /usr/lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/libgcrypt.so* /lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/libpcre.so* /lib/x86_64-linux-gnu/
#COPY --from=builder /lib/x86_64-linux-gnu/libgpg-error.so* /lib/x86_64-linux-gnu/

# Install additional dependencies needed by fluent-bit
RUN apt-get -y --no-install-recommends install zlib1g libssl1.0 libsasl2-2 ca-certificates

# copy fluent-bit from the builder container
COPY --from=builder /fluent-bit /fluent-bit

# check if all the dependencies can be loaded
RUN ldd /fluent-bit/bin/fluent-bit

RUN chmod -R 777 /fluent-bit

# Entry point
CMD ["/fluent-bit/bin/fluent-bit", "-c", "/fluent-bit/conf/fluent-bit.conf"]
