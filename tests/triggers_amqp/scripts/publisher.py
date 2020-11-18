#!/usr/bin/env python
import pika
import json
import time
import socket

curr_hostname = socket.gethostname()
credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters(curr_hostname, 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='egress_exchange', exchange_type='topic', durable=False)

routing_key = "rabbit.routing.key"

for i in range(10000):
    message = str(int(time.time() * 1000))
    channel.basic_publish(exchange='egress_exchange', routing_key=routing_key, body=message)
    time.sleep(1)
    print("Publishing: " + message)

connection.close()

