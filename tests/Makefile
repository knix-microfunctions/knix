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
TESTDIRS := $(shell ls -d */)
TESTS := $(TESTDIRS:%/=%)

.PHONY: $(TESTS)

all: $(TESTS)

quick: helloworld
asl: asl_*
java: java_*

$(TESTS):
	cd $@; PYTHONPATH=../../mfn_sdk python3 -m unittest discover -v

settings:
	if [ ! -e settings.json ]; then \
	cp settings.json.sample settings.json; \
	sed 's/"mfn_user": .*/"mfn_user": "test@knix",/' -i settings.json; \
	sed 's/"mfn_password": .*/"mfn_password": "test",/' -i settings.json; \
	sed 's/"mfn_name": .*/"mfn_name": "KNIX tests",/' -i settings.json; \
	sed 's#"http": .*#"http": "",#' -i settings.json; \
	sed 's#"https": .*#"https": ""#' -i settings.json; \
	sed 's/"timeout": .*/"timeout": 60/' -i settings.json; fi
	URL="http://127.0.0.1"; \
	if [ $$? == 0 ]; then sed 's#"mfn_url": .*#"mfn_url": "'$${URL}'",#' -i settings.json; fi

