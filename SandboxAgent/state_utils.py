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

import os

import process_utils

def create_dummy_resource_for_asl_state(wf_node):
    error = None
    resource = {}
    resource["name"] = wf_node.getGWFStateName()
    dirpath = "/opt/mfn/code/resources/" + resource["name"] + "/"
    if not os.path.exists(os.path.dirname(dirpath)):
        try:
            os.makedirs(os.path.dirname(dirpath))
        except OSError as err:
            if err.errno != os.errno.EEXIST:
                error = err
                return (error, None)

    resource["dirpath"] = dirpath
    # these ASL states do not have a Task resource and are handled by our function worker
    resource["runtime"] = "python 3.6"
    resource["env_var_list"] = []

    return (error, resource)

def create_state(wf_node, resource, logger):
    error = None
    state = {}
    statename = wf_node.getGWFStateName()
    state["name"] = statename
    dirpath = "/opt/mfn/workflow/states/" + statename + "/"
    if not os.path.exists(os.path.dirname(dirpath)):
        try:
            os.makedirs(os.path.dirname(dirpath))
        except OSError as err:
            if err.errno != os.errno.EEXIST:
                error = err
                return (error, None)

    # copy the resource into the state folder
    # if multiple states use the same resource, this will ensure that they get their own copies
    cpcmd = 'cp -a "%s" "%s"' % (resource["dirpath"], dirpath) # modify to allow for white space in state name

    logger.info("Copying resource for state: %s", statename)
    error, _ = process_utils.run_command(cpcmd, logger, wait_output=True)
    if error is not None:
        error = "Could not copy resource for state: " + resource["name"] + " " + statename + " " + error
        logger.error(error)
        return (error, None)

    if resource["runtime"].find("python") != -1:
        rdirpath = dirpath + resource["name"] + "/"
        fname = resource["name"]
        fpath = rdirpath + fname + ".py"
    elif resource["runtime"].find("java") != -1:
        # update it to the .class, because at this point the source has been compiled
        # ensure that the fpath actually contains the actual location of the compiled class file
        # e.g., target/classes for unzipped and/or maven dependency installed java functions
        # if target/classes exists, then we compile the source code
        # else we just assume the .class file is next to where the source is
        # (i.e., according to the uploaded zip/jar)
        if os.path.exists(dirpath + resource["name"] + "/target/classes/"):
            rdirpath = dirpath + resource["name"] + "/target/classes/"
        else:
            rdirpath = dirpath + resource["name"] + "/"
        # _XXX_: fpath is irrelevant for java functions; java request handler uses the fname
        fname = resource["name"]
        fpath = rdirpath + fname
    else:
        error = "Unsupported runtime: " + resource["runtime"]
        return (error, None)

    state["dirpath"] = dirpath
    state["resource_dirpath"] = rdirpath
    state["resource_filepath"] = fpath
    state["resource_filename"] = fname
    state["resource_runtime"] = resource["runtime"]
    state["resource_env_var_list"] = resource["env_var_list"]

    return (error, state)
