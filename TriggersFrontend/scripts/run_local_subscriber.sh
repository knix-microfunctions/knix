#!/bin/sh
docker run -it --rm --network host --name rabbitsubscriber -v "$(pwd)":/code -w /code python:3.6 bash -c './subscriber.sh'
