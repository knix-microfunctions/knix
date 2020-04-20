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
default: init_once riak elasticsearch fluentbit datalayer frontend sandbox management nginx
	echo "Installed KNIX MicroFunctions"

clean:
	rm -f $(LOGS)

$(NAMES): %: %.log

$(LOGS): %.log: %.yaml settings.json ansible.cfg inventory.cfg
	ansible-playbook -e "@settings.json" $< 2>&1 >$@.tmp
	mv $@.tmp $@

nginx.yaml: ../knix_gui.tar.gz
	touch $@

../knix_gui.tar.gz:
	cd ..; make $(@:../%=%); cd -

../../DataLayerService/target/datalayerservice.jar:
	cd ../../DataLayerService/; make; cd -

datalayer.yaml: ../../DataLayerService/target/datalayerservice.jar
	touch $@

riak.yaml: ../mfn_riak_deployment_package.tar.gz
	touch $@

../knix_riak_deployment_package.tar.gz:
	cd ..; make $(@:../%=%); cd -

FLUENTBITFILES=$(shell find ../../LoggingService/)
../../LoggingService/fluentbit: $(FLUENTBITFILES)
	cd ../../LoggingService; make; cd -

fluentbit.yaml: ../../LoggingService/fluentbit
	cd ..; make fluentbit; cd -
	touch $@
