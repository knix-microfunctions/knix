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

default: all

all: fluent-bit

fluent-bit: fluent-bit-1.2.2/conf/*
	cd fluent-bit-1.2.2 && ./build-fluent-bit.sh && cd -
	rm -rf fluent-bit && cp -r ./fluent-bit-1.2.2/fluent-bit .

clean:
	rm -rf fluent-bit
	cd fluent-bit-1.2.2 && rm -rf fluent-bit && cd -
