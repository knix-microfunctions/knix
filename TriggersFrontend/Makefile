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
include ../build_env.mk
UID:=`id -u`
GID:=`id -g`

all: target/release/TriggersFrontend

GIT_REVISION:=`git describe --tags --always --dirty=-dirty`
RUST_SOURCES=$(shell find src/ -type f)
target/release/TriggersFrontend: $(RUST_SOURCES) Cargo.toml ../build_env.mk
	docker run -it --rm --name build_triggers_frontend \
		--user $(UID):$(GID) \
		-v $(CURDIR):/code -w /code \
		$(RUST_IMAGE_NAME):$(RUST_VERSION) bash -c 'cargo build --release'

clean:
	rm -f ./target/release/TriggersFrontend

include ../docker.mk

image: Dockerfile target/release/TriggersFrontend
	$(call build_image,Dockerfile,microfn/triggers_frontend)

push: image
	$(call push_image,microfn/triggers_frontend)
