#!/bin/sh
docker run -it --rm --network host --name rabbit --hostname $(hostname) -e RABBITMQ_DEFAULT_USER=rabbituser -e RABBITMQ_DEFAULT_PASS=rabbitpass -e RABBITMQ_DEFAULT_VHOST=/rabbitvhost rabbitmq

