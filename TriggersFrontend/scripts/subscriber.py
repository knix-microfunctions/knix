#!/usr/bin/env python
import pika
import json
import time

credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters('paarijaat-debian-vm', 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

#channel.exchange_declare(exchange='egress_exchange', exchange_type='topic', durable=True)


result = channel.queue_declare('somename', durable=False, exclusive=False)
queue_name = result.method.queue

routing_key = "rabbit.*.*"

channel.queue_bind(exchange='egress_exchange', queue=queue_name, routing_key=routing_key)


def callback(ch, method, properties, body):
    data = body.decode()
    print(" [x] %r:%r" % (method.routing_key, data))

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()

