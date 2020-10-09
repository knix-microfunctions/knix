#!/usr/bin/env python
import pika
import json
import time

credentials = pika.PlainCredentials('rabbituser', 'rabbitpass')
parameters = pika.ConnectionParameters('paarijaat-debian-vm', 5672, '/rabbitvhost', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.exchange_declare(exchange='rabbitexchange', exchange_type='topic', durable=True)


result = channel.queue_declare('', durable=True, exclusive=True)
queue_name = result.method.queue

binding_key = "rabbit.routing.key"

channel.queue_bind(exchange='rabbitexchange', queue=queue_name, routing_key=binding_key)

'''
def callknix(data):
    tmid = time.time()*1000.0
    d=json.loads(data)
    input_dict = {'t1': d['t1'], 'tmid': tmid}

    urlstr = 'http://192.168.33.21:32789'
    r = requests.post(urlstr, json=input_dict, verify=False)
    d2=json.loads(r.text)
    diff = d2['t2']-d2['t1']
    d1 = tmid - d2['t1']
    d2 = d2['t2'] - tmid
    print(diff, d1, d2, r.url, r.status_code, r.reason, r.text)
'''

def callback(ch, method, properties, body):
    data = body.decode()
    print(" [x] %r:%r" % (method.routing_key, data))
    #callknix(data)


channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()

