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

SHELL := /bin/bash

YAML := $(wildcard *.yaml)
LOGS := $(YAML:%.yaml=%.log)
NAMES := $(YAML:%.yaml=%)

.PHONY: $(NAMES)
default: prepare_packages install

install: init_once installnvidiadocker riak elasticsearch fluentbit datalayer sandbox management nginx triggers_frontend
	echo "Installed KNIX MicroFunctions"

clean:
	rm -f $(LOGS)

prepare_packages: ../../riak/knix_riak_deployment_package.tar.gz \
	../../LoggingService/fluentbit \
	../../DataLayerService/target/datalayerservice.jar \
	../../Sandbox/sandbox_deployment_package.tar.gz \
	../../ManagementService/management_deployment_package.tar.gz \
	../../GUI/knix_gui_deployment_package.tar.gz \
	../../TriggersFrontend/target/release/TriggersFrontend


$(NAMES): %: %.log

$(LOGS): %.log: %.yaml settings.json ansible.cfg inventory.cfg
	ansible-playbook -e "@settings.json" $< 2>&1 >$@.tmp
	mv $@.tmp $@

############################
# riak.yaml and dependencies
RIAK_SRC:=../../riak
RIAKFILES:=$(shell find $(RIAK_SRC) | grep -v knix_riak_deployment_package.tar.gz)
../../riak/knix_riak_deployment_package.tar.gz:
	cd $(RIAK_SRC) && make lib/jiffy.tgz && cd -
	tar -czf $@ -C $(RIAK_SRC) ./lib/jiffy.tgz ./src

riak.yaml: ../../riak/knix_riak_deployment_package.tar.gz
	touch $@

# fluentbit.yaml and dependencies
FLUENTBITFILES=$(shell find ../../LoggingService/)
../../LoggingService/fluentbit: $(FLUENTBITFILES)
	cd ../../LoggingService; make; cd -

fluentbit.yaml: ../../LoggingService/fluentbit
	touch $@

# datalayer.yaml and dependencies
../../DataLayerService/target/datalayerservice.jar:
	cd ../../DataLayerService/; make; cd -

datalayer.yaml: ../../DataLayerService/target/datalayerservice.jar
	touch $@

# sandbox.yaml and dependencies
../../Sandbox/sandbox_deployment_package.tar.gz:
	cd ../../Sandbox/; make build; cd -
	tar -czf $@ -C ../../Sandbox \
                Dockerfile \
                Dockerfile_java \
                build/ \
                frontend/frontend

sandbox.yaml: ../../Sandbox/sandbox_deployment_package.tar.gz
	touch $@

# management.yaml and dependencies
MANAGEMENT_SRC:=../../ManagementService
MANAGEMENTFILES:=$(shell find $(MANAGEMENT_SRC) | grep -v "management_deployment_package.tar.gz")
../../ManagementService/management_deployment_package.tar.gz: $(MANAGEMENTFILES)
	cd ../../ManagementService/; make; cd -

management.yaml: ../../ManagementService/management_deployment_package.tar.gz
	touch $@

# nginx.yaml and dependencies
GUI_SRC:=../../GUI
GUIFILES:=$(shell find $(GUI_SRC) | grep -v "knix_gui_deployment_package.tar.gz")
../../GUI/knix_gui_deployment_package.tar.gz: $(GUIFILES)
	touch $@
	cd ../../GUI; make; cd -
	tar --exclude=knix_gui_deployment_package.tar.gz -czf $@ -C $(GUI_SRC) .

nginx.yaml: ../../GUI/knix_gui_deployment_package.tar.gz
	touch $@

# triggers_frontend.yaml and dependencies
../../TriggersFrontend/target/release/TriggersFrontend:
	cd ../../TriggersFrontend/; make; cd -

triggers_frontend.yaml: ../../TriggersFrontend/target/release/TriggersFrontend
	touch $@
