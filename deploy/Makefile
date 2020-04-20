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

GUI_PACKAGE=knix_gui.tar.gz
GUI_SRC=../GUI

SANDBOX_PACKAGE=sandboxagent.tar.gz

RIAK_PACKAGE=knix_riak_deployment_package.tar.gz
RIAK_SRC=../riak
RIAK_BUILD=knix_riak_deployment

default: all

all: $(GUI_PACKAGE) $(MANAGEMENT_PACKAGE) $(SANDBOX_PACKAGE) knix_riak

clean: clean_gui clean_sandbox clean_riak

#######################
## GUI archive
$(GUI_PACKAGE): $(shell find $(GUI_SRC))
	tar -czf $@ -C $(GUI_SRC) .

clean_gui:
	rm -rf $(GUI_PACKAGE)

#######################
## SANDBOX
## Logging Service's fluent-bit
fluentbit:
	cd ../LoggingService && make && cd -

## Sandbox
$(SANDBOX_PACKAGE):
	cd ../Sandbox; make build; cd -
	tar -czf $@ -C ../Sandbox \
		Dockerfile \
		Dockerfile_java \
		build/ \
		frontend/frontend

sandbox.tar:
	cd ../Sandbox; make container; cd -
	docker save -o $@ microfn/sandbox

sandbox_java.tar:
	cd ../Sandbox; make container_java; cd -
	docker save -o $@ microfn/sandbox_java

clean_sandbox:
	rm -rf $(SANDBOX_PACKAGE) sandbox.tar sandbox_java.tar

#######################
#######################
## RIAK

$(RIAK_BUILD):
	mkdir -p $(RIAK_BUILD)
	cp $(RIAK_SRC)/lib/jiffy.tgz $(RIAK_BUILD)/
	cp -r $(RIAK_SRC)/src/* $(RIAK_BUILD)/

knix_riak: $(RIAK_BUILD)
	tar -czf $(RIAK_PACKAGE) -C $(RIAK_BUILD) .
	rm -rf $(RIAK_BUILD)

clean_riak:
	rm -rf $(RIAK_PACKAGE)

