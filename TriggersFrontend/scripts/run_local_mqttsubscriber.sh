#!/bin/sh
docker run -it --rm --network host --name mqttsubscriber -v "$(pwd)":/code -w /code python:3.6 bash -c './mqttsubscriber.sh'
