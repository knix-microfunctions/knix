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

import base64
import requests
import os
import json
import time
import urllib.request, urllib.parse, urllib.error
from .function import Function
from .workflow import Workflow
from .storage import Storage,TriggerableBucket
from .trigger import Trigger
import logging
logging.basicConfig()
#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


import warnings
def deprecated(reason=""):
    def deprecator(func):
        def wrapper(*args,**kwargs):
            print("Use of deprecated func "+func.__name__+" - "+reason)
            return func(*args,**kwargs)
        return wrapper
    return deprecator

        #warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        #warnings.warn("Call to deprecated function {}. {}".format(func.__name__, reason),
        #              category=DeprecationWarning,
        #              stacklevel=2)
        #warnings.simplefilter('default', DeprecationWarning)  # reset filter


class MfnClient(object):
    """ MfnClient is a client to the MicroFunctions frontend
    The client communicates with management functions (e.g. authenticate, CRUD functions and workflows, deploy workflows, fetch logs).
    It provides workflow and function objects to modify them (e.g. upload ZIP, modify code, fetch logs).
    """


    @classmethod
    def _proxies(cls):
        proxies=dict()
        if 'HTTP_PROXY' in os.environ:
            log.info("Found environment variable HTTP_PROXY")
            proxies['http']=os.environ['HTTP_PROXY']
        if 'http_proxy' in os.environ:
            log.info("Found environment variable http_proxy")
            proxies['http']=os.environ['http_proxy']
        if 'HTTPS_PROXY' in os.environ:
            log.info("Found environment variable HTTPS_PROXY")
            proxies['https']=os.environ['HTTPS_PROXY']
        if 'https_proxy' in os.environ:
            log.info("Found environment variable https_proxy")
            proxies['https']=os.environ['https_proxy']

        if len(proxies) == 0:
            proxies = None
        return proxies


    @classmethod
    def load_env(cls, config=dict()):
        """ Creates a MfnClient config from environment variable

        :MFN_URL: MicroFunctions URL in the form http[s]://<hostname>/
        :MFN_USER: MicroFunctions username, typically an email address
        :MFN_PASSWORD: password authenticating the user
        :MFN_NAME: optional user name to register the user if it doesn't exist
        """
        if 'MFN_NODE' in os.environ and not 'MFN_URL' in os.environ:
            raise NotImplementedError("Use of MFN_NODE is deprecated, please change to MFN_URL")

        if 'MFN_URL' in os.environ:
            config['mfn_url'] = os.environ['MFN_URL']
            log.info("Found environment variable MFN_URL="+os.environ['MFN_URL'])
        if 'MFN_USER' in os.environ:
            config['mfn_user'] = os.environ['MFN_USER']
            log.info("Found environment variable MFN_USER="+os.environ['MFN_USER'])
        if 'MFN_NAME' in os.environ:
            config['mfn_name'] = os.environ['MFN_NAME']
            log.info("Found environment variable MFN_NAME="+os.environ['MFN_NAME'])
        if 'MFN_PASSWORD' in os.environ:
            config['mfn_password'] = os.environ['MFN_PASSWORD']
            log.info("Found environment variable MFN_PASSWORD")
        if 'proxies' not in config:
            config['proxies'] = cls._proxies()
        return config


    @classmethod
    def load_json(cls, config=dict(), filename=None):
        files = ['../settings.json','~/settings.json','~/.mfn/config.json','./settings.json']
        if filename is not None:
            files.append(filename)
        for filename in files:
            """ get the json file """
            if filename.startswith("~"):
                filename = os.path.expanduser(filename)
            if os.path.isfile(filename):
                json_data = {}
                with open(filename,"r") as json_file:
                    try:
                        filecontent = json_file.read()
                        if len(filecontent) == 0:
                            continue
                        json_data = json.loads(filecontent)
                        log.info("Using settings file", filename)
                        config.update(json_data)
                    except Exception:
                        log.error("Could not load json from settings file "+filename)
                        raise
        return config


    def __init__(self,mfn_url=None,mfn_user=None,mfn_password=None,mfn_name=None,proxies=None):
        """ creates a MfnClient and requires parameters to connect and authenticate with the management functions

        :url: URL (protocol+host) of the MicroFunctions server, e.g. https://microfunctions.org
        :user: username, typically the email address, of the user, e.g. test@test.com
        :password: password (plaintext) string authenticating the user
        :name: optional name of the user to have it created (registered) if it doesn't exist
        :proxies: a dict in the form {'http':'http://<proxyaddress>:<proxyport>','https':'http://<proxyhost>:<proxyport>'}

        tries to load the parameters from config files/environment variables if not given
        """
        config = MfnClient.load_json()
        config = MfnClient.load_env(config)
        url = mfn_url or config.get('mfn_url')
        if url is None:
            print("No valid configuration found")
            log.warn("Known configuration data:" + str(config))
            exit(2)
        user = mfn_user or config.get('mfn_user')
        password = mfn_password or config.get('mfn_password')
        name = mfn_name or config.get('mfn_name',None)
        proxies = proxies or config.get('proxies',None)
        if not url.startswith('http'):
            log.warning("WARNING: please use a format 'http://<hostname>:<port>' or 'https://...' for the url")
            if url.endswith(':443'):
                url = 'https://'+url
            else:
                url = 'http://'+url
            log.warning("... adjusted url to "+url)
            time.sleep(1)
        if url.endswith("/"):
            url = url[:-1]
        log.info(f"Connecting as {user} to {url}")
        self._s = requests.Session()
        if proxies:
            self._s.proxies.update(proxies)
        self._s.verify=False
        self._s.max_redirects = 10

        self.baseurl = str(url)
        self.mgmturl= self.baseurl.rstrip("/")+"/management"
        self.user=user
        self.token=None
        self.store=""
        self.name=name
        self.password=password
        self._functions=[]
        self._workflows=[]
        self._triggers={}
        self._buckets={}
        try:
            self.login()
        except requests.exceptions.HTTPError as e:
            log.error(str(e))
            raise Exception("Error reaching "+self.mgmturl+". Aborting")
        except:
            if self.name:
                log.info("Error logging in, trying to sign up for %s (%s)", self.name, self.user)
                userinfo = {}
                userinfo["email"] = self.user
                userinfo["password"] = self.password
                userinfo["name"] = self.name
                data_to_send = {}
                data_to_send["action"] = "signUp"
                data_to_send["data"] = {}
                data_to_send["data"]["user"] = userinfo
                #postdata = {}
                #postdata["value"] = json.dumps(data_to_send)

                #postdata = json.dumps(postdata)

                signUp = self._s.post(self.mgmturl,#verify=False,
                        params={},
                        json=data_to_send)
                        #headers={'Content-Type':'application/json'},
                        #data=postdata)
                try:
                    signUp.raise_for_status()
                    resp = signUp.json()
                    if resp['status'] != 'success':
                        raise Exception("Error signing up with "+self.mgmturl)
                    log.debug("Client signed up")
                    self.login()
                except requests.exceptions.HTTPError as e:
                    log.error(str(e))
                    raise Exception("Error signing up with "+self.mgmturl)
            else:
                raise Exception("Error logging in at "+self.mgmturl+". Maybe check credentials?")
        log.debug("Client %s obtained token %s",self.user,self.token)

    def disconnect(self):
        if self._s is not None:
            self._s.close()

    def version(self):
        data = self.action('version')
        return data.get('message','')

    def login(self):
        userinfo = {}
        userinfo["email"] = self.user
        userinfo["password"] = self.password
        data_to_send = {}
        data_to_send["action"] = "logIn"
        data_to_send["data"] = {}
        data_to_send["data"]["user"] = userinfo

        #postdata = {}
        #postdata["value"] = json.dumps(data_to_send)

        #postdata = json.dumps(postdata)

        r = self._s.post(self.mgmturl,
                    params={},
                    json=data_to_send)
                    #headers={'Content-Type':'application/json'},
                    #data=postdata)
        r.raise_for_status()
        resp = r.json()
        if resp['status'] == 'success':
            self.token = resp['data']['token']
            self.store = self.baseurl+resp['data']['storageEndpoint']
            self._storage = Storage(self._s, self.token, self.mgmturl)
        else:
            raise Exception("Error logging in at "+self.mgmturl)


    def delete_user(self):
        data = {}
        data["user"] = {}
        data["user"]["token"] = self.token

        self.action("deleteAccount", data)

    def action(self,action,data=None):
        if data is None:
            data = dict()
        if 'user' not in data:
            data['user'] = {'token':self.token}
        log.debug("%s: %s -> %s", self.user, action, str(data)[:256]+(str(data)[256:] and '...'))
        data_to_send = {}
        data_to_send["action"] = action
        data_to_send["data"] = data
        #postdata = {}
        #postdata["value"] = json.dumps(data_to_send)
        #postdata = json.dumps(postdata)
        r = self._s.post(self.mgmturl,#verify=False,
                    params={},
                    json=data_to_send)
                    #headers={'Content-Type':'application/json'},
                    #data=postdata)
        r.raise_for_status()
        log.debug("%s: %s <- %s", self.user, action, r.text[:256]+(r.text[256:] and '...'))
        resp = r.json()
        if resp.get('status','') != 'success':
            if resp.get('has_error',False):
                raise Exception(f"MicroFunctions Error for action {action}: {resp['error_type']}")
            elif resp.get('data', None):
                raise Exception(f"MicroFunctions Error for action {action}: {resp['data']['message']}")
            else:
                raise Exception(f"MicroFunctions Error for action {action}: {r.text}")
        return resp['data']

    @property
    def grains(self):
        print("Use of deprecated property grains - Grains have been renamed to functions, use client.functions instead")
        return self.functions

    @property
    def functions(self):
        data = self.action('getFunctions')
        newset = []
        for f in data['functions']:
            found=None
            for old in self._functions:
                if f['id'] == old.id:
                    found=old
            if found is None:
                newset.append(Function(self,f))
            else:
                found._name = f['name']
                found._modified = f['modified']
                newset.append(found)
        #del self._functions
        self._functions = newset
        return self._functions


    @deprecated(reason="Grains have been renamed to functions, use find_function(..) instead")
    def findGrain(self,name):
        return self.find_function(name)

    @deprecated(reason="Grains have been renamed to functions, use find_function(..) instead")
    def find_grain(self,name):
        return self.find_function(name)

    def find_function(self,name):
        res = []
        for f in self.functions:
            if f._name == name:
                return f
            if f._name.startswith(name):
                res.append(f)
        # If nothing was found, try function IDs
        if len(res) == 0:
            for f in self._functions:
                if f.id == name:
                    return f
                if f.id.startswith(name):
                    res.append(f)
        if len(res) == 0:
            raise Exception("Could not find function matching "+name)
        else:
            if(len(res) > 1):
                log.warning("Found multiple functions for search word "+name+", returning first result")
            return res[0]

    @deprecated(reason="Grains have been renamed to functions, use add_function(..) instead")
    def addGrain(self,name,runtime='Python 3.6',gpu_usage="0.",gpu_mem_usage="0."):
        return self.add_function(name,runtime,gpu_usage,gpu_mem_usage)

    @deprecated(reason="Grains have been renamed to functions, use add_function(..) instead")
    def add_grain(self,name,runtime='Python 3.6',gpu_usage="0.",gpu_mem_usage="0."):
        return self.add_function(name, runtime, gpu_usage,gpu_mem_usage)

    def add_function(self,name,runtime='Python 3.6',gpu_usage="0.",gpu_mem_usage="0."):
        """ add a function

        returns an existing function if the name exists, registers a new function name if it doesn't exist
        :name: name of the function
        """
        for f in self.functions:
            if f._name == name:
                return f
        data = self.action('addFunction',{'function':{'name':name,'runtime':runtime, 'gpu_usage': gpu_usage, 'gpu_mem_usage': gpu_mem_usage}})
        gd = data['function']
        f = Function(self,gd)
        self._functions.append(f)
        return f


    @deprecated(reason="Grains have been renamed to functions, use delete_function(..) instead")
    def delGrain(self,g):
        return self.delete_function(g)

    @deprecated(reason="Grains have been renamed to functions, use delete_function(..) instead")
    def delete_grain(self,g):
        return self.delete_function(g)

    def delete_function(self,function):
        self._functions.remove(function)
        self.action('deleteFunction',{'function':{'id':function.id}})


    @property
    def workflows(self):
        data = self.action('getWorkflows')
        newset = []
        for wf in data['workflows']:
            found=None
            for old in self._workflows:
                if wf['id'] == old.id:
                    found=old
            if found is None:
                newset.append(Workflow(self,wf))
            else:
                newset.append(found)
        #del self._workflows
        self._workflows = newset
        return self._workflows


    @deprecated(reason="method name doesn't conform to PEP-8, use add_workflow(..) instead")
    def addWorkflow(self,name):
        return self.add_workflow(name)


    @deprecated(reason="method name doesn't conform to PEP-8, use delete_workflow(..) instead")
    def delWorkflow(self,wf):
        return self.delete_workflow(wf)

    def find_workflow(self,name):
        res = []
        for wf in self.workflows:
            if wf._name == name:
                return wf
            elif wf._name.startswith(name):
                res.append(wf)
        # If nothing was found, try workflow IDs
        if len(res) == 0:
            for wf in self.workflows:
                if wf.id == name:
                    return wf
                if wf.id.startswith(name):
                    res.append(wf)
        if len(res) == 0:
            raise Exception("Could not find workflow matching "+name)
        else:
            if(len(res) > 1):
                log.warning("Found multiple workflows for search word "+name+", returning first result")
            return res[0]


    def _get_state_names_and_resource(self, desired_state_type, wf_dict):
        state_list = []
        states = wf_dict['States']
        for state_name in states:
            state = states[state_name]
            state_type = state['Type']
            resource = ''
            if 'Resource' in state:
                resource = state['Resource']
            should_append = False
            if desired_state_type == 'all':
                should_append = True
            elif state_type == desired_state_type:
                should_append = True
            else:
                pass

            if should_append == True:
                state_list.append((state_type, state_name, resource))

            if state_type == 'Parallel':
                branches = state['Branches']
                for branch in branches:
                    parallel_state_list = self._get_state_names_and_resource(desired_state_type, branch)
                    state_list = state_list + parallel_state_list

            if state_type == 'Map':
                branch = state['Iterator']
                map_state_list = self._get_state_names_and_resource(desired_state_type, branch)
                state_list = state_list + map_state_list

        return state_list


    def add_workflow(self,name,filename=None, gpu_usage=None, gpu_mem_usage=None):
        """ add a workflow

        returns an existing workflow if the name exists, registers a new workflow name if it doesn't exist
        :name: name of the workflow
        """
        for wf in self._workflows:
            if wf._name == name:
                return wf
        data = self.action('addWorkflow',{'workflow':{'name':name, "gpu_usage":gpu_usage, "gpu_mem_usage":gpu_mem_usage}})
        wfd = data['workflow']
        wf = Workflow(self,wfd)
        self._workflows.append(wf)

        if filename is not None:
            wfdesc = ""
            with open(filename,'r') as f:
                wfdesc = f.read()
            wfdir = os.path.dirname(os.path.abspath(filename))

            # set the WF json
            wf.json = wfdesc

            # parse the WF json to find required functions
            fnames = []
            wfjson = json.loads(wfdesc)
            if 'States' in wfjson:
                state_list = self._get_state_names_and_resource('Task', wfjson)
                for state_info in state_list:
                    #state_type = state_info[0]
                    #state_name = state_info[1]
                    state_resource = state_info[2]
                    fnames.append(state_resource)
            elif 'functions' in wfjson:
                for fdict in wfjson['functions']:
                    fnames.append(fdict['name'])

            for fname in fnames:
                fzipname = wfdir+"/%s.zip" % fname
                fpyname = wfdir+"/%s.py" % fname
                if not (os.path.exists(fzipname) or os.path.exists(fpyname)):
                    log.warn("Neither the ZIP file %s nor the source code %s was found for function %s" % (fzipname,fpyname,fname))

                log.info("Adding function: " + fname)

                f = self.add_function(fname)

                # Upload the .zip file
                if os.path.exists(fzipname):
                    f.upload(fzipname)

                # Upload the source code from the .py file
                if os.path.exists(fpyname):
                    with open(fpyname, 'r') as f:
                        fcode = f.read()
                    f.code = fcode
        return wf


    def delete_workflow(self,wf):
        if wf.status == 'deployed':
            wf.undeploy(0)
        if wf in self._workflows:
            self._workflows.remove(wf)
        self.action('deleteWorkflow',{'workflow':{'id':wf.id}})


    # Storage operations

    def _list_stepwise(self, data_type, wid=None):
        start=0
        step=100
        while start >= 0:
            if data_type == "keys":
                resultlist = self.list_keys(start, step, wid)
            elif data_type == "maps":
                resultlist = self.list_maps(start, step, wid)
            elif data_type == "sets":
                resultlist = self.list_sets(start, step, wid)
            elif data_type == "counters":
                resultlist = self.list_counters(start, step, wid)

            for result in resultlist:
                yield result
            if len(resultlist) < step:
                break
            start += step
        else:
            raise Exception("LIST" + data_type.upper() + " failed: " + r.json()["data"]["message"])

    # kv operations
    def get(self, key, wid=None):
        return self._storage.get(key, wid)

    def put(self, key, value, wid=None):
        self._storage.put(key, value, wid)

    def delete(self, key, wid=None):
        self._storage.delete(key, wid)

    def list_keys(self, start=0, count=2000, wid=None):
        return self._storage.list_keys(start, count, wid)

    def keys(self, wid=None):
        self._list_stepwise("keys", wid)

    # map operations
    def create_map(self, mapname, wid=None):
        self._storage.create_map(mapname, wid)

    def put_map_entry(self, mapname, key, value, wid=None):
        self._storage.put_map_entry(mapname, key, value, wid)

    def get_map_entry(self, mapname, key, wid=None):
        return self._storage.get_map_entry(mapname, key, wid)

    def delete_map_entry(self, mapname, key, wid=None):
        self._storage.delete_map_entry(mapname, key, wid)

    def retrieve_map(self, mapname, wid=None):
        return self._storage.retrieve_map(mapname, wid)

    def contains_map_key(self, mapname, key, wid=None):
        return self._storage.contains_map_key(mapname, key, wid)

    def get_map_keys(self, mapname, wid=None):
        return self._storage.get_map_keys(mapname, wid)

    def clear_map(self, mapname, wid=None):
        self._storage.clear_map(mapname, wid)

    def delete_map(self, mapname, wid=None):
        self._storage.delete_map(mapname)

    def list_maps(self, start=0, count=2000, wid=None):
        return self._storage.list_maps(start, count, wid)

    def maps(self, wid=None):
        self._list_stepwise("maps", wid)

    # set operations
    def create_set(self, setname, wid=None):
        self._storage.create_set(setname, wid)

    def add_set_entry(self, setname, item, wid=None):
        self._storage.add_set_entry(setname, item, wid)

    def remove_set_entry(self, setname, item, wid=None):
        self._storage.remove_set_entry(setname, item, wid)

    def contains_set_item(self, setname, item, wid=None):
        return self._storage.contains_set_item(setname, item, wid)

    def retrieve_set(self, setname, wid=None):
        return self._storage.retrieve_set(setname, wid)

    def clear_set(self, setname, wid=None):
        self._storage.clear_set(setname, wid)

    def delete_set(self, setname, wid=None):
        self._storage.delete_set(setname)

    def list_sets(self, start=0, count=2000, wid=None):
        return self._storage.list_sets(start, count, wid)

    def sets(self, wid=None):
        self._list_stepwise("sets", wid)

    # counter operations
    def create_counter(self, countername, countervalue, wid=None):
        self._storage.create_counter(countername, countervalue, wid)

    def get_counter(self, countername, wid=None):
        return self._storage.get_counter(countername, wid)

    def increment_counter(self, countername, increment, wid=None):
        self._storage.increment_counter(countername, increment, wid)

    def decrement_counter(self, countername, decrement, wid=None):
        self._storage.decrement_counter(countername, decrement, wid)

    def delete_counter(self, countername, wid=None):
        self._storage.delete_counter(countername, wid)

    def list_counters(self, start=0, count=2000, wid=None):
        return self._storage.list_counters(start, count, wid)

    def counters(self, wid=None):
        self._list_stepwise("counters", wid)

    ### Triggers
    @property
    def triggers(self):
        data = self.action('getTriggerDetails',{'trigger_names':[]})
        unseen = list(self._triggers.keys())
        for tname,tdetails in data['trigger_details'].items():
            if tname in self._triggers:
                self._triggers[tname].update(tdetails)
                unseen.remove(tname)
            else:
                self._triggers[tname] = Trigger(self,tname,tdetails)
        for tname in unseen:
            del self._triggers[tname]
        return self._triggers

    def add_trigger(self,name,config):
        """ add a trigger

        requires a name and a trigger configuration, raises an error if it already exists, creates a new trigger if it doesn't exist and returns the new Trigger object

        :name: name of the trigger
        :config: trigger configuration (trigger_info)
        """
        if name in self.triggers.keys():
            return self.triggers[name]
        try:
            data = self.action('addTrigger',{'trigger_name':name,'trigger_info':config})
            ts = self.get_triggers([name])
            if len(ts) == 0:
                raise Exception("Trigger '"+name+"' was just created but not found")
            self.triggers[name] = ts[0]
        except Exception as e:
            raise e

    def get_triggers(self,names):
        """ fetch trigger details for specific triggers

        requires a non-empty list of trigger names to fetch, returns an array of triggers found for the given names
        :names: list of names to fetch
        """
        try:
            data = self.action('getTriggerDetails',{'trigger_names':names})
            for tname, tdata in data["trigger_details"].items():
                self._triggers[tname] = Trigger(self, tname, tdata)
        except Exception as e:
            raise e

    def find_trigger(self,name):
        res = []
        for n,t in self.triggers.items():
            if n == name:
                return t
            elif n.startswith(name):
                res.append(t)
        if len(res) == 0:
            raise Exception("Could not find trigger matching "+name)
        else:
            if(len(res) > 1):
                log.warning("Found multiple triggers for search word "+name+", returning first result")
            return res[0]

    def bind_trigger(self,trigger_name,workflow_name):
        """ binds a workflow to a trigger

        Bind a workflow to a trigger (aka 'associate' a workflow with a trigger)
        raises Exception if not successful 
        :trigger_name: name of the trigger (immutable)
        :workflow_name: name of the workflow as which it has been bound
        """
        try:
            self.action('addTriggerForWorkflow',{'trigger_name':trigger_name,'workflow_name':workflow_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to bind workflow '"+workflow_name+"' to trigger '"+trigger_name+"'"
            raise e
    
    def unbind_trigger(self,trigger_name,workflow_name):
        """ unbinds a workflow from a trigger
        Unbind a workflow from a trigger (aka 'disassociate' a workflow from a trigger)
        raises Exception if not successful 
        :trigger_name: name of the trigger (immutable)
        :workflow_name: name of the workflow as which it has been bound
        """
        try:
            self.action('deleteTriggerForWorkflow',{'trigger_name':trigger_name,'workflow_name':workflow_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to unbind workflow '"+workflow_name+"' from trigger '"+trigger_name+"'"
            raise e

    def delete_trigger(self,trigger_name):
        """ deletes a trigger

        Delete a trigger (automatically diassociates all bound workflows)
        :trigger_name: name of the trigger (immutable)
        """
        try:
            self.action('deleteTrigger',{'trigger_name':trigger_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to delete trigger '"+trigger_name+"'"
            raise e


    ### Buckets
    @property
    def buckets(self):
        data = self.action('getTriggerableBuckets')
        unseen = list(self._buckets.keys())
        for bname,bworkflows in data['buckets'].items():
            bmetadatalist = data['buckets_details'].get(bname,[])
            if bname in self._buckets:
                self._buckets[bname]._update(bworkflows, bmetadatalist)
                unseen.remove(bname)
            else:
                self._buckets[bname] = TriggerableBucket(self,bname,bworkflows,bmetadatalist)
        for bname in unseen:
            del self._buckets[name]
        return self._buckets

    def find_bucket(self,name):
        res = []
        for n,b in self.buckets.items():
            if n == name:
                return b
            elif n.startswith(name):
                res.append(b)
        if len(res) == 0:
            raise Exception("Could not find bucket matching "+name)
        else:
            if(len(res) > 1):
                log.warning("Found multiple buckets for search word "+name+", returning first result")
            return res[0]

    def add_bucket(self,bname):
        """ add a bucket

        requires a name, creates a new bucket if it doesn't exist and returns the new Trigger object

        :name: name of the trigger
        :config: trigger configuration (trigger_info)
        """
        if bname in self._buckets:
            return self._buckets[bname] 
        try:
            data = self.action('addTriggerableBucket',{'bucketname':bname})
            self._buckets[bname] = TriggerableBucket(self, bname)
            return self._buckets[bname] 
        except Exception as e:
            raise e

    def bind_bucket(self,bucket_name,workflow_name):
        """ binds a workflow to a bucket

        Bind a workflow to a bucket (aka 'associate' a workflow with a bucket)
        raises Exception if not successful 
        :bucket_name: name of the bucket
        :workflow_name: name of the workflow as which it has been bound
        """
        try:
            self.action('addStorageTriggerForWorkflow',{'bucketname':bucket_name,'workflowname':workflow_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to bind workflow '"+workflow_name+"' to bucket '"+bucket_name+"'"
            raise e
    
    def unbind_bucket(self,bucket_name,workflow_name):
        """ unbinds a workflow from a bucket
        Unbind a workflow from a bucket (aka 'disassociate' a workflow from a bucket)
        raises Exception if not successful 
        :bucket_name: name of the bucket
        :workflow_name: name of the workflow as which it has been bound
        """
        try:
            self.action('deleteStorageTriggerForWorkflow',{'tablename':bucket_name,'workflowname':workflow_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to unbind workflow '"+workflow_name+"' from bucket '"+bucket_name+"'"
            raise e

    def delete_bucket(self,bucket_name):
        """ deletes a bucket

        Delete a bucket (automatically diassociates all bound workflows)
        :bucket_name: name of the bucket
        """
        try:
            self.action('deleteTriggerableBucket',{'bucketname':bucket_name})
        except requests.exceptions.HTTPError as e:
            e.strerror += "while trying to delete bucket '"+bucket_name+"'"
            raise e
