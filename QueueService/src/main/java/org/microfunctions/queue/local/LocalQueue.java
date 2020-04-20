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
import java.util.concurrent.atomic.AtomicLong;

public class LocalQueue {
    
    public static final long NO_MESSAGE_INDEX = 0L;
    public static final long VALID_MESSAGE_INDEX = 1L;
    public static final LocalQueueMessage NO_MESSAGE = new LocalQueueMessage(ByteBuffer.allocate(0)).setIndex(NO_MESSAGE_INDEX);
    
    private ConcurrentHashMap<String, LinkedBlockingQueue<LocalQueueMessage>> topicToNewMessages = new ConcurrentHashMap<String, LinkedBlockingQueue<LocalQueueMessage>>();
    //private ConcurrentHashMap<String, AtomicLong> topicToIndex = new ConcurrentHashMap<String, AtomicLong>();
    //private ConcurrentHashMap<String, ConcurrentHashMap<Long, LocalQueueMessage>> topicToOldMessages = new ConcurrentHashMap<String, ConcurrentHashMap<Long, LocalQueueMessage>>();
    
    public void addTopic (String topic) {
        topicToNewMessages.putIfAbsent(topic, new LinkedBlockingQueue<LocalQueueMessage>());
        //topicToIndex.putIfAbsent(topic, new AtomicLong());
        //topicToOldMessages.putIfAbsent(topic, new ConcurrentHashMap<Long, LocalQueueMessage>());
    }
    
    public void removeTopic (String topic) {
        topicToNewMessages.remove(topic);
        //topicToIndex.remove(topic);
        //topicToOldMessages.remove(topic);
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
        
//        AtomicLong indexGenerator = topicToIndex.get(topic);
//        if (indexGenerator == null) {
//            return NO_MESSAGE;
//        }
//        message.setIndex(indexGenerator.incrementAndGet());
        message.setIndex(VALID_MESSAGE_INDEX);
        return message;
    }
    
    public LocalQueueMessage getMessage (String topic, long timeout) {
        LocalQueueMessage message = this.getAndRemoveMessage(topic, timeout);
        long index = message.getIndex();
        
        if (index == NO_MESSAGE_INDEX) {
            return NO_MESSAGE;
        }
        
        /*
        ConcurrentHashMap<Long, LocalQueueMessage> oldMessages = topicToOldMessages.get(topic);
        if (oldMessages == null) {
            return NO_MESSAGE;
        }
        oldMessages.put(index, message);
        */
        return message;
    }
    /*
    public boolean commitMessage (String topic, long index) {
        ConcurrentHashMap<Long, LocalQueueMessage> oldMessages = topicToOldMessages.get(topic);
        if (oldMessages == null) {
            return false;
        }
        
        return (oldMessages.remove(index) != null)? true: false;
    }
    
    public boolean reAddMessage (String topic, long index) {
        ConcurrentHashMap<Long, LocalQueueMessage> oldMessages = topicToOldMessages.get(topic);
        if (oldMessages == null) {
            return false;
        }
        
        LocalQueueMessage message = oldMessages.remove(index);
        if (message == null) {
            return false;
        }
        
        return this.addMessage(topic, message);
    }
    */
}

