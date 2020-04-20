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

default: all

all: javarequesthandler queueservice datalayerserver frontend fluentbit managementservice

javarequesthandler:
	cd JavaRequestHandler && make

queueservice:
	cd QueueService && make

datalayerserver:
	cd DataLayerService && make

frontend:
	cd HttpFrontend && make

fluentbit:
	cd LoggingService && make

managementservice:
	cd ManagementService && make

riaklibs:
	cd riak && make

clean:
	cd JavaRequestHandler && make clean
	cd QueueService && make clean
	cd DataLayerService && make clean
	cd HttpFrontend && make clean
	cd LoggingService && make clean
	cd ManagementService && make clean
	cd riak && make clean

push:
	cd Sandbox && make push
	cd ManagementService && make push
	cd DataLayerService && make push
	cd riak && make push
	cd HttpFrontend && make push
	cd GUI && make push
