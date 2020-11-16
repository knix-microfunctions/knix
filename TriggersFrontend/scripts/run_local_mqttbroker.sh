#!/bin/sh
docker run -it --rm --network host --name mqtt --hostname $(hostname) eclipse-mosquitto