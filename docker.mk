##############################
## Container images
##
SHELL := /bin/bash
REGISTRY ?= localhost:5000
SELF_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
VERSION ?= $(shell git -C $(SELF_DIR) describe --tags --dirty)

define build_image
	@#echo "Dockerfile $(1)"
	@#echo "container $(2)"
	@#echo "Current dependencies $^"
	@CDATE=$$(docker image inspect $(2):$(VERSION) --format '{{.Created}}'); \
	if [[ $$? != 0 ]]; then \
		docker pull $(REGISTRY)/$(2):$(VERSION); \
		docker tag $(REGISTRY)/$(2):$(VERSION) $(2):$(VERSION); \
		CDATE=$$(docker image inspect $(2):$(VERSION) --format '{{.Created}}'|| echo "1970-01-01 00:00:00.000000"); \
	fi; \
	CTIME=$$(date --date="$$(echo $$CDATE | awk '{print $$1" "$$2}')" +"%s"); \
	for file in $^; do \
	  if [[ $$CTIME -lt $$(stat -c %Y $$file) ]]; then \
	    echo "$$file is newer than the container"; \
	    OLDID=$$(docker images $(2):$(VERSION) --format '{{.ID}}'); \
	    docker -D -l debug build \
			--build-arg http_proxy=$${HTTP_PROXY:-$${http_proxy:-$(HTTP_PROXY)}} \
			--build-arg https_proxy=$${HTTPS_PROXY:-$${https_proxy:-$(HTTP_PROXY)}} \
			--build-arg VERSION=$(VERSION) \
			-f $(1) \
			-t $(2):$(VERSION) . || exit $$!; \
	    docker tag $(2):$(VERSION) $(2):latest; \
	    NEWID=$$(docker images $(2):$(VERSION) --format '{{.ID}}'|grep -v "$$OLDID"); \
	    if [[ ! -z "$$OLDID" && ! -z "$$NEWID" ]]; then echo "Removing image $$OLDID"; docker rmi $$OLDID; fi; \
	    break; \
	  fi; \
	done; if [ -z "$$NEWID" ]; then echo "Container image $(2):$(VERSION) is already up-to-date"; fi
endef

define push_image
	@#echo local image name $(1)
	ID=$$(docker images $(1):$(VERSION) --format '{{.ID}}'); \
	MANIFEST=$$(curl -s -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' https://$(REGISTRY)/v2/$(1)/manifests/$(VERSION) || echo "")
	if [[ -z "$${MANIFEST}" ]]; then \
		MANIFEST=$$(curl -s -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' http://$(REGISTRY)/v2/$(1)/manifests/$(VERSION) || echo ""); \
	fi; \
	RID=$$(echo $$MANIFEST|python -c 'import json; import sys; print(json.loads(sys.stdin.read())["config"]["digest"].split(":")[1])' 2>/dev/null|| echo ""); \
	if [[ ! -z "$${ID}" && ! -z "$${RID}" && "$${RID}" == "$${ID}"* ]]; then \
		echo "Already pushed local image $(1):$(VERSION) ($${ID}) as $(REGISTRY)/$(1):$(VERSION) ($${RID})"; \
	else \
		echo "Tagging and pushing $(1):$(VERSION) as $(REGISTRY)/$(1):$(VERSION)"; \
		docker tag $(1):$(VERSION) $(REGISTRY)/$(1):$(VERSION) || exit $$?; \
		docker push $(REGISTRY)/$(1):$(VERSION) || exit $$?; \
	fi
endef
