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
-include ../proxy.mk
include ../docker.mk

default: app/pages/docs/sdk/cli.md \
	app/pages/docs/sdk/sdk.md \
	app/pages/docs/api/javadoc/index.html \
	app/pages/docs/api/python/MicroFunctionsAPI.html

../FunctionWorker/doc/MicroFunctionsAPI.html:
	make -C ../FunctionWorker doc/MicroFunctionsAPI.html

app/pages/docs/api/python/MicroFunctionsAPI.html: ../FunctionWorker/doc/MicroFunctionsAPI.html
	mkdir -p app/pages/docs/api/python; \
	cp $^ app/pages/docs/api/python/; \
	sed -i 's/<body>/<body bgcolor="#fff">/g' $@

JAVADOC=../JavaRequestHandler/target/site/apidocs $(shell find ../JavaRequestHandler/target/site/apidocs/ -type f)
$(JAVADOC):
	make -C ../JavaRequestHandler target/site/apidocs/index.html

app/pages/docs/api/javadoc/index.html: $(JAVADOC)
	mkdir -p app/pages/docs/api/javadoc
	cp -r ../JavaRequestHandler/target/site/apidocs/* app/pages/docs/api/javadoc/
	touch $@

app/pages/docs/sdk/sdk.md: ../mfn_sdk/README.md
	cp ../mfn_sdk/README.md app/pages/docs/sdk/sdk.md

app/pages/docs/sdk/cli.md: ../mfn_cli/README.md
	cp ../mfn_cli/README.md app/pages/docs/sdk/cli.md

image:	$(shell find . -type f -not -name Makefile) \
	app/pages/docs/sdk/cli.md \
	app/pages/docs/sdk/sdk.md \
	app/pages/docs/api/javadoc/index.html \
	app/pages/docs/api/python/MicroFunctionsAPI.html
	$(call build_image,Dockerfile,microfn/nginx)

push: image
	$(call push_image,microfn/nginx)
