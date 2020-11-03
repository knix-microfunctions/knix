#!/bin/sh
docker run -d --rm --network host --name rabbitpublisher -v $(pwd):/code -w /code python:3.6 bash -c './scripts/publisher.sh'
