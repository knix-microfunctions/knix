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

default: app/pages/docs/sdk/cli.md app/pages/docs/sdk/sdk.md

app/pages/docs/sdk/sdk.md: ../mfn_sdk/README.md
	cp ../mfn_sdk/README.md app/pages/docs/sdk/sdk.md

app/pages/docs/sdk/cli.md: ../mfn_cli/README.md
	cp ../mfn_cli/README.md app/pages/docs/sdk/cli.md

-include ../proxy.mk
include ../docker.mk

image: $(shell find ./ -type f|grep -v Makefile)
	$(call build_image,Dockerfile,microfn/nginx)

push: image
	$(call push_image,microfn/nginx)
