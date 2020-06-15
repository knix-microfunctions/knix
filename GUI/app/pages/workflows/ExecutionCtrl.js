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

(function() {
  angular.module('MfnWebConsole').controller('ExecutionCtrl', function($scope, $http, $cookies, $timeout, $uibModal, $interval, toastr, sharedProperties, sharedData) {

     var urlPath = sharedProperties.getUrlPath();
     var workflowStatus = sharedProperties.getWorkflowStatus();
     var workflowName = sharedProperties.getWorkflowName();
     var workflowId = sharedProperties.getWorkflowId();
     var workflowUrl = sharedProperties.getWorkflowUrl();

     var inter = undefined;

     var workflowEdges = new Array();
     var traversedStates = new Array();
     var executedBranches = 0;
     var lastParallelNext = "";
     var prevLogEntry = "";
     var prevProgressEntry = "";
     var workflowExecuted = false;
     var functionExecIds = { };
     var initialized = false;
     var execCounter = 0;
     var execEvents = [];
     var popoverVisible = false;
     var executionModalVisible = true;

     var executedFunctions = [];
     var failedFunctions = [];

     var currentEntry = 0;
     var items;
     var timeline;
     var startTime;
     var fileContents = "";
     var codeError = "";
     var intervalCounter = 0;
     var state2FunctionMapping = {};
     var workflowJson = "";
     $scope.activeTab = 0;
     $scope.gTab = 0;


     $scope.workflowButtonLabel = "Workflow Editor";

     var dataPrefix = sharedProperties.getDataPrefix();

     retrieveWorkflowJson();

     var vm = $scope;
     vm.file_changed = function(element){
     var file = element.files[0];
     var reader = new FileReader();
     reader.onload = function(e) {
        vm.$apply(function() {
          fileContents = reader.result.slice(reader.result.indexOf("base64,") + "base64,".length);
          var decodedFileContents = atob(fileContents);
          /*if (decodedFileContents.match(/[^\u0000-\u007f]/)) {
            // non-ASCII file
            //$scope.aceInputSession.setValue(fileContents);
            $scope.aceInputSession.setValue("Uploaded file: " + file.name);
            sharedData.setWorkflowExecutionInputEditor(workflowId, "Uploaded file: " + file.name);
            sharedData.setWorkflowExecutionInput(workflowId, fileContents);
            $scope.aceInput.focus();
          } else {*/
            // ASCII file
            $scope.aceInputSession.setValue(decodedFileContents);
            if (workflowName.endsWith("   ")) {
              // test function
              sharedData.setWorkflowExecutionInputEditor("mfn-internal-" + workflowName, decodedFileContents);
              sharedData.setWorkflowExecutionInput("mfn-internal-" + workflowName, decodedFileContents);
            } else {
              // execute workflow
              sharedData.setWorkflowExecutionInputEditor(workflowId, decodedFileContents);
              sharedData.setWorkflowExecutionInput(workflowId, decodedFileContents);
            }
            //$scope.aceInput.focus();
          //}

        });
    };
    reader.readAsDataURL(file);
    };



     var refreshLog = function(_editor) {

       console.log('Loading workflow log: ' + sharedProperties.getWorkflowName());
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "retrieveAllWorkflowLogs", "data" : { "user" : { "token" : token } , "workflow" : { "id" : sharedProperties.getWorkflowId() } } })
       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('retrieveAllWorkflowLogs successfully called.');

             if (response.data.data.workflow.log != prevLogEntry) {

               var logStr = atob(response.data.data.workflow.log);

               logStr = logStr.replace(/\[2/g, "#@![2");

               var logArr = logStr.split('#@!');
               logArr.sort();

               $scope.aceLogSession.setValue(logArr.join(""));

               var n = $scope.aceLog.getValue().split("\n").length;
               $scope.aceLog.gotoLine(n, 0, true);
               $scope.aceInput.focus();

               prevLogEntry = response.data.data.workflow.log;
            }
            if (response.data.data.workflow.progress != prevProgressEntry) {


              //var logFile = $scope.aceLogSession.getDocument().getValue();
              var logFile = atob(response.data.data.workflow.log);

              var logArray = logFile.split(/\r?\n/);


              prevProgressEntry = response.data.data.workflow.progress;

              var progress = atob(response.data.data.workflow.progress);
              //console.log(progress);

              var prevExecutedFunction = "";
              var lastFunctionExecutionDate = 0;


              //if (workflowExecuted) {
              if (true) {
                var progArray = progress.split(/\r?\n/);


                var counter = 0;
                var ev = [];

                var execErr = 'Success';

                var functionExecId = "";
                var wfExecId = "";
                // [2019-10-07 19:36:07.272] [INFO] [b4caad66e93911e9b41f02dc5d3985be] [g] [__mfn_progress] b4caad66e93911e9b41f02dc5d3985be_46851328608099ff478b53c1a798a095-46851328608099ff478b53c1a798a095-g {"t_start_fork": 1570476966756.972, "t_start_pubutils": 1570476966766.0327, "t_start_sessutils": 1570476966774.294, "t_start_sapi": 1570476966774.2964, "t_start": 1570476966774.4314, "t_end": 1570476966775.858, "t_pub_start": 1570476966775.9727, "t_pub_end": 1570476967272.2407, "t_end_fork": 1570476967272.2407, "function_instance_id": "b4caad66e93911e9b41f02dc5d3985be_46851328608099ff478b53c1a798a095-46851328608099ff478b53c1a798a095-g"}
                const regex = /\[(.+?)\] \[(.+?)\] \[(.+?)\] \[(.+?)\] \[(.+?)\] (.+?) ({.+?})/;
                for (var i=0;i<progArray.length;i++) {
                  if ((m = regex.exec(progArray[i])) !== null) {
                    var e = JSON.parse(m[7]);
                    wfExecId = m[3];
                    var stateName = m[4];
                    var functionExecStart = e.t_start;
                    var functionExecEnd = e.t_end;
                    functionExecId = e.function_instance_id;

                    //var functionExecStart = progArray[i].split('function_exec_start=').pop().split(',').shift();
                    //var functionExecEnd = progArray[i].split('function_exec_end=').pop().split(',').shift();
                    //var entry_q = "";
                    //var fork_start = "";
                    //var pub_end = "";
                    //if (progArray[i].includes('entry_gq=')) {
                    //   entry_q = progArray[i].split('entry_gq=').pop().split(',').shift();
                    //} else if (progArray[i].includes('entry_lq=')) {
                    //   entry_q = progArray[i].split('entry_lq=').pop().split(',').shift();
                    //}
                    //if (progArray[i].includes('fork_start=')) {
                    //   fork_start = e.t_start_fork;
                    //}
                    //var pub_end = e.t_pub_end;

                    var dStart = new Date(parseFloat(functionExecStart));
                    var dEnd = new Date(parseFloat(functionExecEnd));

                    if (dStart == dEnd) {
                      dEnd = new Date(parseFloat(functionExecEnd+1));
                    }

                    if (!initialized) {
                      // initialize if no error
                      var options = {
                        editable: false,
                        verticalScroll: true,
                        min: new Date(dStart.getTime()-500),
                        zoomMin: 15,
                        zoomMax: 50000,
                        minHeight: '340px',
                        maxHeight: '340px',
                        margin: {
                          item: 20,
                          axis: 40
                        }
                      };

                      var container = document.getElementById('visualization');
                      items = new vis.DataSet({});
                      timeline = new vis.Timeline(container, items, options);

                      initialized = true;
                    }


                    if (functionExecId && !functionExecIds[functionExecId] && ((!workflowJson.hasOwnProperty('StartAt') || (!workflowJson.States[stateName] || workflowJson.States[stateName].Type!="Parallel")))) {

                      functionExecIds[functionExecId] = true;
                      if (functionExecIds[functionExecId]) {
                        //console.log('gEId:' + functionExecId);
                      }
                      var duration = dEnd.getTime() - dStart.getTime();
                      if (duration==0) {
                        duration = "<1ms";
                      } else {
                        duration = duration + "ms";
                      }
                      var logOutput = '';
                      var errorLine = '';
                      execErr = 'Success';
                      for (var t=0;t<logArray.length;t++) {
                        if (logArray[t].includes(stateName)) {
                          //console.log("ggg:" + stateName);
                          //console.log("ggg:" + logArray[t]);
                          var rawDate = logArray[t].substring(logArray[t].indexOf("[")+1,logArray[t].indexOf("]"));
                          rawDate = rawDate.replace(' ', 'T');
                          rawDate = rawDate.replace(',', '.');
                          //console.log(rawDate);
                          var logEntryDate = new Date(rawDate + "+00:00");
                          //console.log(logEntryDate.toString());
                          //console.log(dStart.toString());
                          //console.log(dEnd.toString());
                          if (logEntryDate >= dStart && logEntryDate <= dEnd) {
                            if (logArray[t].includes("ERROR")) {
                              execErr = 'Error';
                            }
                            var cutB = nthIndex(logArray[t],'[', 3);
                            var cutE = nthIndex(logArray[t],']', 3);
                            logArray[t] = logArray[t].replace(logArray[t].substring(cutB, cutE+1), "");
                            cutB = nthIndex(logArray[t],'[', 3);
                            cutE = nthIndex(logArray[t],']', 3);
                            var lStr = logArray[t].replace(logArray[t].substring(cutB, cutE+1), "");
                            if (!lStr.includes("(functionworker)")) {
                              logOutput += lStr + "<br>";
                            }

                            var f = t+1;

                            while (logArray[f] && !logArray[f].startsWith('[') && (f-t)<25) {
                              logOutput += logArray[f];
                              logOutput += "<br>";
                              f++;
                            }

                          }

                        }

                      }

                      toolTip = '<table style="width:100%;"><tr><th style="padding-bottom:10px;"><b>Function Log Output</b></th><th></th><th style="padding-left:20px;padding-bottom:10px;" valign="top"><b>Function Execution Statistics</b></th></tr><tr><td valign="top" style="width:750px;">' + truncate.apply(logOutput, [1200, true]) + '</td><td></td><td style="padding-left:20px;" valign="top">State Name: ' + stateName + '<br>Function Name: ' + state2FunctionMapping[stateName] + '<br>Status: ' + execErr + '<br><br>Duration: ' + duration + '<table><tr><td>Execution Start:&nbsp;</td><td>' + dateFormat(new Date(parseFloat(functionExecStart))) + '</td></tr><tr><td>Execution End:&nbsp;</td><td>' + dateFormat(new Date(parseFloat(functionExecEnd))) + '</td></tr></table>Exec Id: ' + wfExecId + '</td></tr></table>';


                      if (prevExecutedFunction!=stateName) {
                        executedFunctions.push(stateName);
                        prevExecutedFunction = stateName;
                        lastFunctionExecutionDate = parseFloat(functionExecStart);
                      }

                      //console.log('dStart:' + dStart.getTime());
                      //console.log('dEnd:' + dEnd.getTime());
                      if (dEnd.getTime() - dStart.getTime() > 0) {
                        ev[counter] = [{id: execCounter + counter, start: new Date(dStart.getTime()), end: new Date(dEnd.getTime()), content: stateName + " <span style='color:black;float:right;'>" + duration + "</span>", ttip: toolTip}];
                      } else {
                        ev[counter] = [{id: execCounter + counter, start: new Date(dStart.getTime()), end: new Date(dStart.getTime()+1), content: stateName + " <span style='color:black;float:right;'>&lt;1ms</span>", ttip: toolTip}];
                      }
                      if (execErr=='Error') {
                        ev[counter][0].style = "background-color: #f7a8a8; border-color: black;";
                      } else {
                        ev[counter][0].style = "background-color: #92d193; border-color: black;";
                      }
                      ev[counter][0].status = execErr;
                      counter++;

                    }
                  }
                }


                for (var t=0;t<logArray.length;t++) {
                  var rawDate = "";
                  if (logArray[t].includes("ERROR")) {

                    //console.log("Err:" + logArray[t]);
                    var logOutput = '';
                    var cutB = nthIndex(logArray[t],'[', 3);
                    var cutE = nthIndex(logArray[t],']', 3);
                    var stateName = logArray[t].substring(cutB+1, cutE);
                    //cutB = nthIndex(logArray[t],'[', 4);
                    //cutE = nthIndex(logArray[t],']', 4);
                    var lStr = logArray[t].replace(logArray[t].substring(cutB, cutE+1), "");

                    logOutput += lStr;
                    logOutput += "<br>";
                    var f = t+1;
                    while (logArray[f] && !logArray[f].startsWith('[')) {

                      logOutput += logArray[f];
                      logOutput += "<br>";
                      f++;
                    }

                    rawDate = logArray[t].substring(logArray[t].indexOf("[")+1,logArray[t].indexOf("]"));
                    rawDate = rawDate.replace(' ', 'T');
                    rawDate = rawDate.replace(',', '.');
                    var logEntryDate = new Date(rawDate + "+00:00");

                    var eLine = logOutput.lastIndexOf("line ");
                    if (eLine>=0) {
                      errorLine = logOutput.substr(eLine + 5, logOutput.length-1);
                      if (errorLine.indexOf(',')>0) {
                        errorLine = errorLine.substr(0, errorLine.indexOf(','));
                      } else {
                        errorLine = errorLine.substr(0, errorLine.indexOf('<br>'));
                      }
                      //console.log('lg:' + lastFunctionExecutionDate + ' ed:' + logEntryDate.getTime());
                      if (lastFunctionExecutionDate < logEntryDate.getTime()) {

                        codeError = state2FunctionMapping[stateName] + ':' + errorLine;
                        failedFunctions[0] = stateName;

                        $scope.workflowButtonLabel = "Go to Error";
                      }
                    }

                  }
                }

                //ev.sort(compareExecutionEvents);

                for (var i=0;i<ev.length;i++) {
                  execEvents[execCounter] = ev[i];
                  items.add(execEvents[execCounter]);
                  currentEntry = execCounter;
                  execCounter++;
                }

                if (initialized) {
                  timeline.on('itemover', function (properties) {
                    if (!popoverVisible) {
                      var logLines = (execEvents[properties.item][0].ttip.match(/<br>/g) || []).length;
                      //console.log('count:' + logLines);
                      logLines -= 12;
                      logLines = Math.max(0, logLines);
                      var marginTop = 11 - logLines;
                      if (marginTop>5 && logLines>0) {
                        marginTop-=4;
                      }
                      document.getElementById('popover').style.top = marginTop.toString() + '%';
                      if (logLines > 12) {
                      } else if (logLines > 20) {
                        document.getElementById('popover').style.top = '15%';
                      }
                      document.getElementById('popover').innerHTML = execEvents[properties.item][0].ttip;
                      document.getElementById('popover').style.display = 'block';
                      popoverVisible = true;
                    }
                  });
                  timeline.on('itemout', function (properties) {
                    if (popoverVisible) {
                      document.getElementById('popover').style.display = 'none';
                      popoverVisible = false;
                    }
                  });
                }
                 /*if (execErr && lastFunctionExecutionDate < logEntryDate.getTime()) {

                   setTimeout(function() { timeline.setWindow(new Date(logEntryDate.getTime()-300), new Date(logEntryDate.getTime()+450)) }, 500);
*/
                 if (counter>0) {

                   setTimeout(function() { timeline.setWindow(new Date(dStart.getTime()-((dEnd-dStart)*2)), new Date(dEnd.getTime()+((dEnd-dStart)*2))) }, 500);

                 }

               }

             }
             if (workflowExecuted) {
               if ($scope.activeTab==1) {
                 $scope.gTab = 0;
                 $timeout(function() {
                   document.getElementById('switchTabButton').click();
                   drawWorkflowGraph(workflowJson);
                 }, 50);
               } else {
                 drawWorkflowGraph(workflowJson);
               }
             }
             workflowExecuted = false;

           } else {
             console.log("Failure status returned by retrieveAllWorkflowLogs");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (executionModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during retrieveAllWorkflowLogs");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

     function compareExecutionEvents(a,b) {
       if (a[0].start < b[0].start)
         return -1;
       if (a[0].start > b[0].start)
         return 1;
       return 0;
     }

     function truncate( n, useWordBoundary ){
       if (this.length <= n) { return this; }
       var subString = this.substr(0, n-1);
       return (useWordBoundary
         ? subString.substr(0, subString.lastIndexOf(' '))
         : subString) + "&hellip;";
     };

     function colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curStateName, prevStateName, prevChoice, executed, parallelNext, prefix, wForNum) {
       var parallelNextState = parallelNext;
       var pfix = prefix;
       var waitForNum = wForNum;

       var pEnd = false;

       //console.log("curStateName:" + curStateName);

       //console.log(failedFunctions[0]);
       var curState = states[curStateName];
       if (curState.Resource && curState.Resource!="" && executed) {
         //console.log('gName:' + curState.Resource);
         var cFunction = '#bfc0c1';
         var cEdge = '#bfc0c1';
         var cWidth = '1';
         var gExec = false;
         var cDashes = false;
         if (prevChoice) {
           cDashes = true;
         }

         for (var k in executedFunctions) {
           //console.log("Executed function:" + executedFunctions[k]);
           if (executedFunctions[k]==curStateName) {

             gExec = true;
             cFunction = '#b7d6b1';
             cEdge = '#95a886';
             cWidth = 3;
             cDashes = false;
           }
         }
         if (failedFunctions[0]==curStateName) {
           cEdge = '#bfc0c1';

           cWidth = 3;
         }
         //console.log('eG:' + executedFunctions[k]);
         //console.log('index:' + workflowStateNames.indexOf(pfix + curStateName));
         workflowFunctions[workflowStateNames.indexOf(pfix + curStateName)+2].color = cFunction;
         if (prevStateName!="") {
           var insertedEdge = {from: workflowStateNames.indexOf(prevStateName)+2, to: workflowStateNames.indexOf(pfix + curStateName)+2, label: '', dashes: cDashes, color: {color: cEdge}, width: cWidth, length: 150, font: {align: 'middle'}};
           workflowEdges.push(insertedEdge);
         }
         if (curState.End) {
           if (parallelNextState) {
             if (waitForNum==0 || executedBranches<waitForNum) {
               var insertedEdge = {from: workflowStateNames.indexOf(pfix + curStateName)+2, to: workflowStateNames.indexOf(parallelNextState)+2, label: '', dashes: cDashes, color: {color: cEdge}, width: cWidth, length: 150, font: {align: 'middle'}};
               workflowEdges.push(insertedEdge);
               executedBranches++;
             }

             curState = workflowJson.States[parallelNextState];
             curStateName = parallelNextState;
             for (var k in executedFunctions) {
               if (executedFunctions[k]==curStateName) {
                 gExec = true;
                 cFunction = '#b7d6b1';
                 cEdge = '#95a886';
                 cWidth = 3;
                 cDashes = false;
               }
             }
             if (failedFunctions[0]==curStateName) {
               cEdge = '#bfc0c1';
               cWidth = 3;
             }
             workflowFunctions[workflowStateNames.indexOf(curStateName)+2].color = cFunction;
             if (curState.End && lastParallelNext!=parallelNextState) {
               pEnd = true;
               workflowFunctions[1].color = '#f7a8a8'; // light up 'end' marker
               var insertedEdge = {from: workflowStateNames.indexOf(curStateName)+2, to: 1, label: '', dashes: cDashes, color: {color: cEdge}, width: cWidth, length: 150, font: {align: 'middle'}};
               workflowEdges.push(insertedEdge);
               lastParallelNext = parallelNextState;
             }
             parallelNextState = "";
             pfix = "";
             waitForNum = 0;

           } else {
             if (gExec) {
               workflowFunctions[1].color = '#f7a8a8'; // light up 'end' marker
             }
             var insertedEdge = {from: workflowStateNames.indexOf(pfix + curStateName)+2, to: 1, label: '', dashes: cDashes, color: {color: cEdge}, width: cWidth, length: 150, font: {align: 'middle'}};
             workflowEdges.push(insertedEdge);
           }
         }
         if (failedFunctions[0]==curStateName) {
           workflowFunctions[workflowStateNames.indexOf(pfix + curStateName)+2].color = '#f7a8a8';

           workflowFunctions[1].color = '#bfc0c1'; // gray out 'end' marker

           if (!pEnd) {
             if (curState.Next && curState.Next!="") {
               colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curState.Next, pfix + curStateName, false, false, parallelNextState, pfix, waitForNum);
             }
           }

         } else {
           if (!pEnd) {
             if (curState.Next && curState.Next!="") {
               colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curState.Next, pfix + curStateName, false, gExec, parallelNextState, pfix, waitForNum);
             }
           }
         }
       } else {
         if (executed) {
           workflowFunctions[workflowStateNames.indexOf(pfix + curStateName)+2].color = '#b7d6b1';
           if (prevStateName!="" && !traversedStates.includes(pfix + curStateName)) {
             var insertedEdge = {from: workflowStateNames.indexOf(prevStateName)+2, to: workflowStateNames.indexOf(pfix + curStateName)+2, label: '', dashes: false, color: {color: '#95a886'}, width: 3, length: 150, font: {align: 'middle'}};
             workflowEdges.push(insertedEdge);
           }
         } else {
           workflowFunctions[workflowStateNames.indexOf(pfix + curStateName)+2].color = '#bfc0c1';
           if (prevStateName!="" && !traversedStates.includes(pfix + curStateName)) {
             var insertedEdge = {from: workflowStateNames.indexOf(prevStateName)+2, to: workflowStateNames.indexOf(pfix + curStateName)+2, label: '', dashes: prevChoice, color: {color: '#bfc0c1'}, width: 1, length: 150, font: {align: 'middle'}};
             workflowEdges.push(insertedEdge);
           }
         }
         if (curState.Type=='Choice') {
           if (curState.Default && curState.Default!="") {
             if (traversedStates.includes(pfix + curStateName)) {
               return;
             }
             traversedStates.push(pfix + curStateName);
             colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curState.Default, pfix + curStateName, true, executed, parallelNextState, pfix, waitForNum);
           }
           for (var i = 0;i<curState.Choices.length;i++) {

             colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curState.Choices[i].Next, pfix + curStateName, true, executed, parallelNextState, pfix, waitForNum);
           }
         } else if (curState.Type=="Parallel") {
           for (var i = 0;i<curState.Branches.length;i++) {
             if (curState.WaitForNumBranches) {
               waitForNum = curState.WaitForNumBranches[0];
               //console.log('WaitForNum:' + waitForNum);
             }
             colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, workflowJson.States[curStateName].Branches[i].States, workflowJson.States[curStateName].Branches[i].StartAt, curStateName, false, executed, workflowJson.States[curStateName].Next, curStateName + '|' + i + '|', waitForNum);
           }
         } else {
           if (curState.End) {
             if (executed) {
               workflowFunctions[1].color = '#f7a8a8'; // light up 'end' marker
               var insertedEdge = {from: workflowStateNames.indexOf(pfix + curStateName)+2, to: 1, label: '', dashes: false, color: {color: '#95a886'}, width: 3, length: 150, font: {align: 'middle'}};
               workflowEdges.push(insertedEdge);
             } else {
               var insertedEdge = {from: workflowStateNames.indexOf(pfix + curStateName)+2, to: 1, label: '', dashes: prevChoice, color: {color: '#bfc0c1'}, width: 1, length: 150, font: {align: 'middle'}};
               workflowEdges.push(insertedEdge);
             }

           }
           if (curState.Next && curState.Next!="") {
             if (traversedStates.includes(pfix + curStateName)) {
               return;
             }
             traversedStates.push(pfix + curStateName);
             colorExecutedFunctions(workflowFunctions, workflowStateNames, workflowJson, states, curState.Next, pfix + curStateName, false, executed, parallelNextState, pfix, waitForNum);
           }
         }
       }
     }

     function createStateToFunctionMap(workflowJson) {
       if (workflowJson.hasOwnProperty('StartAt')) {
         Object.keys(workflowJson.States).map(stateName => {
           if (stateName!="") {
             if (workflowJson.States[stateName].Resource && workflowJson.States[stateName].Resource!="") {
               state2FunctionMapping[stateName] = workflowJson.States[stateName].Resource;
             } else {
               state2FunctionMapping[stateName] = "n/a";
             }
             if (workflowJson.States[stateName].Type=="Parallel") {
               for (var i = 0;i<workflowJson.States[stateName].Branches.length;i++) {
                 Object.keys(workflowJson.States[stateName].Branches[i].States).map(parallelStateName => {
                   if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource && workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource!="") {
                     state2FunctionMapping[parallelStateName] = workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource;
                   } else {
                     state2FunctionMapping[parallelStateName] = "n/a";
                   }
                 });
               }
             }
           }
         });
       } else {
         for (var key in workflowJson.functions) {
           if (workflowJson.functions.hasOwnProperty(key)) {
             if (workflowJson.functions[key].name!="") {
               state2FunctionMapping[workflowJson.functions[key].name] = workflowJson.functions[key].name;
             }
           }
         }
       }
     }

     function drawWorkflowGraph(workflowJson) {

        var workflowFunctions = new Array();
        var workflowFunctionNames = new Array();
        workflowEdges = new Array();
        var counter = 2;
        var gName = "";
        workflowFunctions.push({id: 0, label: 'Start', x:10, shape: 'circle', color: '#b7d6b1'});
        workflowFunctions.push({id: 1, label: 'End', x:800, shape: 'circle', color: '#bfc0c1'});

        if (workflowJson.hasOwnProperty('StartAt')) {
          Object.keys(workflowJson.States).map(stateName => {
            if (stateName!="") {
              var stateLabel = stateName;
              var col = '#bfc0c1'; // grayed out
              if (workflowJson.States[stateName].Resource && workflowJson.States[stateName].Resource!="" && stateName != workflowJson.States[stateName].Resource) {
                stateLabel += '\n(' + workflowJson.States[stateName].Resource + ')';
              }
              var insertedFunction = {id: counter, label: stateLabel, color: col};
              workflowFunctionNames.push(stateName);
              workflowFunctions.push(insertedFunction);
              counter++;

              if (workflowJson.States[stateName].Type=="Parallel") {
                var prefix = stateName;

                for (var i = 0;i<workflowJson.States[stateName].Branches.length;i++) {
                  Object.keys(workflowJson.States[stateName].Branches[i].States).map(parallelStateName => {
                    stateLabel = parallelStateName;

                    if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource && workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource!="" && parallelStateName != workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource) {
                      stateLabel += '\n(' + workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource + ')';
                    }

                    var insertedFunction = {id: counter, label: stateLabel, color: col};

                    workflowFunctionNames.push(prefix + '|' + i + '|' + parallelStateName);
                    //console.log("Prefixed State Name:" + prefix + '|' + i + '|' + parallelStateName);
                    workflowFunctions.push(insertedFunction);
                    counter++;
                  });
                }
              }
            }
          });

          if (workflowJson.StartAt!="") {
            workflowEdges.push({from: 0, to: workflowFunctionNames.indexOf(workflowJson.StartAt)+2, label: '', dashes: false, color: {color: '#95a886'}, width: 3, length: 150, font: {align: 'middle'}});
          }
          lastParallelNext = "";
          executedBranches = 0;
          waitForNum = 0;
          traversedStates = new Array();
          colorExecutedFunctions(workflowFunctions, workflowFunctionNames, workflowJson, workflowJson.States, workflowJson.StartAt, "", false, true, "", "", 0);

        } else {

          for (var key in workflowJson.functions) {
            if (workflowJson.functions.hasOwnProperty(key)) {
              if (workflowJson.functions[key].name!="") {
                var col = '#bfc0c1'; // grayed out
                for (var k in executedFunctions) {
                  if (executedFunctions[k]==workflowJson.functions[key].name) {
                    col = '#b7d6b1';
                  }
                }
                if (failedFunctions[0]==workflowJson.functions[key].name) {
                  col = '#f7a8a8';
                  workflowFunctions[1].color = '#bfc0c1'; // gray out 'end' marker
                }

                var insertedFunction = {id: counter, label: workflowJson.functions[key].name, color: col};
                workflowFunctionNames.push(workflowJson.functions[key].name);
                workflowFunctions.push(insertedFunction);
                counter++;
              }
            }
          }
          if (workflowJson.entry!="") {
            workflowEdges.push({from: 0, to: workflowFunctionNames.indexOf(workflowJson.entry)+2, label: '', dashes: false, length: 100, color: {color: '#95a886'}, width: 3, font: {align: 'middle'}});
          }
          for (var key in workflowJson.functions) {
            if (workflowJson.functions.hasOwnProperty(key)) {
              if (workflowJson.functions[key].next) {
                if (workflowJson.functions[key].next!="") {
                  for (var i = 0;i<workflowJson.functions[key].next.length;i++) {
                    if (workflowJson.functions[key].name!="" && workflowJson.functions[key].next[i]!="") {
                      var col = '#bfc0c1'; // grayed out
                      var edgeWidth = 1;
                      var path = 'notExecuted';

                      for (var k=0; k<executedFunctions.length;k++) {
                        if (executedFunctions[k]==workflowJson.functions[key].name) {
                          //console.log('1st gr:' + executedFunctions[k] + ' 2nd gr:' + executedFunctions[k+1]);
                          if (k<executedFunctions.length-1 && executedFunctions[k+1]==workflowJson.functions[key].next[i]) {

                            path = 'executed';
                          }
                          if (k==executedFunctions.length-1 && failedFunctions.length==0 && workflowJson.functions[key].next[i]=='end') {
                            workflowFunctions[1].color = '#f7a8a8'; // light up 'end' marker
                            path = 'executed';
                          }
                          if (k==executedFunctions.length-1 && failedFunctions.length>0 && failedFunctions[0]==workflowJson.functions[key].next[i]) {
                            path = 'executed';
                          }
                        }
                      }

                      //console.log(workflowJson.functions[key].name + '->' + workflowJson.functions[key].next[i]);
                      //console.log('path:' + path);
                      if (path=='executed') {
                          col = '#95a886';
                          edgeWidth = 3;
                      }
                      var insertedEdge = {from: workflowFunctionNames.indexOf(workflowJson.functions[key].name)+2, to: workflowFunctionNames.indexOf(workflowJson.functions[key].next[i])+2, label: '', dashes: false, length: 100, color: {color: col}, width: edgeWidth, font: {align: 'middle'}};
                      workflowEdges.push(insertedEdge);
                    }
                  }
                }
              }
            }
          }

          for (var key in workflowJson.functions) {
            if (workflowJson.functions.hasOwnProperty(key)) {
              if (workflowJson.functions[key].potentialNext) {
                if (workflowJson.functions[key].potentialNext!="") {
                  for (var i = 0;i<workflowJson.functions[key].potentialNext.length;i++) {
                    if (workflowJson.functions[key].name!="" && workflowJson.functions[key].potentialNext[i]!="") {
                      var col = '#bfc0c1'; // grayed out
                      var edgeWidth = 1;
                      var path = 'notExecuted';

                      for (var k=0; k<executedFunctions.length;k++) {
                        if (executedFunctions[k]==workflowJson.functions[key].name) {
                          if (k<executedFunctions.length-1 && executedFunctions[k+1]==workflowJson.functions[key].potentialNext[i]) {
                            path = 'executed';
                          }
                          if (k==executedFunctions.length-1 && failedFunctions.length==0 && workflowJson.functions[key].potentialNext[i]=='end') {
                            path = 'executed';
                            workflowFunctions[1].color = '#f7a8a8'; // light up 'end' marker
                          }
                          if (k==executedFunctions.length-1 && failedFunctions.length>0 && failedFunctions[0]==workflowJson.functions[key].potentialNext[i]) {
                            path = 'executed';
                          }
                        }
                      }

                      if (path=='executed') {
                          col = '#95a886';
                          edgeWidth = 3;
                      }
                      //console.log(workflowJson.functions[key].name + '->' + workflowJson.functions[key].potentialNext[i]);
                      //console.log('path:' + path);
                      var insertedEdge = {from: workflowFunctionNames.indexOf(workflowJson.functions[key].name)+2, to: workflowFunctionNames.indexOf(workflowJson.functions[key].potentialNext[i])+2, label: '', dashes: true, color: {color: col}, width: edgeWidth, length: 100, font: {align: 'middle'}};
                      workflowEdges.push(insertedEdge);
                    }
                  }
                }
              }
            }
          }
        }

        var edges = new vis.DataSet(workflowEdges);
        var nodes = new vis.DataSet(workflowFunctions);

        // create a workflow graph
        var container = document.getElementById('workflowGraph');
        var data = {
            nodes: nodes,
            edges: edges
        };

        var options = {
          autoResize: true,
          interaction:{hover:false},
          physics:{
            stabilization: true
          },
          layout: {randomSeed:0},
          manipulation: {
            enabled: false,
            initiallyActive: false,
          },
          nodes: {
             shape: 'box',
             size: 50,

             font: {
                 size: 14
             },
             borderWidth: 2,
             shadow:true
         },
         edges: {
             width: 2,
             shadow:true,
             color: {
               inherit: false
             },
             arrows:{
               to: {
                 enabled: true,
                 type: 'arrow'
               }
             }
         }
        };

        var network = new vis.Network(container, data, options);

        network.fit();
        network.once('initRedraw', function() {
          network.moveTo({offset:{x: (0.5 * 1000),y: (0.5 * 400)}});
        });

     }

    function retrieveWorkflowJson() {
       console.log('Loading workflow JSON:' + sharedProperties.getWorkflowName());
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "getWorkflowJSON", "data" : { "user" : { "token" : token } , "workflow" : { "id" : sharedProperties.getWorkflowId() } } })

       }

       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Workflow JSON sucessfully downloaded.');

             if (response.data.data.workflow.json) {

               workflowJson = JSON.parse(atob(response.data.data.workflow.json));
               createStateToFunctionMap(workflowJson);

             }

           } else {
             console.log("Failure status returned by getWorkflowJSON");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (executionModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getWorkflowJSON");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       });

     }

     $scope.zoomIn = function() {
       if (timeline) {
         timeline.zoomIn(1);
       }
     }

     $scope.zoomOut = function() {
       if (timeline) {
         timeline.zoomOut(1);
       }
     }

     $scope.goBack = function() {

       if (currentEntry>=1 && execEvents[currentEntry-1]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 1px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 1px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         currentEntry = currentEntry - 1;

       }
       if (execEvents[currentEntry]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 2px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 2px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         timeline.moveTo(execEvents[currentEntry][0].end, false);
       }
     }

     $scope.goBackFast = function() {

       if (currentEntry>=5 && execEvents[currentEntry-5]) {

         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 1px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 1px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         currentEntry = currentEntry - 5;

       }
       if (execEvents[currentEntry]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 2px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 2px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         timeline.moveTo(execEvents[currentEntry][0].end, false);
       }
     }

     $scope.goForward = function() {

       if (execEvents[currentEntry+1]) {
          if (execEvents[currentEntry][0].status == "Success") {
            execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 1px; border-color: black;";
          } else {
            execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 1px; border-color: black;";
          }
          items.update(execEvents[currentEntry][0]);
          currentEntry = currentEntry + 1;
       }

       if (execEvents[currentEntry]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 2px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 2px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         timeline.moveTo(execEvents[currentEntry][0].end, false);
       }
     }

     $scope.goForwardFast = function() {

       if (execEvents[currentEntry+5]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 1px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 1px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         currentEntry = currentEntry + 5;
       }

       if (execEvents[currentEntry]) {
         if (execEvents[currentEntry][0].status == "Success") {
           execEvents[currentEntry][0].style = "background-color: #92d193; border-width: 2px; border-color: black;";
         } else {
           execEvents[currentEntry][0].style = "background-color: #f7a8a8; border-width: 2px; border-color: black;";
         }
         items.update(execEvents[currentEntry][0]);
         timeline.moveTo(execEvents[currentEntry][0].end, false);
       }
     }

     $scope.scrollToEndOfLogFile = function() {
       $timeout(function() {
         var n = $scope.aceLog.getValue().split("\n").length;
         $scope.aceLog.gotoLine(n, 0, true);
         $scope.aceLog.focus();
       }, 350);

     }

     function dateFormat(d) {
       var format = "Y-m-d H:i:s.v";

       return format
         .replace(/Y/gm, d.getFullYear().toString())
         .replace(/m/gm, ('0' + (d.getMonth() + 1)).substr(-2))
         .replace(/d/gm, ('0' + (d.getDate())).substr(-2))
         .replace(/H/gm, ('0' + (d.getHours() + 0)).substr(-2))
         .replace(/i/gm, ('0' + (d.getMinutes() + 0)).substr(-2))
         .replace(/s/gm, ('0' + (d.getSeconds() + 0)).substr(-2))
         .replace(/v/gm, ('0000' + (d.getMilliseconds() % 1000)).substr(-3));
     }

     function nthIndex(str, pat, n) {
        var L = str.length, i= -1;
        while(n-- && i++<L){
          i= str.indexOf(pat, i);
          if (i < 0) break;
        }
      return i;
     }

     $scope.getWorkflowId = function() {
        return workflowId;
     }

     $scope.getWorkflowName = function() {
        return workflowName;
     }

     $scope.getWorkflowStatus = function() {
        return workflowStatus;
     }

     $scope.getWorkflowUrl = function() {
        return workflowUrl;
     }

     $scope.getCodeError = function() {
       return codeError;
     }


     $scope.executeWorkflow = function() {

       return new Promise(resolve => {

         $scope.workflowButtonLabel = "Workflow Editor";

         executedFunctions = [];
         failedFunctions = [];

         $interval.cancel(inter);

         codeError = "";

         var inputData = {};
         var input = $scope.aceInputSession.getDocument().getValue();

         if (input=="") {
           input = "\"\"";
         }

         if (JSON.stringify($scope.aceInputSession.getAnnotations()).includes('"type":"error"')) {
           console.log("Invalid workflow input.");
           $scope.errorMessage = "The workflow input does not contain valid JSON Text.";
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
             $scope.aceInput.focus();
           }
           resolve();
           return;
         }

         if (workflowName.endsWith("   ")) {
           // test function
           sharedData.setWorkflowExecutionInputEditor("mfn-internal-" + workflowName, input);
           sharedData.setWorkflowExecutionInput("mfn-internal-" + workflowName, input);
         } else {
           // execute workflow
           sharedData.setWorkflowExecutionInputEditor(workflowId, input);
           sharedData.setWorkflowExecutionInput(workflowId, input);
         }

         inputData = JSON.parse(input);

         var workflowUrl = sharedProperties.getWorkflowUrl();
         var token = $cookies.get('token');

        var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "executeWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId, "wfurl": workflowUrl, "wfinput": inputData } } })
        }

         intervalCounter = 0;

         //setTimeout(function() { prepareLogFile(); }, 3000);

         setTimeout(function() { inter = $interval(function(){prepareLogFile();}, 3000); }, 250);

         $http(req).then(function successCallback(response) {

                //console.log(response.data);
                //console.log(atob(response.data.data.workflow.log));

               //setTimeout(function() { promise = $interval(function(){prepareLogFile();}, 3000); }, 500);

               $interval.cancel(inter);

               setTimeout(function() { prepareLogFile(); }, 500);
               setTimeout(function() { workflowExecuted = true; prepareLogFile(); }, 4500);

               //showTimeline();
               if (response.data.status=="success") {
                   console.log("executeWorkflow called succesfully.");
                   result = response.data.data.result;
                   document.getElementById('execOutput').innerHTML = result;

                   var jObj = result;
                   if (typeof jObj == 'string') {
                     $scope.aceOutputSession.setValue(result);
                   } else {
                     $scope.aceOutputSession.setValue(JSON.stringify(result, null, 4));
                   }
                   resolve();

               } else {
                 console.log("Failure status returned by executeWorkflow");
                 console.log("Message:" + response.data.data.message);
                 $scope.errorMessage = response.data.data.message;
                 if (executionModalVisible) {
                   $uibModal.open({
                     animation: true,
                     scope: $scope,
                     templateUrl: 'app/pages/workflows/modals/errorModal.html',
                     size: 'md',
                   });
                 }
               }
         }, function errorCallback(response) {
             console.log("Error occurred during workflow execution");
             console.log("Response:" + response);
             $interval.cancel(inter);
             //$interval.cancel(promise);
             if (response.statusText) {
               $scope.errorMessage = response.statusText;
               console.log(response.statusText);
               setTimeout(function() { prepareLogFile(); resolve();}, 500);
             } else {
               $scope.errorMessage = response;
               console.log(response);
               setTimeout(function() { prepareLogFile(); resolve();}, 500);
             }
             toastr.error('Workflow Execution Error: ' + $scope.errorMessage);
             $interval.cancel(inter);
             /*if (executionModalVisible) {
              $uibModal.open({
                animation: true,
                scope: $scope,
                templateUrl: 'app/pages/workflows/modals/errorModal.html',
                size: 'md',
              });
            }*/
         });
        //return $timeout(function() {}, 8000);
       });
     };


     $scope.$on('$destroy', function(){
         executionModalVisible = false;
         $interval.cancel(inter);
     });

     $scope.getWorkflowName = function() {
       return sharedProperties.getWorkflowName();
     }

     $scope.getWorkflowId = function() {
       return sharedProperties.getWorkflowId();
     }

     $scope.getFunctionId = function() {
       return sharedProperties.getFunctionId();
     }

     $scope.getFunctionRuntime = function() {
      return sharedProperties.getFunctionRuntime();
    }

     $scope.undeployTemporaryWorkflow = function(workflowId) {
       var req;
       var token = $cookies.get('token');
       //console.log('deployWorkflow,' + action + ',' + index + ',' + $scope.workflows[index].status);

       console.log('undeploying workflow ' + workflowId);

       req = {
         method: 'POST',
         url: urlPath,
         headers: {
          'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "undeployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId } } })
       }

       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {

               setTimeout(function() { deleteTemporaryWorkflow(workflowId);}, 2000);

           } else {
             console.log("Failure status returned by deploy/undeployWorkflow");
             console.log("Message:" + response.data.data.message);
             if (action=="deploy") {
               $scope.workflows[index].status='undeployed';
             }
             $scope.errorMessage = response.data.data.message;
             if (executionModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during deploy/undeployWorkflow");
           console.log("Response:" + response);
           if (action=="deploy") {
             $scope.workflows[index].status='undeployed';
           }
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       });

     }

     function deleteTemporaryWorkflow(workflowId) {
       console.log('deleting workflow ' + workflowId);
       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
            'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "deleteWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId } } })
       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Temporary workflow sucessfully deleted.');

           } else {
             console.log("Failure status returned by deleteWorkflow");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (executionModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during deleteWorkflow");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       });
     }

     $scope.aceInputLoaded = function(_editor) {
       $scope.aceInputSession = _editor.getSession();
       $scope.aceInput = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.focus();
       if (workflowName.endsWith("   ")) {
         // test function
         if (sharedData.getWorkflowExecutionInputEditor("mfn-internal-" + workflowName)) {
           $scope.aceInputSession.setValue(sharedData.getWorkflowExecutionInputEditor("mfn-internal-" + workflowName));
           fileContents = sharedData.getWorkflowExecutionInput("mfn-internal-" + workflowName);
         }
       } else {
         // execute workflow
         if (sharedData.getWorkflowExecutionInputEditor(workflowId)) {
           $scope.aceInputSession.setValue(sharedData.getWorkflowExecutionInputEditor(workflowId));
           fileContents = sharedData.getWorkflowExecutionInput(workflowId);
         }
       }

       //setTimeout(function() {createTimeline();}, 300);

     }

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceInput.focus();
       }, 350);

     }

     $scope.reloadLog =function() {
       prepareLogFile();
     }

     $scope.clearLog =function() {

       console.log('Deleting workflow log: ' + sharedProperties.getWorkflowId());
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:  JSON.stringify({ "action" : "clearAllWorkflowLogs", "data" : { "user" : { "token" : token } , "workflow" : { "id" : sharedProperties.getWorkflowId() } } })

       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('clearAllWorkflowLogs successfully called.');
             $scope.aceLogSession.setValue("");
           } else {
             console.log("Failure status returned by clearAllWorkflowLogs");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (executionModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during clearAllWorkflowLogs");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (executionModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       });
     }

     function prepareLogFile() {
       if (inter) {
         intervalCounter++;
         //console.log('iC:' + intervalCounter);
       }

       if (intervalCounter>=15) {
         $interval.cancel(inter);
         return;
       }
       console.log('Loading workflow log: ' + sharedProperties.getWorkflowId());
       setTimeout(function() { refreshLog($scope.aceLogSession); }, 500);

     }

    function createTimeline() {

      var options = {
        editable: false,
        verticalScroll: true,
        min: new Date(new Date().getTime()-2000),
        zoomMin: 50,
        zoomMax: 5000,
        minHeight: '210px',
        margin: {
          item: 20,
          axis: 40
        }
      };


      var container = document.getElementById('visualization');

      items = new vis.DataSet({});
      timeline = new vis.Timeline(container, items, options);


    }

     $scope.aceOutputLoaded = function(_editor) {

       $scope.aceOutputSession = _editor.getSession();
       $scope.aceOutput = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.$readOnly = true;

     }

     $scope.aceLogLoaded = function(_editor) {

       $scope.aceLogSession = _editor.getSession();
       $scope.aceLog = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.$readOnly = true;
       console.log('Loading workflow log: ' + sharedProperties.getWorkflowId());
       setTimeout(function() { refreshLog($scope.aceLogSession); }, 500);

     }
   });


}());
