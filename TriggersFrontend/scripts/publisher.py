#!/usr/bin/env python
import pika
import json
import time

credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters('paarijaat-debian-vm', 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='rabbitexchange', exchange_type='topic', durable=True)

routing_key = "rabbit.routing.key"

while True:
    value = input("Press Enter to send a message. Any other 'key + Enter' will exit. ")
    value = value.strip()
    if len(value) > 0:
        break;
    message = 'Hello world ' + str(time.time())
    channel.basic_publish(exchange='rabbitexchange', routing_key=routing_key, body=message)
    print(" [x] Sent %r:%r" % (routing_key, message))

connection.close()

