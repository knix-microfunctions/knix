#!/bin/sh
docker run -it --rm --network host --name mqttpublisher -v $(pwd):/code -w /code python:3.6 bash -c './mqttpublisher.sh'
