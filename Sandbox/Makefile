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

# Makefile
SHELL := /bin/bash
-include ../proxy.mk
include ../build_env.mk
.PHONY: build

default: build_thrift \
	image \
	image_java

clean:
	make -C frontend clean
	rm -rf build/*

build_thrift:
	cd ../build_tools/thrift/$(THRIFT_VERSION)/; ./build_thrift.sh; cd -

##############################
## Build

frontend/frontend: $(shell find frontend/ -type f)
	make -C frontend

SBASOURCE = $(shell find ../SandboxAgent)
build/SandboxAgent.tar.gz: $(SBASOURCE)
	mkdir -p build
	tar -czf $@ ../SandboxAgent

FWSOURCE = $(shell find ../FunctionWorker)
build/FunctionWorker.tar.gz: $(FWSOURCE) ../build_env.mk
	mkdir -p build
	docker run --user $$(id -u):$$(id -g) --rm -v $$(pwd)/../:/root -w /root $(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) bash -c '\
		thrift --gen py -out FunctionWorker/python/ DataLayerService/thrift/DataLayerMessage.thrift; \
		thrift --gen py -out FunctionWorker/python/ DataLayerService/thrift/DataLayerService.thrift; \
		thrift --gen py -out FunctionWorker/python/ QueueService/thrift/LocalQueueService.thrift;'
	tar -czf $@ ../FunctionWorker

QSOURCE = $(shell find ../QueueService/src)
build/queueservice.jar: $(QSOURCE) ../build_env.mk
	mkdir -p build
	cd ../QueueService; make; cd -
	cp ../QueueService/target/queueservice.jar build/

LSOURCE = $(shell find ../LoggingService/fluent-bit-1.2.2)
build/LoggingService.tar.gz: $(LSOURCE)
	mkdir -p build
	cd ../LoggingService && make && cd -
	tar -czf $@ -C ../ LoggingService/fluent-bit

JRHSOURCE = $(shell find ../JavaRequestHandler/src)
build/JavaRequestHandler.tar.gz: $(JRHSOURCE) $(wildcard ../JavaRequestHandler/*.xml) ../build_env.mk
	mkdir -p build
	rm -f $@
	cd ../JavaRequestHandler; make all; cd -
	tar -cf build/JavaRequestHandler.tar -C ../ JavaRequestHandler/target/javaworker.jar
	tar -rf build/JavaRequestHandler.tar -C ../ JavaRequestHandler/mfnapi.jar
	tar -rf build/JavaRequestHandler.tar -C ../ JavaRequestHandler/setup_maven.sh
	tar -rf build/JavaRequestHandler.tar -C ../ JavaRequestHandler/sandbox-mvn-settings_original.xml
	tar -rf build/JavaRequestHandler.tar -C ../ JavaRequestHandler/init-mvn.pom.xml
	gzip -f build/JavaRequestHandler.tar

build: build/queueservice.jar \
	frontend/frontend \
	build/LoggingService.tar.gz \
	build/JavaRequestHandler.tar.gz \
	build/FunctionWorker.tar.gz \
	build/SandboxAgent.tar.gz

include ../docker.mk

image: \
	Dockerfile \
	build/queueservice.jar \
	frontend/frontend \
	build/LoggingService.tar.gz \
	build/FunctionWorker.tar.gz \
	build/SandboxAgent.tar.gz
	$(call build_image,Dockerfile,microfn/sandbox)

image_java: \
	Dockerfile_java \
	build/queueservice.jar \
	frontend/frontend \
	build/LoggingService.tar.gz \
	build/JavaRequestHandler.tar.gz \
	build/FunctionWorker.tar.gz \
	build/SandboxAgent.tar.gz
	$(call build_image,Dockerfile_java,microfn/sandbox_java)

push: image image_java
	$(call push_image,microfn/sandbox)
	$(call push_image,microfn/sandbox_java)


##############################
## Testing
test: image
	docker run -it --rm --name frontend \
		--env MFN_DATALAYER=192.168.137.111:4998 \
		--env MFN_HOSTNAME=$(shell hostname) \
		--env MFN_ELASTICSEARCH_CONNECT=$(shell hostname):9200 \
		--env USERID=admin@management \
		--env SANDBOXID=Management \
		--env WORKFLOWID=Management \
		--env PORT=33333 \
		--env HTTP_PROXY=$(HTTP_PROXY) \
		--env HTTPS_PROXY=$(HTTPS_PROXY) \
		--env http_proxy=$(HTTP_PROXY) \
		--env https_proxy=$(HTTPS_PROXY) \
		--net host \
		microfn/sandbox
	#sleep 1
	#curl --data '{"foo":"bar","mybool":true,"mynum":5.5}' http://127.0.0.1:33333/
	#docker stop frontend
	#docker rm frontend
