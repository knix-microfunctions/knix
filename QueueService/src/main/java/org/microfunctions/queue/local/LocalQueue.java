/*
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
package org.microfunctions.queue.local;

import java.nio.ByteBuffer;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

public class LocalQueue {
    
    public static final long NO_MESSAGE_INDEX = 0L;
    public static final long VALID_MESSAGE_INDEX = 1L;
    public static final LocalQueueMessage NO_MESSAGE = new LocalQueueMessage(ByteBuffer.allocate(0)).setIndex(NO_MESSAGE_INDEX);
    
    // define a queue capacity; this will mean that the queue for a function will have only this many outstanding messages
    private static final int QUEUE_SIZE = 1000;
    
    private ConcurrentHashMap<String, LinkedBlockingQueue<LocalQueueMessage>> topicToNewMessages = new ConcurrentHashMap<String, LinkedBlockingQueue<LocalQueueMessage>>();
    
    public void addTopic (String topic) {
        topicToNewMessages.putIfAbsent(topic, new LinkedBlockingQueue<LocalQueueMessage>(QUEUE_SIZE));
    }
    
    public void removeTopic (String topic) {
        topicToNewMessages.remove(topic);
    }
    
    public boolean addMessage (String topic, LocalQueueMessage message) {
        LinkedBlockingQueue<LocalQueueMessage> newMessages = topicToNewMessages.get(topic);
        return (newMessages != null)? newMessages.offer(message): false;
    }
    
    public void addMessageNoAck (String topic, LocalQueueMessage message) {
        LinkedBlockingQueue<LocalQueueMessage> newMessages = topicToNewMessages.get(topic);
        if (newMessages != null)
        {
            newMessages.offer(message);
        }
    }

    public LocalQueueMessage getAndRemoveMessage (String topic, long timeout) {
        LinkedBlockingQueue<LocalQueueMessage> newMessages = topicToNewMessages.get(topic);
        if (newMessages == null) {
            return NO_MESSAGE;
        }
        
        LocalQueueMessage message = null;
        try {
            message = newMessages.poll(timeout, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            return NO_MESSAGE;
        }
        if (message == null) {
            return NO_MESSAGE;
        }
        
        message.setIndex(VALID_MESSAGE_INDEX);
        return message;
    }
    
    public LocalQueueMessage getMessage (String topic, long timeout) {
        LocalQueueMessage message = this.getAndRemoveMessage(topic, timeout);
        long index = message.getIndex();
        
        if (index == NO_MESSAGE_INDEX) {
            return NO_MESSAGE;
        }
        
        return message;
    }
}

