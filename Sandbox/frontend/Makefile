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

UID:=`id -u`
GID:=`id -g`
-include ../../proxy.mk
include ../../build_env.mk
SOURCES=$(shell find ./ -name '*.go')

default: build_thrift \
	frontend

build_thrift:
	cd ../../build_tools/thrift/$(THRIFT_VERSION)/; ./build_thrift.sh; cd -

datalayermessage: ../../DataLayerService/thrift/DataLayerMessage.thrift ../../build_env.mk
	docker run --rm -it --name sandbox-thrift \
		--user $(UID):$(GID) \
		-v $(CURDIR)/../../DataLayerService:/usr/src/datalayer \
		-v $(CURDIR):/usr/src/sandbox -w /usr/src/sandbox \
		$(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) \
		bash -c 'thrift --gen go:package_prefix=github.com/knix-microfunctions/knix/Sandbox/frontend/ -out ./ /usr/src/datalayer/thrift/DataLayerMessage.thrift'

datalayerservice: ../../DataLayerService/thrift/DataLayerService.thrift ../../build_env.mk
	docker run --rm -it --name sandbox-thrift \
		--user $(UID):$(GID) \
		-v $(CURDIR)/../../DataLayerService:/usr/src/datalayer \
		-v $(CURDIR):/usr/src/sandbox -w /usr/src/sandbox \
		$(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) \
		bash -c 'thrift --gen go:package_prefix=github.com/knix-microfunctions/knix/Sandbox/frontend/ -out ./ /usr/src/datalayer/thrift/DataLayerService.thrift'

localqueueservice: ../../QueueService/thrift/LocalQueueService.thrift ../../build_env.mk
	docker run --rm -it --name sandbox-thrift \
		--user $(UID):$(GID) \
		-v $(CURDIR)/../../QueueService:/usr/src/queue \
		-v $(CURDIR):/usr/src/sandbox -w /usr/src/sandbox \
		$(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) \
		bash -c 'thrift --gen go:package_prefix=github.com/knix-microfunctions/knix/Sandbox/frontend/ -out ./ /usr/src/queue/thrift/LocalQueueService.thrift'

mfnmessage.go: ../schema/mfnmessage-schema.json
	docker run --rm -it --name mfn-event-schema \
		--user $(UID):$(GID) \
		--env http_proxy=$(HTTP_PROXY) \
		--env https_proxy=$(HTTPS_PROXY) \
		--env XDG_CACHE_HOME=/tmp/.cache \
		-v $(CURDIR)/../:/usr/src/sandbox \
		-w /usr/src/sandbox/frontend \
		golang:1.13 \
		bash -c 'go get github.com/a-h/generate/...; schema-generate $^ > $@'

#mfnworkflow.go: ../schema/mfnworkflow-schema.json
#	docker run --rm -it --name sandbox-jsonschema \
#		--user $(UID):$(GID) \
#		--env http_proxy=$(HTTP_PROXY) \
#		--env https_proxy=$(HTTPS_PROXY) \
#		-v $(CURDIR)/../:/usr/src/sandbox \
#		-w /usr/src/sandbox/frontend \
#		golang:1.13 \
#		bash -c 'go get github.com/a-h/generate/...; schema-generate $^ > $@'

frontend: mfnmessage.go localqueueservice datalayermessage datalayerservice $(SOURCES)
	-rm -f frontend
	docker run --rm -it --name build-$@ \
		--user $(UID):$(GID) \
		--env http_proxy=$(HTTP_PROXY) \
		--env https_proxy=$(HTTPS_PROXY) \
		--env XDG_CACHE_HOME=/tmp/.cache \
		-v $(CURDIR):/app \
		-w /app \
		golang:1.13 \
		bash -c 'go mod download; CGO_ENABLED=0 GOOS=linux go build -v -o $@'

clean:
	rm -rf frontend mfnmessage.go mfnworkflow.go localqueueservice datalayermessage datalayerservice

test: frontend
	mkdir -p logs
	MFN_DATALAYER=192.168.137.111:4998 \
	MFN_QUEUE=192.168.137.111:4999 \
	MFN_QUEUE=192.168.137.111:4999 \
	MFN_ENTRYTOPIC=abc \
	MFN_RESULTTOPIC=abc \
	USERID=admin@management \
	SANDBOXID=Management \
	WORKFLOWID=Management \
	PORT=33333 \
	./frontend &
	sleep 3
	curl -sS -H 'Content-type: application/json' --data '{"foo":"bar","mybool":true,"mynum":5.5}' "http://127.0.0.1:33333/"
	sleep 1
	EID=$$(curl -sS --max-redirs 0 -H 'Content-type: application/json' --data '{"foo":"bar","mybool":true,"mynum":5.5}' "http://127.0.0.1:33333/?async=1"); echo ""; echo "Fetching result of $$EID (first async attempt)"; echo $$(curl -sS -H 'Content-type: application/json' "http://127.0.0.1:33333/?executionId=$${EID}&async=true"); sleep 2; echo "Fetching result of $$EID (second async attempt)"; echo $$(curl -sS -H 'Content-type: application/json' "http://127.0.0.1:33333/?executionId=$${EID}&async=true")
	sleep 2
	EID=$$(curl -sS --max-redirs 0 -H 'Content-type: application/json' --data '{"foo":"bar","mybool":true,"mynum":5.5}' "http://127.0.0.1:33333/?async=1"); echo ""; echo "Fetching result of $$EID (concurrent synchronous attempts)"; for (( x=0;x<5;x++ )); do echo $$(curl -sS -H 'Content-type: application/json' "http://127.0.0.1:33333/?executionId=$${EID}") & done; echo ""
	sleep 2
	pkill frontend
