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
UID:=`id -u`
GID:=`id -g`

default: build_thrift \
	management_deployment_package.tar.gz

build_thrift:
	cd ../build_tools/thrift/$(THRIFT_VERSION)/; ./build_thrift.sh; cd -

DataLayerClient.py: ../FunctionWorker/python/DataLayerClient.py
	cp $< $@

THRIFT=$(-shell find data_layer/ -type f -size +1c) data_layer

thrift: $(THRIFT)

$(THRIFT): ../DataLayerService/thrift/DataLayerMessage.thrift ../DataLayerService/thrift/DataLayerService.thrift ../build_env.mk
	mkdir -p data_layer
	docker run --user $(UID):$(GID) --rm -v $(CURDIR)/..:/root -w /root $(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) bash -c '\
		thrift --gen py -out ManagementService/ DataLayerService/thrift/DataLayerMessage.thrift; \
		thrift --gen py -out ManagementService/ DataLayerService/thrift/DataLayerService.thrift'

SOURCES=$(shell find python/ -type f) $(shell ls *.py *.json)

management_deployment_package.tar.gz: $(SOURCES) DataLayerClient.py $(THRIFT)
	mkdir -p build/
	for FILE in $^; do \
		mkdir -p build/$$(dirname $$FILE); \
		cp -af $$FILE build/$$FILE; \
	done
	sed 's/_VERSION_STRING =.*/_VERSION_STRING = "$(shell git describe --long --tags --dirty --always)"/' -i build/python/ManagementServiceEntry.py
	rm -rf $@
	tar -czf $@ -C build/ .
	rm -rf build/

include ../docker.mk

image: \
	Dockerfile \
	management_deployment_package.tar.gz
	$(call build_image,Dockerfile,microfn/management)

push: image
	$(call push_image,microfn/management)

test: image
	docker run -it --rm --name management \
		--env MFN_DATALAYER=192.168.137.111:4998 \
		--env MFN_HOSTNAME=$(shell hostname) \
		--env MFN_ELASTICSEARCH_CONNECT=$(shell hostname):9200 \
		--env HTTP_PROXY=$(HTTP_PROXY) \
		--env HTTPS_PROXY=$(HTTPS_PROXY) \
		--env http_proxy=$(HTTP_PROXY) \
		--env https_proxy=$(HTTPS_PROXY) \
		--net host \
		microfn/management

print: image
	docker run -it --rm --name management \
		--env MFN_DATALAYER=192.168.137.111:4998 \
		--env MFN_HOSTNAME=$(shell hostname) \
		--env MFN_ELASTICSEARCH_CONNECT=$(shell hostname):9200 \
		--env HTTP_PROXY=$(HTTP_PROXY) \
		--env HTTPS_PROXY=$(HTTPS_PROXY) \
		--env http_proxy=$(HTTP_PROXY) \
		--env https_proxy=$(HTTPS_PROXY) \
		--net host \
		microfn/management python3 /opt/mfn/ManagementService/management_init.py print
