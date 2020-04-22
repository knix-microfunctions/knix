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
namespace java org.microfunctions.queue.local
namespace py local_queue.service

struct LocalQueueMessage {
	1: optional i64 index,
	2: binary payload
}

service LocalQueueService {
	void addTopic (1: string topic),
	void removeTopic (1: string topic),
	
	bool addMessage (1: string topic, 2: LocalQueueMessage message),
    oneway void addMessageNoack (1: string topic, 2: LocalQueueMessage message),

    LocalQueueMessage getAndRemoveMessage (1: string topic, 2: i64 timeout),
    LocalQueueMessage getMessage (1: string topic, 2: i64 timeout),

    list<LocalQueueMessage> getAndRemoveMultiMessages (1: string topic, 2: i32 maxCount, 3: i64 timeout),

	i64 totalMemory (),
	i64 freeMemory ()
}

