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

import click
import collections
import datetime
import getpass
import json
import logging
import os
import stat
import sys
import tempfile
import traceback
from . import __version__
from mfn_sdk import MfnClient
logging.basicConfig(format="%(message)s")
log = logging.getLogger()

class Aliased(click.Group):
    aliases = {
        'wfs': 'workflows',
        'wf': 'workflow',
        'fns': 'functions',
        'fn': 'function'
    }

    def __init__(self, name=None, commands=None, **attrs):
        super(Aliased, self).__init__(name, commands, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or collections.OrderedDict()

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        if cmd_name in Aliased.aliases:
            return click.Group.get_command(self, ctx, Aliased.aliases[cmd_name])
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))

    def list_commands(self, ctx):
        return self.commands

class Config(dict):
    configfile = None
    f = None

    def __init__(self, filename):
        self.configfile = filename
        try:
            self.f = open(self.configfile,"r")
            args = json.load(self.f)
            self.f.close()
        except FileNotFoundError:
            self.f = open(self.configfile,"a")
            os.chmod(self.configfile, stat.S_IWRITE | stat.S_IREAD)
            self.f.close()
            args = {}
        self.f = open(self.configfile,"w")
        dict.__init__(self, args)

    def __setattr__(self,name,value):
        if hasattr(Config,name):
            super().__setattr__(name, value)
        else:
            self[name] = value

    def __delattr__(self,name):
        if hasattr(Config,name):
            super().__delattr__(name)
        else:
            del self[name]

    def __getattr__(self,name):
        if hasattr(Config,name):
            super().__getattr__(name)
        else:
            return self.get(name,None)

    def __del__(self):
        json.dump(self,self.f)
        self.f.close()

    def get_client(self):
        if not (self.mfn_url and self.mfn_user and self.mfn_password):
            print("Please login")
            sys.exit(2)
        else:
            return MfnClient(self.mfn_url,self.mfn_user,self.mfn_password,self.mfn_name,self.proxies)

pass_config = click.make_pass_decorator(Config)

class Resource(click.Command):
    def __json__(self):
        return json.dumps(self.data)

pass_resource = click.make_pass_decorator(Resource)


