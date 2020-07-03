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


class Execution(object):
    """ Execution represents the execution of a workflow that can be referenced by its execution ID
    an execution object is returned from asynchronous workflow invocations
    """
    def __init__(self, client, url, exec_id):
        self.client=client
        self.url=url
        self.execution_id = exec_id

    def get(self, timeout=60):
        try:
            r = self.client._s.post(self.url,
                params = {"executionId": self.execution_id},
                timeout=timeout)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            raise Exception("Retrieving result of workflow from URL '"+self.url+"' failed due to "+type(e).__name__).with_traceback(sys.exc_info()[2])
        r.raise_for_status()
        return r.json()


class Workflow(object):
    """ Workflow represents a registered workflow, every method invocation or property assignment results in one or more calls to management functions
    """

    def __init__(self,client,wf):
        self.client=client
        self.id=wf["id"]
        self._name=wf["name"]
        self._modified=wf["modified"]
        self._status=wf.get("status",None)
        self._endpoints=wf.get("endpoints",None)

        self._deployment_error = ""
        self._json=None

    def __str__(self):
        if self._status == "deployed":
            return f"{self.id} ({self._name}, status: {self._status}, endpoints: {self._endpoints})"
        else:
            return f"{self.id} ({self._name}, status: {self._status})"

    @property
    def name(self):
        # TODO: workflow name could have been updated, decide if we should fetch workflow status
        return self._name

    @name.setter
    def name(self,name):
        res = self.client.action('modifyWorkflow',{'workflow':{'id':self.id,'name':name,'runtime':self._runtime}})
        self._name = name

    @property
    def modified(self):
        # TODO: workflow modification date could have been updated, decide if we should fetch workflow status
        return self._modified

    @property
    def status(self):
        data = self.client.action('getWorkflows',{'workflow':{'id':self.id}})
        self._status = data['workflow']['status']
        if self._status == "deployed":
            self._endpoints = data['workflow']['endpoints']
        else:
            self._endpoints = None
        if self._status == 'failed' and "deployment_error" in data['workflow']:
            self._deployment_error = data['workflow']['deployment_error']
        return self._status

    def get_deployment_error(self):
        return self._deployment_error

    @property
    def endpoint(self):
        if self.status == 'deployed':
            return random.choice(self._endpoints)
        else:
            return None

    @property
    def endpoints(self):
        if self.status == 'deployed':
            return self._endpoints
        else:
            return None

    @property
    def json(self):
        if not self._json:
            data = self.client.action('getWorkflowJSON',{'workflow':{'id':self.id}})
            self._json = base64.b64decode(data['workflow']['json']).decode().replace("\r","\n")
        return self._json


    @json.setter
    def json(self,json):
        if json != self.json:
            self._json = json
            self.client.action('uploadWorkflowJSON',{'workflow':{'id':self.id,'json':base64.b64encode(self._json.encode()).decode()}})


    def deploy(self, timeout=None):
        """ deploy a workflow and optionally wait in linearly increasing multiples of 1000ms
        :timeout: By default returns after calling deploy on the workflow without waiting for it to be actually deployed.
            If timeout is set to a numeric <= 0, it waits indefinitely in intervals of 1000ms, 2000ms, 3000ms, ...
            If timeout is set to a numeric > 0, it waits for the workflow to be deployed in increasing multiples of 100ms, but no longer than the timeout. When the timeout expires and the workflow is not deployed, the function raises an Exception
        """
        s = self.status
        if s == 'deployed':
            log.debug("deploy: wf %s already deployed",self.name)
            return
        elif s == 'deploying':
            log.debug("deploy: wf %s already being deployed",self.name)
        elif s == 'failed':
            log.debug("deploy: wf %s cannot be deployed", self.name)
            log.debug("deployment error: %s", self._deployment_error)
        else:
            self.client.action('deployWorkflow',{'workflow':{'id':self.id}})

        # if timeout is None, do not wait but return immediately even if it's not yet deployed
        if timeout is None:
            return

        sleep = 1
        if timeout > 0:
            # if timeout > 0, wait in increasing intervals but raise Exception if it's not deployed until the timeout expires
            t = time.time()
            end = t + timeout
            while t < end:
                s = self.status
                if s == 'deployed' or s == 'failed':
                    print()
                    return
                print("Waiting for deployment to come online; passed so far: " + str(round(t-end+timeout, 2)) + " seconds", end=" \r")
                sys.stdout.flush()
                t = time.time()
                if sleep < (end-t):
                    time.sleep(sleep)
                    sleep += 1
                else:
                    time.sleep(max(0,end-t))
            raise Exception("Deployment attempt timed out (%d)"%timeout)
        else:
            # if timeout <=0, wait in increasing intervals until deployed, even if this means forever
            while True:
                s = self.status
                if s == 'deployed' or s == 'failed':
                    return
                time.sleep(sleep)
                sleep += 1


    def undeploy(self, timeout=None):
        """ undeploy a workflow and optionally wait in linearly increasing multiples of 100ms
        :timeout: By default returns after calling undeploy on the workflow without waiting for it to be actually undeployed.
            If timeout is set to a numeric <= 0, it waits indefinitely in intervals of 100ms, 200ms, 300ms, ...
            If timeout is set to a numeric > 0, it waits for the workflow to be undeployed in increasing multiples of 100ms, but no longer than the timeout. When the timeout expires and the workflow is not undeployed, the function raises an Exception
        """
        if self.status == 'undeployed':
            log.debug("undeploy: wf %s not deployed",self.name)
            return
        if self.status == 'undeploying':
            log.debug("undeploy: wf %s is already being undeployed",self.name)
        else:
            self.client.action('undeployWorkflow',{'workflow':{'id':self.id}})

        # if timeout is None, do not wait but return immediately even if it's not yet deployed
        if timeout is None:
            return

        sleep = 1
        if timeout > 0:
            # if timout > 0, wait in increasing intervals but raise Exception if it's not undeployed until the timeout expires
            end = timeout + time.time()
            t = 0
            while t < end:
                if self.status == 'undeployed':
                    return
                t = time.time()
                if sleep < (end-t):
                    time.sleep(sleep)
                    sleep += 1
                else:
                    time.sleep(end-t)
            raise Exception("Deployment attempt timed out (%d)"%timeout)
        else:
            # if timeout <=0, wait in increasing intervals until undeployed, even if this means forever
            while True:
                if self.status == 'undeployed':
                    return
                time.sleep(sleep)
                sleep += 1

    def execute_async(self,data,timeout=30):
        """ execute a workflow asynchronously and returns an Execution object

        The function delivers an event to the frontend and returns an Execution object. Note that the timeout here applies to the delivery of the event, another timeout can be used when fetching the result with the Execution.get(timeout) method
        see Execution execute_async execute_async.get()

        :param data: the event dictionary passed to the workflow
        :type data: dict()
        :param timeout: time in seconds to wait for the event delivery to complete, otherwise throws ReadTimeout
        :type timeout: int
        :return: an Execution object to fetch the result
        :rtype: Execution
        :raises requests.exceptions.HTTPError: when the HTTP request to deliver the event fails
        :raises requests.exceptions.ConnectionError: when the platform can not be reached
        :raises requests.exceptions.ReadTimeout: when reading the HTTP result of delivering the event times out
        :raises ValueError: in case the response is not JSON
        """
        if self._status != "deployed":
            raise Exception("Workflow not deployed: " + self.name)

        # we are already deployed and have the endpoints stored in self._endpoints
        url = random.choice(self._endpoints)

        try:
            r = self.client._s.post(url,
                params={'async':'True'},
                json=data,
                allow_redirects=False,
                timeout=timeout)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            raise Exception("Asynchronous execution of workflow at URL '"+url+"' failed due to "+type(e).__name__)

        r.raise_for_status()
        exec_id = r.text
        return Execution(self.client, url, exec_id)

    def execute(self,data,timeout=60, check_duration=False):
        """ execute a workflow synchronously

        The function sends an event to the frontend and waits for the result in the HTTP response

        :param data: the event dictionary passed to the workflow
        :type data: dict()
        :param timeout: time in seconds to wait for the workflow to complete, otherwise throws ReadTimeout
        :type timeout: int
        :return: the result of the workflow execution
        :rtype: dict()

        :raises requests.exceptions.HTTPError: when the HTTP request to execute the workflow fails (e.g. 500 ServerError)
        :raises requests.exceptions.ConnectionError: when the platform can not be reached
        :raises requests.exceptions.ReadTimeout: when reading the HTTP response with the workflow result times out
        :raises ValueError: in case the response is not JSON
        """
        #if self.status != 'deployed':
        #    self.deploy(-1)
        if self._status != "deployed":
            raise Exception("Workflow not deployed: " + self.name)

        # we are already deployed and have the endpoints stored in self._endpoints
        url = random.choice(self._endpoints)
        try:
            #postdata = {}
            #postdata["value"] = json.dumps(data)
            #postdata = json.dumps(postdata)
            if check_duration:
                t_start = time.time()
            r = self.client._s.post(url,
                params={},
                json=data,
                #headers={'Content-Type':'application/json'},
                #data=postdata,
                #headers={'Content-Type':'application/x-www-form-urlencoded'},
                #data=postdata,
                timeout=timeout)
            if check_duration:
                t_total = (time.time() - t_start) * 1000.0
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            raise Exception("Execution of workflow '"+self.name+"' at URL '"+url+"' failed due to "+type(e).__name__)
        r.raise_for_status()
        if check_duration:
            return r.json(), t_total
        return r.json()


    def logs(self, clear=False, ts_earliest=0.0, num_lines=500):
        """ fetch logs of this workflow
        :clear: default=False; if True, the function calls delete_logs() before returning
        :returns: a dict {'exceptions':<str>,'progress':<str>,'log':<str>}
        """
        #print("earliest: " + str(ts_earliest))
        data = self.client.action('retrieveAllWorkflowLogs',{'workflow':{'id':self.id, 'ts_earliest': ts_earliest, 'num_lines': num_lines}})
        res = {'exceptions':base64.b64decode(data['workflow']['exceptions']).decode(),
               'progress':base64.b64decode(data['workflow']['progress']).decode(),
               'log':base64.b64decode(data['workflow']['log']).decode(),
                'timestamp': data['workflow']['timestamp']}
        if clear:
            self.delete_logs()
        return res


    def delete_logs(self):
        """ delete logs of this workflow """
        return
        #try:
        #    self.client.action('clearAllWorkflowLogs',{'workflow':{'id':self.id}})
        #except requests.exceptions.HTTPError as e:
        #    e.strerror += "while trying to clearAllWorkflowLogs for wf '"+self.name+"'/"+self.id
        #    raise e


    def get_functions(self):
        fnames = []
        wfjson = json.loads(self.json)
        if 'States' in wfjson:
            for sname,state in list(wfjson['States'].items()):
                if 'Resource' in state:
                    fnames.append(state['Resource'])
        elif 'grains' in wfjson:
            for gdict in wfjson['grains']:
                fnames.append(gdict['name'])
        functions = []
        for f in self.client.functions:
            if f._name in fnames:
                functions.append(f)
                fnames.remove(f.name)
        if len(fnames) > 0:
            log.warn("Could not find all functions of workflow %s, missing %s"%(self.name,str(fnames)))
        return functions
