#   Copyright 2021 The KNIX Authors
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

import requests
import base64
import json
import random
import sys
import time
import logging

from .deprecated import deprecated

#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class Trigger(object):
    """ Trigger is an available event trigger received through a message channel and can be linked to a workflow
    """

    def __init__(self,client,tname,bdetails):
        self.client=client
        self._name=tname
        self._update(bdetails)

    def _update(self,bdetails):
        self._id=bdetails["trigger_id"]
        self._status=bdetails["trigger_status"]
        self._type=bdetails["trigger_type"]
        self._count=bdetails["trigger_count"]
        self._associated_workflows=bdetails["associated_workflows"]
            # TODO: parse workflows
            #"workflow_name"
            #"wf_triggers_timer_based_trigger_control"
            #"workflow_url":"http://10.0.2.15:32768"
            #"workflow_state"
        self._info=bdetails["trigger_info"]
            # TODO: parse info
            #"amqp_addr":\"amqp://rabbituser:rabbitpass@paarijaat-debian-vm:5672/%2frabbitvhost\"
            #"routing_key":\"rabbit.*.*\"
            #"exchange\":\"egress_exchange\"
            #"durable\":false
            #"exclusive\":false
            #"auto_delete\":true
            #"no_wait\":true
            #"with_ack\":false"

    def __str__(self):
        return f"{self.name} ({self._id}, status: {self._status})"

    ### read-only properties
    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

    @property
    def type(self):
        return self._type

    @property
    def count(self):
        # TODO: decide whether to auto-fetch details when count is accessed 
        return self._count

    @property
    def associated_workflows(self):
        # TODO: decide whether to auto-fetch details when associated_workflows is accessed 
        return self._associated_workflows

    @property
    def settings(self):
        return self._settings

    def associate_workflow(self, wf):
        self.client.bind_trigger(self._name,wf._name)

    def disassociate_workflow(self, wf):
        self.client.unbind_trigger(self._name,wf._name)

class TriggerableBucket(object):
    """ TriggerableBucket is a user-defined storage bucket that can also be used to trigger workflows upon data changes
    """

    def __init__(self,client,bname,bassociated_workflows=[],bmetadatalist=[]):
        self.client=client
        self._name=bname
        self._update(bassociated_workflows,bmetadatalist)

    def _update(self,bassociated_workflows,bmetadatalist):
        self._associated_workflows=bassociated_workflows
        self._metadata=bmetadatalist

    @property
    def associated_workflows(self):
        # TODO: decide whether to auto-fetch details when associated_workflows is accessed 
        return self._associated_workflows

    def associate_workflow(self, wf):
        self.client.bind_bucket(self._name,wf._name)

    def disassociate_workflow(self, wf):
        self.client.unbind_bucket(self._name,wf._name)
