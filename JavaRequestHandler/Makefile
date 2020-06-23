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

all: build_thrift \
	target/javaworker.jar \
	mfnapi

build_thrift:
	cd ../build_tools/thrift/$(THRIFT_VERSION)/; ./build_thrift.sh; cd -

mfnapi:
	docker run --rm --name mfnapijava \
	--user $(UID):$(GID) \
	-v $(CURDIR)/target/classes:/usr/src/mfnapijava -w /usr/src/mfnapijava \
	openjdk:8-jdk-stretch \
	bash -c 'jar -cvf mfnapi.jar org/microfunctions/mfnapi/*.class'; \
	mv -v target/classes/mfnapi.jar .

src/main/java/org/microfunctions/mfnapi/MicroFunctionsAPIService.java: ../build_env.mk \
	../FunctionWorker/MicroFunctionsAPI.thrift
	cp ../FunctionWorker/MicroFunctionsAPI.thrift .
	docker run --rm -it --name mfnapi-thrift \
		--user $(UID):$(GID) \
		-v $(CURDIR):/usr/src/mfnapi -w /usr/src/mfnapi \
		$(THRIFT_IMAGE_NAME):$(THRIFT_VERSION) \
		bash -c 'thrift --gen java -out ./src/main/java/ ./MicroFunctionsAPI.thrift'
	rm ./MicroFunctionsAPI.thrift

# In case the user doesn't have maven configurations in the home directory, we need to create it
~/.m2/settings-docker.xml: settings-docker.xml.sample
	if [ ! -e ~/.m2 ]; then mkdir ~/.m2; fi
	cp settings-docker.xml.sample $@.tmp; \
	noproxyhosts=$$(echo $$no_proxy|sed 's/,/|/g'); \
	http_proxy=$${http_proxy:-$${HTTP_PROXY}}; \
	https_proxy=$${https_proxy:-$${HTTPS_PROXY}}; \
	if [ "$$http_proxy" != "" ]; then proto=$${http_proxy%://*}; port=$${http_proxy##*:}; port=$${port%/*}; host=$${http_proxy#*://}; host=$${host%:*}; \
	sed "s#<proxy><id>http</id>.*#<proxy><id>http</id><active>true</active><protocol>$${proto}</protocol><host>$${host}</host><port>$${port:-80}</port><nonProxyHosts>$${noproxyhosts}</nonProxyHosts></proxy>#" -i $@.tmp; \
	else sed "s#<proxy><id>http</id>.*##" -i $@.tmp; fi; \
	if [ "$$https_proxy" != "" ]; then proto=$${https_proxy%://*}; port=$${https_proxy##*:}; port=$${port%/*}; host=$${https_proxy#*://}; host=$${host%:*}; \
	sed "s#<proxy><id>https</id>.*#<proxy><id>https</id><active>true</active><protocol>$${proto}</protocol><host>$${host}</host><port>$${port:-80}</port><nonProxyHosts>$${noproxyhosts}</nonProxyHosts></proxy>#" -i $@.tmp; \
	else sed "s#<proxy><id>https</id>.*##" -i $@.tmp; fi;
	mv $@.tmp $@

# all source files except DataLayerService.java (would be mentioned explicitly)
JAVA_SOURCES=$(shell find src/ -type f|grep -v src/main/java/org/microfunctions/mfnapi/MicroFunctionsAPIService.java)
GIT_REVISION:=`git describe --tags --always --dirty=-dirty`
target/javaworker.jar: $(JAVA_SOURCES) \
		src/main/java/org/microfunctions/mfnapi/MicroFunctionsAPIService.java \
		~/.m2/settings-docker.xml
	if [ ! -e ~/.m2/repository ]; then mkdir -p ~/.m2/repository; fi
	docker run --rm -it --name javaworker \
	--user $(UID):$(GID) \
	-v ~/.m2:/usr/share/maven/ref \
	-v $(CURDIR):/usr/src/javaworker -w /usr/src/javaworker \
	maven:3.6.1-jdk-8 \
	mvn -Drevision=$(GIT_REVISION) -Dlibthrift.version=$(MVN_LIBTHRIFT_VERSION) -DargLine="-Duser.home=/tmp" -s /usr/share/maven/ref/settings-docker.xml -e package; 

java_api_doc: $(JAVA_SOURCES) \
		src/main/java/org/microfunctions/mfnapi/MicroFunctionsAPIService.java \
		target/javaworker.jar \
		mfnapi \
		~/.m2/settings-docker.xml
	docker run --rm -it --name javaworker \
		--user $(UID):$(GID) \
		-v ~/.m2:/usr/share/maven/ref \
		-v $(CURDIR):/usr/src/javaworker -w /usr/src/javaworker \
		maven:3.6.1-jdk-8 \
		mvn -Drevision=$(GIT_REVISION) -Dlibthrift.version=$(MVN_LIBTHRIFT_VERSION) -DargLine="-Duser.home=/tmp" -s /usr/share/maven/ref/settings-docker.xml -e javadoc:javadoc;

clean:
	rm -rf target/
	rm -f mfnapi.jar

