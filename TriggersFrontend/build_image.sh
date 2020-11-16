#!/bin/sh
docker build -t 'triggers_frontend' --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg HTTP_PROXY=$HTTP_PROXY --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy .