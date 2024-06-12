#   Copyright 2021 The KNIX Authors
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

SELF_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
VERSION ?= $(shell git -C $(SELF_DIR) describe --tags --dirty)
PKG=MicroFunctions-$(VERSION).tgz
FILES=$(shell find microfunctions/)

default: $(PKG)
	-rm -f MicroFunctions.tgz
	ln -s $(PKG) MicroFunctions.tgz

.PHONY: push deploy undeploy

$(PKG): $(FILES)
	rm -f $(PKG)
	helm package --app-version $(VERSION) --version $(VERSION) microfunctions/

-include ../../docker.mk

push:
	@echo "Pushing to registry $(REGISTRY)"
	make -C ../../Sandbox push
	make -C ../../ManagementService push
	make -C ../../DataLayerService push
	make -C ../../riak push
	make -C ../../GUI push
	make -C ../../TriggersFrontend push

deploy: push
	helm install mfn microfunctions/
