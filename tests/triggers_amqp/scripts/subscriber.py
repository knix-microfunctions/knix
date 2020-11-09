#!/usr/bin/env python
import pika
import json
import time
import os

credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters('paarijaat-debian-vm', 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

result = channel.queue_declare('somename', durable=False, exclusive=False)
queue_name = result.method.queue

routing_key = "rabbit.*.*"

channel.queue_bind(exchange='egress_exchange', queue=queue_name, routing_key=routing_key)


def callback(ch, method, properties, body):
    #data = body.decode()
    #print(" [x] %r:%r" % (method.routing_key, data))
    try:
        data = body.decode()
        if data is not None and data is not "" and len(data) > 0:
            os._exit(0)
    except Exception as e:
        pass


channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()

