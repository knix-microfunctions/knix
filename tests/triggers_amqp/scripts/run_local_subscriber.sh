#!/bin/sh
./scripts/wait-for-it.sh $(hostname):5672 -t 30
docker run -it --rm --network host --name rabbitsubscriber -v $(pwd):/code -w /code python:3.6 bash -c './scripts/subscriber.sh'
