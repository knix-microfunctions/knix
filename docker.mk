##############################
## Container images
##
SHELL := /bin/bash
REGISTRY ?= localhost:5000
VERSION ?= latest #$(shell git describe --tags)

define build_image
	@#echo "Dockerfile $(1)"
	@#echo "container $(2)"
	@#echo "Current dependencies $^"
	@CDATE=$$(docker image inspect $(2) --format '{{.Created}}'); \
	if [[ $$? != 0 ]]; then \
		docker pull $(REGISTRY)/$(2):$(VERSION); \
		docker tag $(REGISTRY)/$(2):$(VERSION) $(2); \
		CDATE=$$(docker image inspect $(2) --format '{{.Created}}'|| echo "1970-01-01 00:00:00.000000"); \
	fi; \
	CTIME=$$(date --date="$$(echo $$CDATE | awk '{print $$1" "$$2}')" +"%s"); \
	for file in $^; do \
	  if [[ $$CTIME -lt $$(stat -c %Y $$file) ]]; then \
	    echo "$$file is newer than the container"; \
	    OLDID=$$(docker images $(2) --format '{{.ID}}'); \
	    docker -D -l debug build --no-cache \
			--build-arg http_proxy=$${HTTP_PROXY:-$${http_proxy:-$(HTTP_PROXY)}} \
			--build-arg https_proxy=$${HTTPS_PROXY:-$${https_proxy:-$(HTTP_PROXY)}} \
			-f $(1) \
			-t $(2) . || exit $$!; \
	    NEWID=$$(docker images $(2) --format '{{.ID}}'|grep -v "$$OLDID"); \
	    if [[ ! -z "$$OLDID" && ! -z "$$NEWID" ]]; then echo "Removing image $$OLDID"; docker rmi $$OLDID; fi; \
	    break; \
	  fi; \
	done; if [ "$$NEWID" == "" ]; then echo "Container image $(2) is already up-to-date"; fi
endef

define push_image
	@#echo local image name $(1)
	@ID=$$(docker images $(1) --format '{{.ID}}'); \
	RID2=$$(curl -s -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' $(REGISTRY)/v2/$(1)/manifests/$(VERSION)); \
	if [[ "$${RID2}" != "" ]]; then \
		RID=$$(echo $${RID2}|python -c 'import json; import sys; print(json.load(sys.stdin)["config"]["digest"].split(":")[1])'); \
	else \
		RID=""; \
	fi; \
	if [[ "$${RID}" == "$${ID}"* ]]; then \
		echo "Already pushed local image $(1) ($${ID}) as $(REGISTRY)/$(1):$(VERSION) ($${RID})"; \
	else \
		echo "Tagging and pushing $(1) as $(REGISTRY)/$(1):$(VERSION)"; \
		docker tag $(1) $(REGISTRY)/$(1):$(VERSION) || exit $$?; \
		docker push $(REGISTRY)/$(1):$(VERSION) || exit $$?; \
	fi
endef
