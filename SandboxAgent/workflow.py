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

import collections
import json

class WorkflowType:
    WF_TYPE_SAND = 0
    WF_TYPE_ASL = 1

class WorkflowStateType:
    SAND_TASK_STATE_TYPE = "Task_SAND"
    TASK_STATE_TYPE = "Task"
    CHOICE_STATE_TYPE = "Choice"
    PASS_STATE_TYPE = "Pass"
    SUCCEED_STATE_TYPE = "Succeed"
    FAIL_STATE_TYPE = "Fail"
    WAIT_STATE_TYPE = "Wait"
    PARALLEL_STATE_TYPE = "Parallel"
    MAP_STATE_TYPE = "Map"

class WorkflowNode:
    def __init__(self, topic, nextNodes, potNext, gwftype, gwfstatename, gwfstateinfo, is_session_function, sfparams, logger):

        self.nodeId = topic
        self.nextMap = {}
        self.gWFType = gwftype
        self._resource_name = ""
        if gwftype == WorkflowStateType.SAND_TASK_STATE_TYPE or gwftype == WorkflowStateType.TASK_STATE_TYPE:
            try:
                self._resource_name = gwfstateinfo["Resource"]
            except Exception as exc:
                logger.error("Could not get resource name for task: " + topic + " " + str(exc))
        self.gWFStateName = gwfstatename
        self.gWFStateInfo = json.dumps(gwfstateinfo)

        for next_node in nextNodes:
            self.nextMap[next_node] = True

        self.potentialNextMap = {}
        for potnext_node in potNext:
            self.potentialNextMap[potnext_node] = True

        self._is_session_function = is_session_function
        self._session_function_parameters = sfparams

    def getNextMap(self):
        return self.nextMap

    def getPotentialNextMap(self):
        return self.potentialNextMap

    def getGWFType(self):
        return self.gWFType

    def getGWFStateName(self):
        return self.gWFStateName

    def getGWFStateInfo(self):
        return self.gWFStateInfo

    def is_session_function(self):
        return self._is_session_function

    def get_session_function_parameters(self):
        return self._session_function_parameters

    def get_resource_name(self):
        return self._resource_name

