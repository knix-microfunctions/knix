#!/bin/sh
docker run -it --rm --network host --name rabbitpublisher -v $(pwd):/code -w /code python:3.6 bash -c './publisher.sh'
