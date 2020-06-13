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

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TCompactProtocol

from local_queue.service import LocalQueueService
from local_queue.service.ttypes import LocalQueueMessage

class LocalQueueClient:
    '''
    The local queue client that is utilized by the function worker to
        - subscribe to the local queue and retrieve any messages
        - publish messages to the local queue topics of other functions as well
        as the publication manager in the queue service.

    '''
    def __init__(self, connect="127.0.0.1:4999"):
        self.qaddress = connect
        self.connect()

    def connect(self):
        host, port = self.qaddress.split(':')
        retry = 0.5 #s
        while True:
            try:
                self.socket = TSocket.TSocket(host, int(port))
                self.transport = TTransport.TFramedTransport(self.socket)
                self.transport.open()
                self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
                self.queue = LocalQueueService.Client(self.protocol)
                break
            except Thrift.TException as exc:
                if retry < 60:
                    print("[LocalQueueClient] Could not connect due to "+str(exc)+", retrying in "+str(retry)+"s")
                    time.sleep(retry)
                    retry = retry * 2
                else:
                    raise

    def addMessage(self, topic, lqcm, ack):
        status = True
        message = LocalQueueMessage()
        message.payload = lqcm.get_serialized().encode()
        try:
            if ack:
                status = self.queue.addMessage(topic, message)
            else:
                self.queue.addMessageNoack(topic, message)
        except TTransport.TTransportException as exc:
            print("[LocalQueueClient] Reconnecting because of failed addMessage: " + str(exc))
            status = False
            self.connect()
        except Exception as exc:
            print("[LocalQueueClient] failed addMessage: " + str(exc))
            raise

        return status

    def getMessage(self, topic, timeout):
        try:
            lqm = self.queue.getAndRemoveMessage(topic, timeout)
            if lqm.index != 0:
                return lqm
        except TTransport.TTransportException as exc:
            print("[LocalQueueClient] Reconnecting because of failed getMessage: " + str(exc))
            self.connect()
        except Exception as exc:
            print("[LocalQueueClient] failed getMessage: " + str(exc))
            raise

        return None

    def getMultipleMessages(self, topic, max_count, timeout):
        try:
            lqm_list = self.queue.getAndRemoveMultiMessages(topic, max_count, timeout)
        except TTransport.TTransportException as exc:
            print("[LocalQueueClient] Reconnecting because of failed getMultipleMessages: " + str(exc))
            lqm_list = []
            self.connect()
        except Exception as exc:
            print("[LocalQueueClient] failed getMultipleMessages: " + str(exc))
            raise

        return lqm_list

    def shutdown(self):
        if self.transport.isOpen():
            #self.socket.handle.shutdown(socket.SHUT_RDWR)
            self.transport.close()

    def addTopic(self, topic):
        try:
            self.queue.addTopic(topic)
        except Thrift.TException as exc:
            print("[LocalQueueClient] failed addTopic: " + str(exc))
        except Exception as exc:
            print("[LocalQueueClient] failed addTopic: " + str(exc))
            raise

    def removeTopic(self, topic):
        try:
            self.queue.removeTopic(topic)
        except Thrift.TException as exc:
            print("[LocalQueueClient] failed removeTopic: " + str(exc))
        except Exception as exc:
            print("[LocalQueueClient] failed removeTopic: " + str(exc))
            raise
