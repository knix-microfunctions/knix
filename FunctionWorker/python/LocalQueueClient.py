#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import time
import socket

import redis

class LocalQueueClient:
    '''
    The local queue client that is utilized by the function worker to
        - subscribe to the local queue and retrieve any messages
        - publish messages to the local queue topics of other functions as well
        as the publication manager in the queue service.

    '''
    def __init__(self, connect="127.0.0.1:4999"):
        self._qaddress = connect

        self._is_running = True

        self.connect()

    def connect(self):
        while self._is_running:
            try:
                self._queue = redis.Redis.from_url("redis://" + self._qaddress, decode_responses=True)
                break
            except Exception as exc:
                if retry < 60:
                    print("[LocalQueueClient] Could not connect due to " + str(exc) + ", retrying in " + str(retry) + "s")
                    time.sleep(retry)
                    retry = retry * 2
                else:
                    raise

    def addMessage(self, topic, message, ack):
        status = True
        try:
            if ack:
                status = bool(self._queue.xadd(topic, message.get_message()))
            else:
                self._queue.xadd(topic, message.get_message())
        except Exception as exc:
            print("[LocalQueueClient] Reconnecting because of failed addMessage: " + str(exc))
            status = False
            self.connect()

        return status

    def getMessage(self, topic, timeout):
        message = None
        try:
            message_list = self._queue.xread({topic: 0}, block=timeout, count=1)
            if message_list:
                message = message_list[0][1][0][1]
                # remove the message from the topic
                msg_id = message_list[0][1][0][0]
                self._queue.xdel(topic, msg_id)
        except Exception as exc:
            print("[LocalQueueClient] Reconnecting because of failed getMessage: " + str(exc))
            self.connect()

        return message

    def getMultipleMessages(self, topic, max_count, timeout):
        message_list = []
        try:
            message_list = self._queue.xread({topic: "0"}, block=timeout, count=max_count)
        except Exception as exc:
            print("[LocalQueueClient] Reconnecting because of failed getMultipleMessages: " + str(exc))
            self.connect()

        msg_list = []
        for msg in message_list[0][1]:
            msg_list.append(msg[1])
            # remove the message from the topic
            self._queue.xdel(topic, msg[0])

        return msg_list

    def shutdown(self):
        self._is_running = False
        self._queue.close()

    def addTopic(self, topic):
        # no op with regular streams
        return

    def removeTopic(self, topic):
        self._queue.xtrim(topic, "0", approximate=False)