@click.command(cls=Aliased,context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-q', count=True, help='Quiet, (Log level -q: ERROR, -qq: no output).')
@click.option('-v', count=True, help='Verbose, reduces log levels (-v: INFO, -vv: DEBUG).')
@click.version_option(__version__)
@click.pass_context
def cli(ctx, q, v):
    directory = os.path.realpath(os.environ["HOME"])+"/.mfn"
    if not os.path.exists(directory):
        os.makedirs(directory)
    ctx.obj = Config(directory+"/config.json")
    lvl = max(1, 30 - (10*v) + (10*q) )
    logging.basicConfig(level=lvl)
    log.setLevel(max(1,lvl))

@cli.command()
@pass_config
def version(config):
    """Show software versions used"""
    print("mfn_cli "+__version__)
    from mfn_sdk import __version__ as sdkversion
    print("mfn_sdk "+sdkversion)
    client = config.get_client()
    try:
        print("management service "+client.version())
    except Exception as e:
        log.error(e)

@cli.command()
@click.option('--url', help='URL host to connect to')
@click.option('--user', help='username, e.g. test@example.com')
@click.option('--name', help='account name (required to auto-create an account)')
@click.option('--password', help='user password')
@pass_config
def login(config, url=None, user=None, name=None, password=None):
    """Log in to your MicroFunctions platform"""
    default = MfnClient.load_json()
    default = MfnClient.load_env(default)

    # sanitize input
    if url and not url.startswith('http'):
        print("WARNING: please use a format 'http://<hostname>:<port>' or 'https://...' for the url")
        if url.endswith(':443'):
            url = 'https://'+url
        else:
            url = 'http://'+url

    # overwrite values if provided
    config.mfn_url = url or config.mfn_url or default.get('mfn_url', 'https://knix.io')
    config.mfn_user = user or config.mfn_user or default.get('mfn_user')
    config.mfn_name = name or config.mfn_name or default.get('mfn_name')
    config.mfn_password = password or config.mfn_password or default.get('mfn_password')
    if config.mfn_user is None:
        config.mfn_user = click.prompt(f"Enter username for {config.mfn_url}")
    if config.mfn_password is None:
        config.mfn_password = getpass.getpass(f"Enter password for {config.mfn_user}: ")
    config.proxies = default.get('proxies', None)
    if config.proxies is None:
        proxies=dict()
        if 'http_proxy' in os.environ:
            config.proxies['http'] = os.environ['http_proxy']
        elif 'HTTP_PROXY' in os.environ:
            config.proxies['http'] = os.environ['HTTP_PROXY']
        if 'https_proxy' in os.environ:
            config.proxies['https'] = os.environ['https_proxy']
        elif 'HTTPS_PROXY' in os.environ:
            config.proxies['https'] = os.environ['HTTPS_PROXY']
        if len(proxies) > 0:
            config.proxies = proxies
    try:
        client = config.get_client()
        print(f"Successfully logged into {config.mfn_url} as user {config.mfn_user}!")
        return client
    except Exception as e:
        config.mfn_password = None
        print(str(e))


@cli.command()
@click.argument('workflow')
@click.argument('data', nargs=-1, type=click.UNPROCESSED, required=False)
@pass_config
def invoke(config, workflow, data=None):
    """Invoke a workflow.

    DATA can be any string
    """
    client = config.get_client()
    try:
        wf = client.find_workflow(str(workflow.strip()))
        click.echo(wf.execute(' '.join(data)))
    except Exception as e:
        log.error(e)


@cli.command()
@click.argument('workflow')
@click.option('--timeout', '-t', help='Time to wait for the workflow to be deployed (optional, waits indefinitely if set to <= 0)')
@pass_config
def deploy(config, workflow=None, timeout=None):
    """Deploy a workflow"""
    client = config.get_client()
    try:
        wf = client.find_workflow(str(workflow.strip()))
        if wf._status == 'deployed':
            log.warning("Workflow already deployed")
        else:
            wf.deploy(timeout)
    except Exception as e:
        log.error(e)


@cli.command()
@click.argument('workflow')
@click.option('--timeout', '-t', help='Time to wait for the workflow to be undeployed (optional, waits indefinitely if set to <= 0)')
@pass_config
def undeploy(config, workflow=None, timeout=None):
    """Undeploy a workflow.

    """
    client = config.get_client()
    try:
        wf = client.find_workflow(str(workflow.strip()))
        wf.undeploy(timeout)
    except Exception as e:
        log.error(e)

@cli.command()
@click.argument('workflow')
@click.option('--after', '-a', help='Timestamp of the earliest log', required=False)
@click.option('--progress', '-p', is_flag=True, help='Show progress log', required=False)
@click.option('--exceptions', '-e', is_flag=True, help='Show system exceptions', required=False)
@pass_config
def logs(config, after=None, progress=False, exceptions=False, workflow=None):
    """Fetch logs of a workflow."""
    client = config.get_client()
    try:
        wf = client.find_workflow(str(workflow.strip()))
        logs = wf.logs()
        #cleaclick.echo(logs.keys())
        if not progress and not exceptions:
            for l in logs.get("log").split('\n'):
                click.echo(l)
        if progress:
           for l in logs.get("progress").split('\n'):
                click.echo(l)
        if exceptions:
           for l in logs.get("exceptions").split('\n'):
                click.echo(l)
    except Exception as e:
        log.error(e)

def compile_python(name, code):
    try:
        compile(code, name+".py", 'exec') # check encoding
    except SyntaxError as e:
        e.filename = name
        traceback.print_exc(0)
        raise click.Abort()

############
## CREATE ##
############
@cli.command(cls=Aliased)
@click.pass_context
def create(ctx):
    """ Create a resource [workflow|function].
    """
    pass

@create.command(name='workflow')
@click.argument('name')
@click.argument('file',type=click.File('r'),required=False)
@pass_config
def create_workflow(config,name,file):
    """ Create a workflow

    NAME is the workflow's name, an ID will be generated by the platform
    """
    if file:
        try:
            wfd = file.read()
            json.loads(wfd)
        except Exception as e:
            click.echo("Can't read worfklow JSON from file ("+str(e)+")")
            return
    client = config.get_client()
    wf = client.add_workflow(str(name).strip())
    log.info("Created workflow "+wf._name+" ("+wf.id+")")
    if file and wfd:
        wf.json = wfd
    click.echo(wf.id)

# The new choice class allows a dictionary of choices and in case it is asked for all alternatives, it
class MyChoice(click.Choice):
    def __init__(self, choices, default=None, *args, **kwargs):
        self.aliases = choices
        self.default = default
        super(MyChoice,self).__init__(list(a[0] for k,a in choices.items())+['?'], *args, **kwargs)
    def convert(self, value, param, ctx):
        if value != '?':
            if value in self.aliases:
                return value
            else:
                selected = [key for key in self.aliases if value in self.aliases[key]]
                if len(selected) > 0:
                    return selected[0]
        click.echo("Available runtimes (and aliases)")
        click.echo("RUNTIME\tALIASES")
        for rt,aliases in runtimes.items():
            click.echo(rt+"\t"+','.join(aliases))
        ctx.exit(0)

runtimes = {
    'Python 3.6': ['python','Python 3.6','py36','Python3.6','Python36','python','py','py3'],
    'JRE 8u232': ['java','JRE 8u232','jre8','j8','java8','java','jre'],
}
@create.command(name='function')
@click.option('--runtime','-r', help="Runtime", default="python", is_eager=True, type=MyChoice(runtimes))
@click.argument('name')
@click.argument('file',type=click.File('r'),required=False)
@pass_config
def create_function(config,runtime,name,file):
    """Create a function.

    NAME is the function's name, an ID will be generated by the platform
    """
    if file:
        try:
            code = file.read()
        except Exception as e:
            click.echo("Can't read function code from "+file+" ("+str(e)+")")
            return
        if runtime.startswith("Python %d" % (sys.version_info.major)):
            compile_python(name, code)
    client = config.get_client()
    fn = client.add_function(str(name).strip(),runtime)
    log.info("Created function "+fn._name+" ("+fn.id+")")
    if file and code:
        fn.code = code
    click.echo(fn.id)


#########
## GET ##
#########
@cli.command(cls=Aliased)
@click.pass_context
def get(ctx):
    """ Get a resource [workflow|function].
    """
    pass

@get.command(name='workflow')
@click.argument('workflow', required=False)
@pass_config
def get_workflow(config,workflow):
    """Get workflow.

    WORKFLOW can be the workflow's name or ID, accepts partial values
    """
    client = config.get_client()

    if workflow:
        wfs = [client.find_workflow(str(workflow).strip())]
    else:
        wfs = client.workflows
    table = [("ID","NAME","STATUS","MODIFIED","ENDPOINT")]
    namelen = 0
    eplen = 0
    for wf in wfs:
        table.append((wf.id,wf._name,wf._status,datetime.datetime.fromtimestamp(wf._modified).strftime("%Y-%m-%d %H:%M:%S"),wf._endpoints[0] if len(wf._endpoints) else ""))
        namelen = max(namelen,len(wf._name))
        eplen = max(eplen,len(table[-1][4]))
        for ep in wf._endpoints[1:]:
            table.append(("","","","",ep))
            eplen = max(eplen,len(ep))
    formatstr = f"%-32s %-{namelen}s %-12s %-19s %-{eplen}s"
    for row in table:
        click.echo(formatstr % row)

@get.command(name='function')
@click.argument('function', required=False)
@pass_config
def get_function(config,function):
    """List functions."""
    client = config.get_client()

    if function:
        fns = [client.find_function(str(function).strip())]
    else:
        fns = client.functions

    table = [("ID","NAME","RUNTIME","MODIFIED")]
    namelen = 0
    rtlen = 0
    for g in fns:
        table.append((g.id,g._name,g._runtime,datetime.datetime.fromtimestamp(g._modified).strftime("%Y-%m-%d %H:%M:%S")))
        namelen = max(namelen,len(g._name))
        rtlen = max(rtlen,len(g._runtime))
    formatstr = f"%-32s %-{namelen}s %-{rtlen}s %-12s"
    for row in table:
        click.echo(formatstr % row)


##########
## EDIT ##
##########
def edit_string(input):
    (tfd,tfpath) = tempfile.mkstemp(text=True)
    try:
        with open(tfd,"w+") as tf:
            tf.write(input)
            tf.flush()
            rv = os.system('vi' + ' "' + tfpath + '" </dev/tty >/dev/tty 2>&1')
            if rv != 0:
                click.echo("Editor exit status: "+str(rv))
                return
            tf.seek(0)
            output = tf.read()
    finally:
        os.unlink(tfpath)
    return output


@cli.command(cls=Aliased)
@click.pass_context
def edit(ctx):
    """ Edit a resource [workflow|function].
    """
    pass

@edit.command(name='workflow')
@click.argument('workflow')
@pass_config
def edit_workflow(config,workflow):
    """Edit workflow description.

    WORKFLOW can be the workflow's name or ID, accepts partial values
    """
    client = config.get_client()

    wf = client.find_workflow(str(workflow).strip())
    old_wfd = wf.json
    wfd = edit_string(old_wfd)
    if wfd == old_wfd:
        click.echo("Unchanged workflow "+wf._name)
        return
    try:
        json.loads(wfd) # check encoding
        wf.json = wfd
        click.echo("Updated workflow "+wf._name)
    except json.JSONDecodeError as e:
        lines = wfd.split('\n')
        click.echo(lines[e.lineno-2],file=sys.stderr)
        click.echo(lines[e.lineno-1],file=sys.stderr)
        click.echo(" "*(e.colno-1)+"^",file=sys.stderr)
        click.echo(str(e),file=sys.stderr)

@edit.command(name='function')
@click.argument('function')
@pass_config
def edit_function(config,function):
    """Edit function code."""
    client = config.get_client()

    g = client.find_function(str(function).strip())
    old_code = g.code
    code = edit_string(old_code)
    if code == old_code:
        click.echo("Unchanged function code "+g._name)
        return
    if g._runtime.startswith("Python %d" % (sys.version_info.major)):
        compile_python(g._name, code)
    g.code = code
    click.echo("Updated function code "+g._name+", you'd need to redeploy workflows that use this function to use it.")


############
## DELETE ##
############
@cli.command(cls=Aliased)
@click.pass_context
@click.option('--force','-f',is_flag=True,help="Don't ask for confirmation.",default=False)
def delete(ctx,force):
    """ Delete a resource [workflow|function].
    """
    ctx.obj.force=force
    pass

@delete.command(name='workflow')
@click.argument('name')
@click.option('--force','-f',is_flag=True,help="Don't ask for confirmation.",default=False)
@click.pass_context
def delete_workflow(ctx,name,force):
    """Delete a workflow

    WORKFLOW can be the workflow's name or ID, accepts partial values
    """
    ctx.obj.force=force
    client = ctx.obj.get_client()
    wf = client.find_workflow(str(name).strip())
    if ctx.obj.force or click.confirm("Do you want to delete workflow '"+wf._name+"' ("+wf.id+")?"):
        client.delete_workflow(wf)
        click.echo(wf.id)

@delete.command(name='function')
@click.argument('name')
@click.option('--force','-f',is_flag=True,help="Don't ask for confirmation.",default=False)
@click.pass_context
def delete_workflow(ctx,name,force):
    ctx.obj.force=force
    client = ctx.obj.get_client()
    try:
        fn = client.find_function(name)
    except Exception as e:
        log.exception(e)
        click.echo("Could not find a function matching '"+name+"'",file=sys.stderr)
        return
    if ctx.obj.force or click.confirm("Do you want to delete function '"+fn._name+"' ("+fn.id+")?"):
        client.delete_function(fn)
        click.echo(fn.id)


#########################

@cli.command()
@click.argument('workflow')
@pass_config
def workflow(config, workflow):
    """Show workflow specification.

    WORKFLOW can be the workflow's name or ID, accepts partial values
    """
    client = config.get_client()
    try:
        wf = client.find_workflow(str(workflow.strip()))
        print(f"WORKFLOW '{wf._name}' ({wf.id})",file=sys.stderr)
        click.echo(wf.json)
    except Exception as e:
        log.error(e)


@cli.command()
@pass_config
def workflows(config):
    """List workflows.

    WORKFLOW can be the workflow's name or ID, accepts partial values
    """
    client = config.get_client()

    table = [("ID","NAME","STATUS","MODIFIED","ENDPOINT")]
    namelen = 0
    eplen = 0
    for wf in client.workflows:
        table.append((wf.id,wf._name,wf._status,datetime.datetime.fromtimestamp(wf._modified).strftime("%Y-%m-%d %H:%M:%S"),wf._endpoints[0] if len(wf._endpoints) else ""))
        namelen = max(namelen,len(wf._name))
        eplen = max(eplen,len(table[-1][4]))
        for ep in wf._endpoints[1:]:
            table.append(("","","","",ep))
            eplen = max(eplen,len(ep))
    formatstr = f"%-32s %-{namelen}s %-12s %-19s %-{eplen}s"
    for row in table:
        click.echo(formatstr % row)


@cli.command()
@click.argument('function')
#@click.option('--runtime','-r')
@pass_config
def function(config, function="", subcommand=None):
    """Show code of a function.

    FUNCTION can be the function's name or ID, accepts partial values
    """
    client = config.get_client()
    g = None
    try:
        g = client.find_function(str(function.strip()))
        click.echo(f"FUNCTION '{g._name}' (id={g.id}, runtime={g._runtime})",file=sys.stderr)
    except Exception as e:
        log.error(e)
        return


@cli.command()
@pass_config
def functions(config):
    """List functions.

    FUNCTION can be the function's name or ID, accepts partial values
    """
    client = config.get_client()

    table = [("ID","NAME","RUNTIME","MODIFIED")]
    namelen = 0
    rtlen = 0
    for fn in client.functions:
        table.append((fn.id,fn._name,fn._runtime,datetime.datetime.fromtimestamp(fn._modified).strftime("%Y-%m-%d %H:%M:%S")))
        namelen = max(namelen,len(fn._name))
        rtlen = max(rtlen,len(fn._runtime))
    formatstr = f"%-32s %-{namelen}s %-{rtlen}s %-12s"
    for row in table:
        click.echo(formatstr % row)