class Workflow:
    def __init__(self, uid, sid, wid, wf_type, wfstr, logger): # throws Exception
        self._logger = logger

        self.userId = uid
        self.sandboxId = sid
        self.workflowId = wid
        self._workflow_type = wf_type

        self.topicPrefix = self.sandboxId + "-" + self.workflowId + "-"
        self.workflowDefaultTableDataLayer = "wf_" + wid
        self.workflowMapTableDataLayer = "wf_maps_" + wid
        self.workflowSetTableDataLayer = "wf_sets_" + wid
        self.workflowCounterTableDataLayer = "wf_counters_" + wid
        self.workflowNodeMap = {}
        self.workflowFunctionMap = {}
        self.workflowLocalFunctions = {}
        self.workflowSessionFunctions = {}

        self.parallelStateNamesStack = collections.deque([])
        self.parallelBranchCounterStack = collections.deque([])

        self.mapStateNamesStack = collections.deque([])
        self.mapBranchCounterStack = collections.deque([])

        self.workflowExitPoint = None
        self.workflowExitTopic = None

        self._is_session_workflow = False

        # whether the function workers should store backups of triggers to next functions
        self._enable_checkpoints = True
        self._allow_immediate_messages = False

        self._has_error = False

        # construct from JSON
        wfobj = json.loads(wfstr)
        if self._workflow_type == WorkflowType.WF_TYPE_ASL:
            self.parseASL(wfobj)
        else:
            self.parseSandDescription(wfobj)

    def parseSandDescription(self, wfobj):

        """ {
                "name": "test_workflow",
                "entry": "entryFunction",
                "enable_checkpoints": False,
                "allow_immediate_messages": True,
                "exit": "exitName",
                "functions": [
                    {
                        "name": "entryFunction",
                        "next": [],
                        "isSessionFunction": true,
                        "sessionFunctionParameters":
                        {
                            "heartbeat_method": "function",
                            "heartbeat_function": "aFunction",
                            "heartbeat_interval_ms": 5000
                        },
                        "potentialNext": []
                    }
                ]
            }
        """
        self.workflowName = wfobj["name"]
        self.workflowEntryPoint = wfobj["entry"]
        self.workflowEntryTopic = self.topicPrefix + self.workflowEntryPoint

        if "exit" in wfobj.keys():
            self.workflowExitPoint = wfobj["exit"]
        elif "end" in wfobj.keys():
            self.workflowExitPoint = wfobj["end"]
        else:
            # default case
            self.workflowExitPoint = "end"

        if "enable_checkpoints" in wfobj.keys():
            self._enable_checkpoints = wfobj["enable_checkpoints"]

        if "allow_immediate_messages" in wfobj.keys():
            self._allow_immediate_messages = wfobj["allow_immediate_messages"]

        if self._allow_immediate_messages:
            # also include the exit as a potential destination for sending immediate trigger messages
            self.workflowFunctionMap[self.workflowExitPoint] = True

        self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
        self._logger.info("parseSAND: workflowExitTopic: " + self.workflowExitTopic)

        functions = wfobj["functions"]
        for function in functions:
            gname = function["name"]
            resource = gname
            if "resource" in function:
                resource = function["resource"]

            if self._allow_immediate_messages:
                # keep a map of function names as potential destination for sending immediate trigger messages
                self.workflowFunctionMap[gname] = True
            topic = self.topicPrefix + gname

            #print("topic:", topic)
            #print("gname:", gname)

            nextNodes = []
            if "next" in function.keys():
                next = function["next"]
                for nnode in next:
                    nextNodes.append(nnode)
            potNext = []
            if "potentialNext" in function.keys():
                potential = function["potentialNext"]
                for pnnode in potential:
                    potNext.append(pnnode)

            gwftype = WorkflowStateType.SAND_TASK_STATE_TYPE
            gwfstatename = gname
            gwfstateinfo = {}
            gwfstateinfo["Resource"] = resource
            #self._logger.info("parseSAND: gwftype: " + gwftype + ", gwfstatename: " + gname + ", gwfstateinfo: " + gwfstateinfo)

            is_session_function = False
            if "isSessionFunction" in function.keys():
                is_session_function = function["isSessionFunction"]

            sfparams = {}
            if is_session_function and "sessionFunctionParameters" in function.keys():
                sfparams = function["sessionFunctionParameters"]

            wfnode = WorkflowNode(topic, nextNodes, potNext, gwftype, gwfstatename, gwfstateinfo, is_session_function, sfparams, self._logger)

            self.workflowNodeMap[topic] = wfnode

            if is_session_function:
                self._is_session_workflow = True
                self.workflowSessionFunctions[gname] = is_session_function

        # check whether all 'next' fields refer to existing functions
        # for (Map.Entry<String, WorkflowNode> entry: this.workflowNodeMap.entrySet())
        for entry in self.workflowNodeMap:

            #wfnode = entry.getValue()
            wfnode = self.workflowNodeMap[entry]
            currentFunction = wfnode.getGWFStateName()

            nextNodes = wfnode.getNextMap().keys()
            for next in nextNodes:
                nexttopic = self.topicPrefix + next

                if nexttopic != self.workflowExitTopic and nexttopic not in self.workflowNodeMap.keys():
                    self._logger.error("Faulty workflow description: " + currentFunction + " uses " + next + ", which does not exist!")
                    self._has_error = True

            potentialNext = wfnode.getPotentialNextMap().keys()
            for potnext in potentialNext:
                potnexttopic = self.topicPrefix + potnext

                if potnexttopic != self.workflowExitTopic and potnexttopic not in self.workflowNodeMap.keys():
                    self._logger.error("Faulty workflow description: " + currentFunction + " potentially uses " + potnext + ", which does not exist!")
                    self._has_error = True

    def has_error(self):
        return self._has_error

    def parseASL(self, wfobj):
        self.workflowName = self.workflowId # there is no "Name" key in ASL
        self.workflowEntryPoint = wfobj["StartAt"]
        self.workflowEntryTopic = self.topicPrefix + self.workflowEntryPoint

        if "EnableCheckpoints" in wfobj.keys():
            self._enable_checkpoints = wfobj["EnableCheckpoints"]

        if "AllowImmediateMessages" in wfobj.keys():
            self._allow_immediate_messages = wfobj["AllowImmediateMessages"]

        self._logger.info("parseASL: workflowName: " + self.workflowName)
        self._logger.info("parseASL: workflowEntryPoint: " + self.workflowEntryTopic)
        workflowstates = wfobj["States"]
        self.parseStates(workflowstates)

    def createAndAddASLWorkflowNode(self, gname, nextNodes, potNext, gwfstatetype, gwfstatename, gwfstateinfo, is_session_function=False, sfparams={}):
        topic = self.topicPrefix + gname

        wfnode = WorkflowNode(topic, nextNodes, potNext, gwfstatetype, gwfstatename, gwfstateinfo, is_session_function, sfparams, self._logger)
        self.workflowNodeMap[topic] = wfnode # add new node to workflow node map

    def insideMapBranchAlready(self):
        if self.mapStateNamesStack:
            return True  # not empty

    def insideParallelBranchAlready(self):
        if self.parallelStateNamesStack:
            return True  # not empty

        return False # empty

    def constructParentParallelInfo(self):
        parentInfo = {}
        parentInfo["Name"] = self.parallelStateNamesStack[len(self.parallelStateNamesStack)-1] # peek() operation
        parentInfo["BranchCounter"] = self.parallelBranchCounterStack[len(self.parallelBranchCounterStack)-1] # peek() operation
        return parentInfo

    def constructParentMapInfo(self):
        parentInfo = {}
        parentInfo["Name"] = self.mapStateNamesStack[len(self.mapStateNamesStack)-1] # peek() operation
        #parentInfo["BranchCounter"] = self.mapBranchCounterStack[len(self.parallelBranchCounterStack)-1] # peek() operation
        parentInfo["BranchCounter"] = 1 # hardcoded branch count, required?
        return parentInfo


    def parseStates(self, workflowstates):
        for statename in workflowstates.keys(): # loop over ASL states
            stateinfo = workflowstates[statename] # loop over the states in the set
            assert "Type" in stateinfo.keys()
            statetype = stateinfo["Type"]

            self._logger.info("parseStates: State name: %s, state type: %s", statename, statetype)

            if statetype == WorkflowStateType.TASK_STATE_TYPE:
                self.parseTaskState(statename, stateinfo)
            elif statetype == WorkflowStateType.CHOICE_STATE_TYPE:
                self.parseChoiceState(statename, stateinfo)
            elif statetype == WorkflowStateType.PASS_STATE_TYPE:
                self.parsePassState(statename, stateinfo)
            elif statetype == WorkflowStateType.SUCCEED_STATE_TYPE:
                self.parseSucceedState(statename, stateinfo)
            elif statetype == WorkflowStateType.FAIL_STATE_TYPE:
                self.parseFailState(statename, stateinfo)
            elif statetype == WorkflowStateType.WAIT_STATE_TYPE:
                self.parseWaitState(statename, stateinfo)
            elif statetype == WorkflowStateType.PARALLEL_STATE_TYPE:
                self.parseParallelState(statename, stateinfo)
            elif statetype == WorkflowStateType.MAP_STATE_TYPE:
                self.parseMapState(statename, stateinfo)
            else:
                raise Exception("Error: unknown state type")

    def parseTaskState(self, taskstatename, taskstateinfo):
        potNext = []
        nextNodes = []

        if "Resource" not in taskstateinfo.keys():
            self._logger.error("Task state missing Resource field")
            raise Exception("Task state missing Resource field")

        if "End" in taskstateinfo.keys():
            value = taskstateinfo["End"]

            if bool(value) and not (self.insideParallelBranchAlready() or self.insideMapBranchAlready()):
                self.workflowExitPoint = "end"
                if self._allow_immediate_messages:
                    self.workflowFunctionMap[self.workflowExitPoint] = True
                nextNodes.append(self.workflowExitPoint)
                self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
            #else:
                # This is a branch end, so don't add this as a workflow exit point
        else:
            taskstateinfo["End"] = False

        if "Next" in taskstateinfo.keys():
            nextNodes.append(taskstateinfo["Next"])

        if "PotentialNext" in taskstateinfo.keys():
            potential = taskstateinfo["PotentialNext"]
            sizePotNext = len(potential)
            for j in range(sizePotNext):
                potNext.append(potential[j])

        is_session_function = False
        if "SessionFunction" in taskstateinfo.keys():
            is_session_function = taskstateinfo["SessionFunction"]

        sfparams = {}
        if is_session_function and "SessionFunctionParameters" in taskstateinfo.keys():
            sfparams = taskstateinfo["SessionFunctionParameters"]

        if is_session_function:
            self._is_session_workflow = True
            self.workflowSessionFunctions[taskstatename] = is_session_function

        if self._allow_immediate_messages:
            self.workflowFunctionMap[taskstatename] = True

        if "Catch" in taskstateinfo.keys(): # need to add Catch Next to potentialNext
            for catch in taskstateinfo["Catch"]:
                potential_cat = catch["Next"]
                potNext.append(potential_cat)
                self._logger.info("Catch policy adding: " + potential_cat + " as potential Next to: " + taskstatename)

        """
        if "InputPath" in taskstateinfo.keys():
        if "OutputPath" in taskstateinfo.keys():
        if "ResultPath" in taskstateinfo.keys():
        if "Retry" in taskstateinfo.keys():
        """

        if self.insideParallelBranchAlready():
            taskstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            taskstateinfo["ParentMapInfo"] = self.constructParentMapInfo()

        self._logger.info("parseTask: State info: " + str(taskstateinfo))
        self.createAndAddASLWorkflowNode(taskstatename, nextNodes, potNext, WorkflowStateType.TASK_STATE_TYPE, taskstatename, taskstateinfo, is_session_function, sfparams)

    def parseChoiceState(self, choicestatename, choicestateinfo):
        potNext = []
        nextNodes = []
        gname = choicestatename

        """
        if "InputPath" in choicestateinfo.keys():
        if "OutputPath" in choicestateinfo.keys():
        """

        if "Default" in choicestateinfo.keys():
            potNext.append(choicestateinfo["Default"])
        if "Choice" in choicestateinfo.keys():
            arr = {}
            arr = choicestateinfo["Choices"]
            for i in range(arr.length()):
                option = arr[i]
                nextVal = option["Next"]
                potNext.append(nextVal)

        choicestateinfo["End"] = False

        if self.insideParallelBranchAlready():
            choicestateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            choicestateinfo["ParentMapInfo"] = self.constructParentMapInfo()

        self._logger.info("parseChoice: State info: " + str(choicestateinfo))
        self.createAndAddASLWorkflowNode(gname, nextNodes, potNext, WorkflowStateType.CHOICE_STATE_TYPE, choicestatename, choicestateinfo)

    def parsePassState(self, passstatename, passstateinfo):
        potNext = []
        nextNodes = []
        gname = passstatename
        if "End" in passstateinfo.keys():
            value = passstateinfo["End"]
            if bool(value) and not (self.insideParallelBranchAlready() or self.insideMapBranchAlready()):
                self.workflowExitPoint = "end"
                nextNodes.append(self.workflowExitPoint)
                self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
            #else:
                # This is a branch end state and not a workflow exit point
        else:
            passstateinfo["End"] = False
            if "Next" in passstateinfo.keys():
                nextNodes.append(passstateinfo["Next"])
        """
        if "InputPath" in passstateinfo.keys():
        if "OutputPath" in passstateinfo.keys():
        if "ResultPath" in passstateinfo.keys():
        if "Result" in passstateinfo.keys():
        """
        if self.insideParallelBranchAlready():
            passstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            passstateinfo["ParentMapInfo"] = self.constructParentMapInfo()

        self._logger.info("parsePass: State info: " + str(passstateinfo))
        self.createAndAddASLWorkflowNode(gname, nextNodes, potNext, WorkflowStateType.PASS_STATE_TYPE, passstatename, passstateinfo)

    def parseSucceedState(self, succeedstatename, succeedstateinfo):
        potNext = []
        nextNodes = []
        gname = succeedstatename

        """
        if "InputPath" in succeedstateinfo.keys():
        if "OutputPath" in succeedstateinfo.keys():
        """
        self.workflowExitPoint = "end"
        nextNodes.append(self.workflowExitPoint)
        self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
        succeedstateinfo["End"] = True

        if self.insideParallelBranchAlready():
            succeedstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            succeedstateinfo["ParentMapInfo"] = self.constructParentMapInfo()

        self._logger.info("parseSucceed: State info: " + str(succeedstateinfo))
        self.createAndAddASLWorkflowNode(gname, nextNodes, potNext, WorkflowStateType.SUCCEED_STATE_TYPE, succeedstatename, succeedstateinfo)


    def parseFailState(self, failstatename, failstateinfo):
        potNext = []
        nextNodes = []
        gname = failstatename

        """
        if "InputPath" in failstateinfo.keys():
        if "Error" in failstateinfo.keys():
        """

        self.workflowExitPoint = "end"
        nextNodes.append(self.workflowExitPoint)
        self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
        failstateinfo["End"] = True

        if self.insideParallelBranchAlready():
            failstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            failstateinfo["ParentMapInfo"] = self.constructParentMapInfo()

        self._logger.info("parseFail: State info: " + str(failstateinfo))
        self.createAndAddASLWorkflowNode(gname, nextNodes, potNext, WorkflowStateType.FAIL_STATE_TYPE, failstatename, failstateinfo)

    def parseWaitState(self, waitstatename, waitstateinfo):
        potNext = []
        nextNodes = []
        gname = waitstatename

        if "End" in waitstateinfo.keys():
            value = waitstateinfo["End"]
            if bool(value) and not self.insideParallelBranchAlready():
                self.workflowExitPoint = "end"
                nextNodes.append(self.workflowExitPoint)
                self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
            #else:
                # This is branch terminal state and not a workflow exit point
        else:
            waitstateinfo["End"] = True
            if "Next" in waitstateinfo.keys():
                nextNodes.append(waitstateinfo["Next"])

        """
        if (waitstateinfo.has("Seconds")) {}
        if (waitstateinfo.has("Timestamp")) {}
        if (waitstateinfo.has("SecondsPath")) {}
        if (waitstateinfo.has("TimestampPath")) {}
        if (waitstateinfo.has("InputPath")) {}
        if (waitstateinfo.has("OutputPath")) {}
        """

        if self.insideParallelBranchAlready():
            waitstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        if self.insideMapBranchAlready():
            waitstateinfo["ParentParallelInfo"] = self.constructParentMapInfo()

        self._logger.info("parseWait: State info: " + str(waitstateinfo))
        self.createAndAddASLWorkflowNode(gname, nextNodes, potNext, WorkflowStateType.WAIT_STATE_TYPE, waitstatename, waitstateinfo)

    def parseParallelState(self, parallelstatename, parallelstateinfo):
        potNext = []
        nextNodes = []
        parallelstateinfo["WorkflowID"] = self.workflowId
        parallelstateinfo["SandboxID"] = self.sandboxId

        if "End" in parallelstateinfo.keys():
            value = parallelstateinfo["End"]
            if bool(value) and not self.insideParallelBranchAlready():
                self.workflowExitPoint = "end"
                potNext.append(self.workflowExitPoint)
                self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
            #else:
                # This is a branch end and not a workflow exit point
        else:
            parallelstateinfo["End"] = False
            if "Next" in parallelstateinfo.keys():
                potNext.append(parallelstateinfo["Next"])

        """
        if(parallelstateinfo.has("InputPath"))
        if(parallelstateinfo.has("OutputPath"))
        if(parallelstateinfo.has("ResultPath"))
        """

        parallelstateinfo["Name"] = parallelstatename

        if self.insideParallelBranchAlready():
            parallelstateinfo["ParentParallelInfo"] = self.constructParentParallelInfo()

        self.parallelStateNamesStack.append(parallelstatename)

        if "Branches" in parallelstateinfo.keys():
            count = 0
            branches = parallelstateinfo["Branches"]

            len_branches = len(branches)
            for i in range(len_branches):
                branch = branches[i]
                self.parallelBranchCounterStack.append(i+1)
                count += 1

                if "StartAt" in branch.keys():
                    potNext.append(branch["StartAt"])
                else:
                    raise Exception("Branch missing StartAt field")

                if "States" in branch.keys():
                    self.parseStates(branch["States"])
                else:
                    raise Exception("Branch missing States field")
                self.parallelBranchCounterStack.pop()
            parallelstateinfo["BranchCount"] = count
        else:
            self._logger.info("parseParallelState: 'Branches' parameter missing from state description of: " + parallelstatename)
            raise Exception("'Branches' parameter missing from state description of: " + parallelstatename)
        self.parallelStateNamesStack.pop()
        self._logger.info("parseParallel: State info: " + str(parallelstateinfo))
        self.createAndAddASLWorkflowNode(parallelstatename, nextNodes, potNext, WorkflowStateType.PARALLEL_STATE_TYPE, parallelstatename, parallelstateinfo)

    def parseMapState(self, mapstatename, mapstateinfo):
        potNext = []
        nextNodes = []
        mapstateinfo["WorkflowID"] = self.workflowId
        mapstateinfo["SandboxID"] = self.sandboxId
        self._logger.info("Inside parseMapState, mapstateinfo: " + str(mapstateinfo))
        if "End" in mapstateinfo.keys() and mapstateinfo["End"] == True:
            value = mapstateinfo["End"]
            if bool(value) and not self.insideMapBranchAlready():
                self.workflowExitPoint = "end"
                potNext.append(self.workflowExitPoint)
                self.workflowExitTopic = self.topicPrefix + self.workflowExitPoint
            #else:
                # This is a branch end and not a workflow exit point
        else:
            mapstateinfo["End"] = False
            if "Next" in mapstateinfo.keys():
                potNext.append(mapstateinfo["Next"])
                #nextNodes.append(mapstateinfo["Next"])

        """
        if(mapstateinfo.has("InputPath"))
        if(mapstateinfo.has("OutputPath"))
        if(mapstateinfo.has("ResultPath"))
        """

        mapstateinfo["Name"] = mapstatename

        if self.insideMapBranchAlready():
            mapstateinfo["ParentMapInfo"] = self.constructParentMapInfo() # BranchCounter needs to be added by FunctionWorker
        #mapstateinfo["ParentMapInfo"] = {"Name": mapstatename, "BranchCounter": 1}

        self.mapStateNamesStack.append(mapstatename)
        if "MaxConcurrency" in mapstateinfo.keys():
            mapstateinfo["MaxConcurrency"] = mapstateinfo["MaxConcurrency"]

        if "Iterator" in mapstateinfo.keys():
            count = 1 # hardcoded number of branches
            iterator = mapstateinfo["Iterator"]

            self.mapBranchCounterStack.append(1)

            if "StartAt" in iterator.keys():
                potNext.append(iterator["StartAt"])
            else:
                raise Exception("Iterator missing StartAt field")

            if "States" in iterator.keys():
                self.parseStates(iterator["States"])
            else:
                raise Exception("Iterator missing States field")

            mapstateinfo["BranchCount"] = count # needs to be corrected in FunctionWorker

        else:
            self._logger.info("parseMapState: 'Iterator' parameter missing from state description of: " + mapstatename)
            raise Exception("'Iterator' parameter missing from state description of: " + mapstatename)
        self.mapStateNamesStack.pop()
        self._logger.info("parseMap: State info: " + str(mapstateinfo))
        self.createAndAddASLWorkflowNode(mapstatename, nextNodes, potNext, WorkflowStateType.MAP_STATE_TYPE, mapstatename, mapstateinfo)

    def getWorkflowNode(self, topic):
        return self.workflowNodeMap[topic]

    def getNextMap(self, topic):
        wnode = self.workflowNodeMap[topic]
        if wnode is not None:
            return wnode.getNextMap()
        return {}

    def getWorkflowTopics(self):
        wftopics = self.workflowNodeMap.keys()
        return wftopics

    def getPotentialNextMap(self, topic):
        wnode = self.workflowNodeMap[topic]
        if wnode is not None:
            return wnode.getPotentialNextMap()
        return {}

    def getWorkflowNodeState(self, topic):
        wnode = self.workflowNodeMap[topic]
        if wnode is not None:
            return [wnode.getGWFType(), wnode.getGWFStateName(), wnode.getGWFStateInfo()]
        return [""]

    def getSandboxId(self):
        return self.sandboxId

    def getWorkflowId(self):
        return self.workflowId

    def getWorkflowNodeMap(self):
        return self.workflowNodeMap

    def getAllWorkflowTopics(self):
        return self.workflowNodeMap.keys()

    def getWorkflowExitPoint(self):
        return self.workflowExitPoint

    def getWorkflowExitTopic(self):
        return self.workflowExitTopic

    def getWorkflowEntryTopic(self):
        return self.workflowEntryTopic

    def getWorkflowLocalFunctions(self):
        return self.workflowLocalFunctions

    def getUserId(self):
        return self.userId

    def getWorkflowDefaultTableDataLayer(self):
        return self.workflowDefaultTableDataLayer

    def getWorkflowMapTableDataLayer(self):
        return self.workflowMapTableDataLayer

    def getWorkflowSetTableDataLayer(self):
        return self.workflowSetTableDataLayer

    def getWorkflowCounterTableDataLayer(self):
        return self.workflowCounterTableDataLayer

    def getWorkflowFunctionMap(self):
        return self.workflowFunctionMap

    def getWorkflowSessionFunctions(self):
        return self.workflowSessionFunctions

    def is_session_workflow(self):
        return self._is_session_workflow

    def set_session_workflow(self, flag):
        self._is_session_workflow = flag

    def addLocalFunction(self, function_topic):
        self.workflowLocalFunctions[function_topic] = True

    def removeLocalFunction(self, function_topic):
        del self.workflowLocalFunctions[function_topic]

    def are_checkpoints_enabled(self):
        return self._enable_checkpoints
