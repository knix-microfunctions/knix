import paho.mqtt.client as mqtt
import json
import time

# Define Variables
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_TOPIC = "mqtttopic"

#MQTT_MSG=json.dumps({"key1": "value1","key2": 3.2,"key3": [10,20],"key4": {"subkey1": "acbd"}});
# Define on_publish event function

def on_connect(client, userdata, flags, rc):
    print("connected")

# Initiate MQTT Client
mqttc = mqtt.Client()

mqttc.on_connect = on_connect

# Connect with MQTT Broker
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

while True:
    value = input("Press Enter to send a message. Any other 'key + Enter' will exit. ")
    value = value.strip()
    if len(value) > 0:
        break;
    message = 'Hello world ' + str(time.time())
    mqttc.publish(MQTT_TOPIC, message)
    print(" [x] Sent %r:%r" % (MQTT_TOPIC, message))

client.close()
