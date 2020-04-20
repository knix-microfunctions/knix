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

import sys
import base64
import datetime
from zipfile import ZipFile
import logging

from .deprecated import deprecated


#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class Function(object):
    """ Function object represents a registered function, every method execution and property assignment triggers one or more calls to management functions
    """

    def __init__(self,client,function):
        self.client=client
        self.id=function["id"]
        self._runtime=function["runtime"]
        self._name=function["name"]
        self._modified=function["modified"]
        self._code=None
        self._metadata=None
        self._zip=None

    def __str__(self):
        return f"{self.id} ({self._name}, {self._runtime})"

    @property
    def name(self):
        # TODO: function name could be updated, but there's no management service call that would fetch the function's metadata only
        return self._name

    @name.setter
    def name(self,name):
        res = self.client.action('modifyFunction',{'function':{'id':self.id,'name':name,'runtime':self._runtime}})
        self._name = name

    @property
    def runtime(self):
        # TODO: function name could be updated, but there's no management service call that would fetch the function's metadata only
        return self._runtime

    @runtime.setter
    def runtime(self,runtime):
        res = self.client.action('modifyFunction',{'function':{'id':self.id,'name':self._name,'runtime':runtime}})
        self._runtime = runtime

    @property
    def modified(self):
        # TODO: function modification date could have been updated
        return self._modified

    @property
    def source(self):
        ret = dict()
        if self._code is None:
            res = self.client.action('getFunctionZipMetadata',{'function':{'id':self.id}})
            self._metadata = res['function']['metadata']
            chunks = res['function']['chunks']
            data = self.client.action('getFunctionCode',{'function':{'id':self.id}})
            self._code = base64.b64decode(data['function']['code']).decode()
            #print("Downloading and checking function zip: " + self._name)
            if chunks > 0: # download code
                self._zip = []
                for c in range(chunks):
                    data = self.client.action('getFunctionZip',{'function':{'id':self.id,'chunk':c}})
                    #print("Got chunk number: " + str(c+1) + "/" + str(chunks), end=' \r')
                    sys.stdout.flush()
                    self._zip.append(data['function']['code'])
                #print()
        ret['code'] = self._code
        if self._zip is not None:
            ret['zip'] = self._zip
            ret['metadata'] = self._metadata
        return ret

    @source.setter
    def source(self,g):
        if not self._code:
            self.source
        if not ('code' in g or 'zip' in g):
            raise Exception("Need dict of code and/or zip to update the function sources")
        if 'zip' in g:
            #if cmp(self._zip,g['zip']) == 0:
            if type(self._zip) == type(g['zip']) and ((self._zip > g['zip']) - (self._zip < g['zip'])) == 0:
                log.info("%s - %s - Not updating matching zip", self.client.user, self._name)
            else:
                newZip=True
                self._zip = g['zip']
                size=len(self._zip)
                print("Uploading function zip: " + self._name)
                for c in range(size):
                    data = self.client.action('uploadFunctionCode',{'function':{'id':self.id,'chunk':c,'code':self._zip[c],'format':'zip'}})
                    print(str(round((c+1)*100.0/size,2)) + " %", end=' \r')
                    sys.stdout.flush()
                print()
        if 'metadata' in g or 'zip' in g:
            if ('metadata' in g and self._metadata != g['metadata']) or ('zip' in g and len(self._zip) != len(g['zip'])):
                self._metadata = g['metadata']
                res = self.client.action('uploadFunctionZipMetadata',{'function':{'id':self.id,'chunks':len(self._zip),'metadata':self._metadata,'format':'zipMetadata'}})
            else:
                log.info("%s - %s - Not updating matching metadata", self.client.user, self._name)
        if 'code' in g:
            if self._code == g['code']:
                log.info("%s - %s - Not updating matching code", self.client.user, self._name)
            else:
                self._code = g['code']
                code = self._code
                if isinstance(code, str):
                    code = code.encode()
                data = self.client.action('uploadFunctionCode',{'function':{'id':self.id,'code':base64.b64encode(code).decode(),'format':"text"}})

    @property
    def code(self):
        return self.source['code']

    @code.setter
    def code(self,code):
        self.source = {'code':code}

    def upload(self,filename):
        src = self.source
        chunks=[]
        with open(filename, 'rb') as zf:
            content = base64.b64encode(zf.read()).decode()
            for pos in range(0,len(content),1024*1024):
                chunks.append(content[pos:pos+1024*1024])
        # create metadata information on the ZIP file contents
        metadata = "Last uploaded Zip file: <b>%s</b><br><br><table border='1'>" % (filename.split('/')[-1])
        with ZipFile(filename, 'r') as zf:
            codefile = None
            for fn in zf.namelist():
                if fn.endswith(self._name+".py") and (codefile is None or len(fn) < len(codefile)):
                    codefile = fn

                try:
                    fi = zf.getinfo(fn)
                except KeyError:
                    log.error('ERROR: Did not find %s in zip file', fn)
                else:
                    metadata += "<tr>" \
                        "<td style='padding: 5px 5px 5px 5px;'>%s</td>" \
                        "<td style='padding: 5px 5px 5px 5px;'>%.2f kB</td>" \
                        "<td style='padding: 5px 5px 5px 5px;'>%s</td>" \
                        "</tr>" % (fn, fi.file_size/1024.0, datetime.datetime(*fi.date_time))
            if codefile is not None:
                log.info("Updating code with file '%s' from zip archive", codefile)
                with zf.open(codefile, 'r') as code:
                    sc = code.read()
                    src['code'] = sc
        metadata += "</table>"
        # upload the zip file
        src['zip'] = chunks
        src['metadata'] = base64.b64encode(metadata.encode()).decode()
        self.source = src

    @property
    def requirements(self):
        data = self.client.action('getFunctionRequirements',{'function':{'id':self.id}})
        reqs = data['function']['requirements'].replace(" ", "+")
        return base64.b64decode(reqs.encode()).decode()

    @requirements.setter
    def requirements(self,requirements):
        self.client.action('uploadFunctionRequirements',{
            'function':{
                'id':self.id,
                'requirements':base64.b64encode(requirements.encode()).decode()
            }
        })
