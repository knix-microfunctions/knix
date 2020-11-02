#!/usr/bin/env python
import pika
import json
import time

credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters('paarijaat-debian-vm', 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='rabbitexchange', exchange_type='topic', durable=False)

routing_key = "rabbit.routing.key"

for i in range(100):
    message = str(int(time.time() * 1000))
    channel.basic_publish(exchange='rabbitexchange', routing_key=routing_key, body=message)
    time.sleep(1)
    print(message)

connection.close()

