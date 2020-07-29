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
import os
import json
import time
import urllib.request, urllib.parse, urllib.error
from .function import Function
from .workflow import Workflow
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
        files = ['../settings.json','~/settings.json','./settings.json']
        if filename is not None:
            files.append(filename)
        for filename in files:
            """ get the json file """
            if os.path.isfile(filename):
                json_data = {}
                with open(filename) as json_file:
                    try:
                        json_data = json.load(json_file)
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
    def addGrain(self,name,runtime='Python 3.6'):
        return self.add_function(name,runtime)

    @deprecated(reason="Grains have been renamed to functions, use add_function(..) instead")
    def add_grain(self,name,runtime='Python 3.6'):
        return self.add_function(name, runtime)

    def add_function(self,name,runtime='Python 3.6'):
        """ add a function

        returns an existing function if the name exists, registers a new function name if it doesn't exist
        :name: name of the function
        """
        for f in self.functions:
            if f._name == name:
                return f
        data = self.action('addFunction',{'function':{'name':name,'runtime':runtime}})
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


    def add_workflow(self,name,filename=None):
        """ add a workflow

        returns an existing workflow if the name exists, registers a new workflow name if it doesn't exist
        :name: name of the workflow
        """
        for wf in self._workflows:
            if wf._name == name:
                return wf
        data = self.action('addWorkflow',{'workflow':{'name':name}})
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


    def keys(self, table="defaultTable", all_at_once=False):
        return self.list_keys(table=table, all_at_once=all_at_once)

    def keys(self,table="defaultTable"):
        start=0
        step=100
        while start >= 0:
            data_to_send = {}
            data_to_send["action"] = "performStorageAction"
            data = {}
            user = {}
            user["token"] = self.token
            data["user"] = user
            storage = {}
            storage["action"] = "listKeys"
            storage["table"] = table
            storage["start"] = start
            storage["count"] = step
            data["storage"] = storage
            data_to_send["data"] = data
            r = self._s.post(self.mgmturl,
                    params={},
                    json=data_to_send)
            r.raise_for_status()
            if r.json()["status"] == "success":
                keylist = r.json()["data"]["keylist"]
                for key in keylist:
                    yield key
                if len(keylist) < step:
                    break
                start += step
            else:
                raise Exception("LISTKEYS failed: " + r.json()["data"]["message"])

    def list_keys(self,table="defaultTable", start=0, count=2000):
        data_to_send = {}
        data_to_send["action"] = "performStorageAction"
        data = {}
        user = {}
        user["token"] = self.token
        data["user"] = user
        storage = {}
        storage["action"] = "listKeys"
        storage["table"] = table
        storage["start"] = start
        storage["count"] = count
        data["storage"] = storage
        data_to_send["data"] = data
        r = self._s.post(self.mgmturl,
                params={},
                json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("LISTKEYS failed: " + r.json()["data"]["message"])

        return r.json()["data"]["keylist"]


    def get(self,key,table="defaultTable"):
        data_to_send = {}
        data_to_send["action"] = "performStorageAction"
        data = {}
        user = {}
        user["token"] = self.token
        data["user"] = user
        storage = {}
        storage["action"] = "getdata"
        storage["table"] = table
        storage["key"] = key
        data["storage"] = storage
        data_to_send["data"] = data
        r = self._s.post(self.mgmturl,
                params={},
                json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] == "success":
            return r.json()["data"]["value"]
        else:
            raise Exception("GET failed: " + r.json()["data"]["message"])


    def put(self,key,value,table="defaultTable"):
        data_to_send = {}
        data_to_send["action"] = "performStorageAction"
        data = {}
        user = {}
        user["token"] = self.token
        data["user"] = user
        storage = {}
        storage["action"] = "putdata"
        storage["table"] = table
        storage["key"] = key
        storage["value"] = value
        data["storage"] = storage
        data_to_send["data"] = data
        r = self._s.post(self.mgmturl,
                params={},
                json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("PUT failed: " + r.json()["data"]["message"])


    def delete(self,key,table="defaultTable"):
        data_to_send = {}
        data_to_send["action"] = "performStorageAction"
        data = {}
        user = {}
        user["token"] = self.token
        data["user"] = user
        storage = {}
        storage["action"] = "deletedata"
        storage["table"] = table
        storage["key"] = key
        data["storage"] = storage
        data_to_send["data"] = data
        r = self._s.post(self.mgmturl,
                params={},
                json=data_to_send)
        r.raise_for_status()
        if r.json()["status"] != "success":
            raise Exception("DELETE failed: " + r.json()["data"]["message"])
