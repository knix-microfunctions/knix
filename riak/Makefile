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

default: image

include ../docker.mk

lib/jiffy.tgz: Dockerfile
	mkdir -p lib
	echo "Building jiffy"
	$(call build_image,Dockerfile,riak_libs_build)
	docker run -i --rm -u $$(id -u):$$(id -g) -v $(CURDIR):/temp -w /temp --ulimit nofile=262144:262144 riak_libs_build cp /build/jiffy.tgz ./lib/.

image: Dockerfile-riak \
		lib/jiffy.tgz \
		src/mfn_counter_triggers.erl \
		src/workflow_triggers.erl \
		$(shell find script/ -type f)
	$(call build_image,Dockerfile-riak,microfn/riak)

push: image
	$(call push_image,microfn/riak)
