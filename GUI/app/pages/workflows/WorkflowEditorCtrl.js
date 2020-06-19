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
  angular.module('MfnWebConsole').controller('WorkflowEditorCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties, sharedData) {

     var complNum = 0;

     // retrieve JSON schema definitions for ASL workflow validation

     var task = $.getJSON("lib/asl-validator/schemas/task.json", function(json) {
     });

     var choice = $.getJSON("lib/asl-validator/schemas/choice.json", function(json) {
     });

     var fail = $.getJSON("lib/asl-validator/schemas/fail.json", function(json) {
     });

     var mapState = $.getJSON("lib/asl-validator/schemas/map.json", function(json) {
     });

     var parallel = $.getJSON("lib/asl-validator/schemas/parallel.json", function(json) {
     });

     var wait = $.getJSON("lib/asl-validator/schemas/wait.json", function(json) {
     });

     var state = $.getJSON("lib/asl-validator/schemas/state.json", function(json) {
     });

     var stateMachine = $.getJSON("lib/asl-validator/schemas/state-machine.json", function(json) {
     });

     var pass = $.getJSON("lib/asl-validator/schemas/pass.json", function(json) {
     });

     var succeed = $.getJSON("lib/asl-validator/schemas/succeed.json", function(json) {
     });

     // KNIX extensions to ASL
     var knix_task = $.getJSON("lib/knix-asl-validator/schemas/task.json", function(json) {
     });

     var knix_choice = $.getJSON("lib/knix-asl-validator/schemas/choice.json", function(json) {
     });

     var knix_fail = $.getJSON("lib/knix-asl-validator/schemas/fail.json", function(json) {
     });

     var knix_mapState = $.getJSON("lib/knix-asl-validator/schemas/map.json", function(json) {
     });

     var knix_parallel = $.getJSON("lib/knix-asl-validator/schemas/parallel.json", function(json) {
     });

     var knix_wait = $.getJSON("lib/knix-asl-validator/schemas/wait.json", function(json) {
     });

     var knix_state = $.getJSON("lib/knix-asl-validator/schemas/state.json", function(json) {
     });

     var knix_stateMachine = $.getJSON("lib/knix-asl-validator/schemas/state-machine.json", function(json) {
     });

     var knix_pass = $.getJSON("lib/knix-asl-validator/schemas/pass.json", function(json) {
     });

     var knix_succeed = $.getJSON("lib/knix-asl-validator/schemas/succeed.json", function(json) {
     });

     var urlPath = sharedProperties.getUrlPath();

     var dataPrefix = sharedProperties.getDataPrefix();

     var codeError = sharedProperties.getCodeError();

     var token = $cookies.get('token');

     var mfnAPI = [ {"word" : "log(\"\")", "score" : 1008 },
                     {"word" : "get(\"\")", "score" : 1007}, {"word" : "put()", "score" : 1006}, {"word" : "delete(\"\")", "score" : 1005} ];
     var mfnAPITooltip = [ {"command" : "log()", "ttip" : "<b>log(text)</b><br><br>Log text. Uses the instance id to indicate which function instance logged the text.<br><br><b>Args:</b><br>text (string): text to be logged.<br><br><b>Returns:</b><br>None.<br><br><b>Raises:</b><br>MicroFunctionsUserLogException: if there are any errors in the logging function."},
     {"command" : "put()", "ttip" : "<b>put(key, value, is_private=False, is_queued=False)</b><br><br>Access to data layer to store a data item in the form of a (key, value) pair.<br>By default, the put operation is reflected on the data layer immediately.<br>If the put operation is queued (i.e., is_queued = True), the data item is put into the transient data table.<br>If the key was previously deleted by the function instance, it is removed from the list of items to be deleted.<br>When the function instance finishes, the transient data items are committed to the data layer.<br><br><b>Args:</b><br>key (string): the key of the data item<br>value (string): the value of the data item<br>is_private (boolean): whether the item should be written to the private data layer of the workflow; default: False<br>is_queued (boolean): whether the put operation should be reflected on the data layer after the execution finish; default: False<br><br><b>Returns:</b><br>None<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key and/or value are not a strings."},
     {"command" : "get(\"\")", "ttip" : "<b>get(key, is_private=False)</b><br><br>Access to data layer to load the value of a given key. The key is first checked in the transient deleted items.<br>If it is not deleted, the key is then checked in the transient data table. If it is not there,<br>it is retrieved from the global data layer. As a result, the value returned is consistent with what this function<br>instance does with the data item. If the data item is not present in either the transient data table<br>nor in the global data layer, an empty string (i.e., \"\") will be returned.<br>If the function used put() and delete() operations with is_queued = False (default), then the checks<br>of the transient table will result in empty values, so that the item will be retrieved<br>from the global data layer.<br><br><b>Args:</b><br>key (string): the key of the data item<br>is_private (boolean): whether the item should be read from the private data layer of the workflow; default: False<br><br><b>Returns:</b><br>value (string): the value of the data item; empty string if the data item is not present.<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key is not a string."},
    {"command" : "delete(\"\")", "ttip" : "<b>delete(key, is_private=False, is_queued=False)</b><br><br>Access to data layer to delete data item associated with a given key.<br>By default, the delete operation is reflected on the data layer immediately.<br>If the delete operation is queued (i.e., is_queued = True), the key is removed from the transient data table.<br>It is also added to the list of items to be deleted from the global data layer when the function instance finishes.<br><br><b>Args:</b><br>key (string): the key of the data item<br>is_private (boolean): whether the item should be deleted from the private data layer of the workflow; default: False<br>is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False<br><br><b>Returns:</b><br>None<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key is not a string."}
    ];

     //var workflowBlueprint = '{\r\n\t"name": "' + sharedProperties.getWorkflowName() + '",\r\n\t"entry": "",\r\n\t"functions": [\r\n\t\t{\r\n\t\t\t"name": "",\r\n\t\t\t"next": ["end"]\r\n\t\t}\r\n\t]\r\n}';
     var workflowBlueprint = '{\r\n\t"Comment": "' + sharedProperties.getWorkflowName() + ' Workflow",\r\n\t"StartAt": "",\r\n\t"States": {\r\n\t\t"": {\r\n\t\t\t"Type": "Task",\r\n\t\t\t"Resource": "",\r\n\t\t\t"End": true\r\n\t\t}\r\n\t}\r\n}';

     $scope.showFunctionCodeTab = new Array(10);
     $scope.changedBuffers = "";
     var functionCodeEditor = new Array(10);
     var functionCodeBuffer = new Array(10);
     var functionCodeName = new Array(10);
     var nodeToTabMapping = new Array();
     var workflowBuffer = "";

     var functionCode = "";

     $scope.activeTab = 0;
     $scope.gTab = 0;
     $scope.initiatedAction = "";
     $scope.sObjects = [ ];

     getStorageObjectsList();

     for (var i=0;i<10;i++) {
       $scope.showFunctionCodeTab[i] = false;
       functionCodeName[i] = "";
     }

     $scope.functions = sharedData.getFunctions();

     if (!$scope.functions) {
       getFunctions();
     }

     var workflowJson = { };

     var vm = $scope;
     vm.file_changed = function(element){
     var textFile = element.files[0];
     var reader = new FileReader();
     reader.onload = function(e){
        vm.$apply(function(){
            $scope.aceSession.setValue(reader.result);
        });
    };
    reader.readAsText(textFile);
    };

    $scope.aceFunction0Loaded = function(_editor) {
      functionCodeEditor[0] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction1Loaded = function(_editor) {
      functionCodeEditor[1] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction2Loaded = function(_editor) {
      functionCodeEditor[2] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction3Loaded = function(_editor) {
      functionCodeEditor[3] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction4Loaded = function(_editor) {
      functionCodeEditor[4] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction5Loaded = function(_editor) {
      functionCodeEditor[5] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction6Loaded = function(_editor) {
      functionCodeEditor[6] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction7Loaded = function(_editor) {
      functionCodeEditor[7] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction8Loaded = function(_editor) {
      functionCodeEditor[8] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }
    $scope.aceFunction9Loaded = function(_editor) {
      functionCodeEditor[9] = _editor;
      _editor.on("blur", function() { _editor.completer.detach(); });
      _editor.commands.on("afterExec", function (e) {
        if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
          _editor.execCommand("startAutocomplete");
        }
      });
    }



     $scope.aceLoaded = function(_editor) {
       $scope.aceSession = _editor.getSession();
       _editor.on("blur", function() { _editor.completer.detach(); });

       _editor.completers.push({
              getCompletions: function(editor, session, pos, prefix, callback) {

                  var line = session.getLine(editor.getCursorPosition().row);

                  var wordList = [ ];
                  var metaLabel = "";

                  if (undefined !== line) {

                    if (line.includes('context.delete') || line.includes('context.get') || line.includes('context.put')) {
                      wordList = $scope.sObjects;
                      metaLabel = "Storage Object";

                    } else if (line.includes('"next"') || line.includes('"name"') || line.includes('"potentialNext"') || line.includes('"entry"')
                      || line.includes('"Resource"') || (line.includes('"Next"') && !session.getDocument().getValue().includes('"StartAt"')) || line.includes('"Name"') || line.includes('"PotentialNext"') || line.includes('"Entry"'))  {

                        var score = 2000;
                        for (var key in $scope.functions) {
                          wordList.push({"word": $scope.functions[key].name, "score": score});
                          score--;
                        }
                        metaLabel = "Function";

                    } else if (line.includes('context.')) {

                    wordList = mfnAPI;
                    metaLabel = "MFN API";
                    }
                  }
                  callback(null, wordList.map(function(ea) {
                      return {
                          caption: ea.word,
                          value: ea.word,
                          completer: {
                              insertMatch: function (editor, data) {
                                  var currline = editor.getSelectionRange().start.row;
                                  var wholelinetxt = editor.session.getLine(currline);
                                  /*console.log (wholelinetxt);
                                  console.log (wholelinetxt[wholelinetxt.length-1]);
                                  console.log (wholelinetxt[wholelinetxt.length-2]);
                                  console.log (wholelinetxt[wholelinetxt.length-3]);*/

                                  if (wholelinetxt.length>1 && wholelinetxt[wholelinetxt.length-1]!='.' && wholelinetxt[wholelinetxt.length-1]!='"' && wholelinetxt[wholelinetxt.length-2]!='(') {
                                  //if (wholelinetxt.length>1 && (wholelinetxt[wholelinetxt.length-1]!='.'  && (wholelinetxt[wholelinetxt.length-2]!='"' || wholelinetxt[wholelinetxt.length-1]!='"'))) {
                                    if (wholelinetxt.length>2 && wholelinetxt[wholelinetxt.length-3]!='"') {
                                      editor.removeWordLeft();
                                    } else if (wholelinetxt.length==2) {
                                      editor.removeWordLeft();
                                    }
                                  }

                                  editor.insert(data.value);
                                  if (data.value.indexOf('()')==data.value.length-2) {
                                    var pos = editor.selection.getCursor(); //Take the latest position on the editor
                                    editor.moveCursorTo(pos.row, pos.column -1);
                                  } else if (data.value.indexOf('("")')==data.value.length-4) {
                                    var pos = editor.selection.getCursor(); //Take the latest position on the editor
                                    editor.moveCursorTo(pos.row, pos.column-2);
                                  }
                                  if (data.value.indexOf('delete("")')==data.value.length-10 || data.value.indexOf('get("")')==data.value.length-7 || data.value.indexOf('put()')==data.value.length-5) {
                                    $timeout(function() {
                                      editor.execCommand("startAutocomplete");
                                    }, 50);
                                  }

                              }
                          },
                          score: ea.score,
                          ttip: ea.ttip,
                          meta: metaLabel

                      };
                  }));

              },
              getDocTooltip: function(item) {
                if (item.meta == "MFN API" && !item.docHTML) {
                    for (var command in mfnAPITooltip) {
                      if (mfnAPITooltip[command].command==item.caption) {

                        item.docHTML = mfnAPITooltip[command].ttip;
                      }
                    }

                } else if (item.meta == "Function" && !item.docHTML) {
                    for (var key in $scope.functions) {
                      if ($scope.functions[key].name==item.caption) {
                        getFunctionCode(item.caption, $scope.functions[key].id, $scope.functions[key].runtime, null, -1).then(function(code) {
                          item.docHTML = code;
                          return;
                        });
                      }
                    }

                }
              }
          });

        _editor.commands.on("afterExec", function (e) {
          if (e.command.name == "insertstring" && (/^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
            _editor.execCommand("startAutocomplete");
          }
        });

        complNum = _editor.completers.length;

       $scope.aceWorkflowEditor = _editor;
       _editor.$blockScrolling = Infinity;

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
               _editor.getSession().setValue(atob(response.data.data.workflow.json));
               workflowJson = JSON.parse(atob(response.data.data.workflow.json));
               workflowBuffer = atob(response.data.data.workflow.json);
               setTimeout(function(){ enableFunctionCodeTabs(workflowJson); }, 250);
               drawWorkflowGraph(workflowJson);
             } else {
               _editor.getSession().setValue(workflowBlueprint);
               $scope.saveChanges(true);
               workflowBuffer = workflowBlueprint;
             }
             // decoding and inserting workflow JSON file into inline editor

             _editor.focus();

           } else {
             console.log("Failure status returned by getWorkflowJSON");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getWorkflowJSON");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });

       });

     };

     $scope.deployLabel = function() {
       if (sharedProperties.getWorkflowStatus()=='deployed') {
         return "Re-deploy and execute";
       } else {
         return "Deploy and execute";
       }
     }

     function getStorageObjectsList() {

       var path = "/storage/";
       var email = $cookies.get('email');
       var token = $cookies.get('token');

       var req = {
         method: 'GET',
         url: path + "?token=" + token + "&email=" + email + "&table=defaultTable&action=listKeys&start=0&count=500",
         headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
         }
       }

       $http(req).then(function successCallback(response) {

           $scope.sObjects = [ ];
           var score = 2000;

           for (var i=0;i<response.data.length;i++) {
             if (!response.data[i].startsWith("grain_requirements_") && !response.data[i].startsWith("grain_source_") && !response.data[i].startsWith("workflow_json_")) {
               $scope.sObjects.push({"word" : response.data[i], "score": score});
               score--;
             }
           }


       }, function errorCallback(response) {
           console.log("Error occurred during listKeys action");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });
       });
     }

     $scope.getFunctionName = function(id) {

       return functionCodeName[id];

     };


     $scope.closeDialog = function() {

       //$scope.aceWorkflowEditor.remove(complNum-1);
       var dirty = false;
       $scope.changedBuffers = "";
       if (workflowBuffer != $scope.aceSession.getDocument().getValue()) {
         dirty = true;
         $scope.changedBuffers = $scope.getWorkflowName();
       }
       for (var i=0;i<10;i++) {
         if ($scope.showFunctionCodeTab[i] == true && functionCodeBuffer[i]!=functionCodeEditor[i].getSession().getDocument().getValue()) {
           dirty = true;
           if ($scope.changedBuffers != "") {
             $scope.changedBuffers += ", ";
           }
           $scope.changedBuffers += functionCodeName[i];
         }
       }

       if (dirty) {
         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/workflows/modals/closeWorkflowEditorModal.html',
           size: 'md',
         });
       } else {
         $timeout(function() {
           document.getElementById('closeButton').click();
         }, 50);

       }
     }

     $scope.closeModal = function() {
       if ($scope.initiatedAction=="execute") {
         $scope.openWorkflowExecutionModal(sharedProperties.getWorkflowId());
       } else if ($scope.initiatedAction=="deployAndExecute") {
         $scope.deployAndExecuteWorkflow(sharedProperties.getWorkflowId());
       }
       $scope.initiatedAction = "";
       $timeout(function() {
         document.getElementById('closeButton').click();
       }, 50);
     }

     $scope.aceChanged = function(e) {

     };

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceWorkflowEditor.focus();
       }, 350);

     }

     $scope.getWorkflowName = function() {
       return sharedProperties.getWorkflowName();
     }

     $scope.getWorkflowStatus = function() {
       if (sharedProperties.getWorkflowStatus()=='deployed') {
         return true;
       } else {
         return false;
       }
     }



     function drawWorkflowGraph(workflowJson) {



        var workflowFunctions = new Array();
        var workflowFunctionNames = new Array();
        var workflowEdges = new Array();
        var counter = 2;
        nodeToTabMapping = [];
        workflowFunctions.push({id: 0, label: 'Start', x:10, shape: 'circle', color: '#b7d6b1'});
        workflowFunctions.push({id: 1, label: 'End', x:800, shape: 'circle', color: '#f7a8a8'});

        if (workflowJson.hasOwnProperty('StartAt')) {
          Object.keys(workflowJson.States).map(stateName => {
            nodeToTabMapping[counter] = -1;
            if (stateName!="") {
              var stateLabel = stateName;
              if (workflowJson.States[stateName].Resource && workflowJson.States[stateName].Resource!="" && stateName != workflowJson.States[stateName].Resource) {
                stateLabel += '\n(' + workflowJson.States[stateName].Resource + ')';
                for (var i=0;i<10;i++) {
                  if (functionCodeName[i]==workflowJson.States[stateName].Resource)
                  nodeToTabMapping[counter] = i;
                }
              }

              var insertedFunction = {id: counter, label: stateLabel, color: 'rgb(121, 204, 229,1.0)'};
              workflowFunctionNames.push(stateName);
              workflowFunctions.push(insertedFunction);
              counter++;

              if (workflowJson.States[stateName].Type=="Parallel") {
                for (var i = 0;i<workflowJson.States[stateName].Branches.length;i++) {
                  Object.keys(workflowJson.States[stateName].Branches[i].States).map(parallelStateName => {
                    stateLabel = parallelStateName;
                    nodeToTabMapping[counter] = -1;
                    if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource && workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource!="" && parallelStateName != workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource) {
                      stateLabel += '\n(' + workflowJson.States[stateName].Branches[i].States[parallelStateName].Resource + ')';
                      for (var t=0;t<10;t++) {
                        if (functionCodeName[t]==workflowJson.States[stateName].Resource)
                        nodeToTabMapping[counter] = t;
                      }
                    }

                    var insertedFunction = {id: counter, label: stateLabel, color: 'rgb(121, 204, 229,1.0)'};

                    workflowFunctionNames.push(parallelStateName);
                    workflowFunctions.push(insertedFunction);
                    counter++;
                  });
                }
              }
            }
          });
          if (workflowJson.StartAt!="") {
            workflowEdges.push({from: 0, to: workflowFunctionNames.indexOf(workflowJson.StartAt)+2, label: '', dashes: false, length: 150, font: {align: 'middle'}});
          }
          Object.keys(workflowJson.States).map(stateName => {
            if (workflowJson.States[stateName].End) {
              finalDest = 1;
              if (workflowJson.States[stateName].Type!="Parallel") {
                var insertedEdge = {from: workflowFunctionNames.indexOf(stateName)+2, to: 1, label: '', dashes: false, length: 150, font: {align: 'middle'}};
                workflowEdges.push(insertedEdge);
              }
            }
            if (workflowJson.States[stateName].Type=="Choice") {
              if (workflowJson.States[stateName].Default) {
                var insertedEdge = {from: workflowFunctionNames.indexOf(stateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Default)+2, label: '', dashes: true, length: 150, font: {align: 'middle'}};
                workflowEdges.push(insertedEdge);
              }
              for (var i = 0;i<workflowJson.States[stateName].Choices.length;i++) {
                var insertedEdge = {from: workflowFunctionNames.indexOf(stateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Choices[i].Next)+2, label: '', dashes: true, length: 150, font: {align: 'middle'}};
                workflowEdges.push(insertedEdge);
              }
            }
            if (workflowJson.States[stateName].Next && workflowJson.States[stateName].Next!="") {
              finalDest = workflowFunctionNames.indexOf(workflowJson.States[stateName].Next)+2;
              if (workflowJson.States[stateName].Type!="Parallel") {
                var insertedEdge = {from: workflowFunctionNames.indexOf(stateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Next)+2, label: '', dashes: false, length: 150, font: {align: 'middle'}};
                workflowEdges.push(insertedEdge);
              }
            }
            if (workflowJson.States[stateName].Type=="Parallel") {

              for (var i = 0;i<workflowJson.States[stateName].Branches.length;i++) {
                var insertedEdge = {from: workflowFunctionNames.indexOf(stateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Branches[i].StartAt)+2, label: '', dashes: false, length: 150, font: {align: 'middle'}};
                workflowEdges.push(insertedEdge);
                Object.keys(workflowJson.States[stateName].Branches[i].States).map(parallelStateName => {

                  if (workflowJson.States[stateName].Branches[i].States[parallelStateName].End) {
                    var insertedEdge = {from: workflowFunctionNames.indexOf(parallelStateName)+2, to: finalDest, label: '', dashes: false, length: 150, font: {align: 'middle'}};
                    workflowEdges.push(insertedEdge);
                  }
                  if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Next && workflowJson.States[stateName].Branches[i].States[parallelStateName].Next!="") {
                    var insertedEdge = {from: workflowFunctionNames.indexOf(parallelStateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Branches[i].States[parallelStateName].Next)+2, label: '', dashes: false, length: 150, font: {align: 'middle'}};
                    workflowEdges.push(insertedEdge);
                  }
                  if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Type=="Choice") {
                    if (workflowJson.States[stateName].Branches[i].States[parallelStateName].Default) {
                      var insertedEdge = {from: workflowFunctionNames.indexOf(parallelStateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Branches[i].States[parallelStateName].Default)+2, label: '', dashes: true, length: 150, font: {align: 'middle'}};
                      workflowEdges.push(insertedEdge);
                    }
                    for (var t = 0;t<workflowJson.States[stateName].Branches[i].States[parallelStateName].Choices.length;t++) {
                      var insertedEdge = {from: workflowFunctionNames.indexOf(parallelStateName)+2, to: workflowFunctionNames.indexOf(workflowJson.States[stateName].Branches[i].States[parallelStateName].Choices[t].Next)+2, label: '', dashes: true, length: 150, font: {align: 'middle'}};
                      workflowEdges.push(insertedEdge);
                    }
                  }

                });
              }


            }

          });


        } else {

          for (var key in workflowJson.functions) {
            if (workflowJson.functions.hasOwnProperty(key)) {
              if (workflowJson.functions[key].name!="") {
                var insertedFunction = {id: counter, label: workflowJson.functions[key].name, color: 'rgb(121, 204, 229,1.0)'};
                for (var i=0;i<10;i++) {
                  if (functionCodeName[i]==workflowJson.functions[key].name)
                  nodeToTabMapping[counter] = i;
                }
                workflowFunctionNames.push(workflowJson.functions[key].name);
                workflowFunctions.push(insertedFunction);
                counter++;
              }
            }
          }
          if (workflowJson.entry!="") {
            workflowEdges.push({from: 0, to: workflowFunctionNames.indexOf(workflowJson.entry)+2, label: '', dashes: false, length: 100, font: {align: 'middle'}});
          }
          for (var key in workflowJson.functions) {
            if (workflowJson.functions.hasOwnProperty(key)) {
              if (workflowJson.functions[key].next) {
                if (workflowJson.functions[key].next!="") {
                  for (var i = 0;i<workflowJson.functions[key].next.length;i++) {
                    if (workflowJson.functions[key].name!="" && workflowJson.functions[key].next[i]!="") {
                      var insertedEdge = {from: workflowFunctionNames.indexOf(workflowJson.functions[key].name)+2, to: workflowFunctionNames.indexOf(workflowJson.functions[key].next[i])+2, label: '', dashes: false, length: 100, font: {align: 'middle'}};
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
                      var insertedEdge = {from: workflowFunctionNames.indexOf(workflowJson.functions[key].name)+2, to: workflowFunctionNames.indexOf(workflowJson.functions[key].potentialNext[i])+2, label: '', dashes: true, length: 100, font: {align: 'middle'}};
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
          interaction:{hover:true},
          physics:{
            stabilization: true
          },

          layout: {
            randomSeed:0,
          },
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
             arrows:{
               to: {
                 enabled: true,
                 type: 'arrow'
               }
             }
         }
        };

        var network = new vis.Network(container, data, options);

        network.on("doubleClick", function (params) {
          if (params.nodes[0]) {
            //$scope.gTab = 3 + (params.nodes[0]-2);
            if (nodeToTabMapping[params.nodes[0]]>=0) {
              $scope.gTab = 3 + (nodeToTabMapping[params.nodes[0]]);
              document.getElementById('switchTabButton').click();
            }
          }
        });

        network.fit();
        network.once('initRedraw', function() {
          network.moveTo({offset:{x: (0.5 * 1000),y: (0.5 * 550)}});
        });

     }

     function initializeGraph() {
       var edges = new vis.DataSet(workflowEdges);
       var nodes = new vis.DataSet(workflowFunctions);

       var workflowFunctions = new Array();
       var workflowEdges = new Array();

       workflowFunctions.push({id: 0, label: 'Start', x:10, shape: 'circle', color: '#b7d6b1'});
       workflowFunctions.push({id: 1, label: 'End', x:600, shape: 'circle', color: '#f7a8a8'});

       var edges = new vis.DataSet(workflowEdges);
       var nodes = new vis.DataSet(workflowFunctions);

       // create a network
       var container = document.getElementById('workflowGraph');
       var data = {
           nodes: nodes,
           edges: edges
       };

       var options = {
         autoResize: true,
         interaction:{hover:true},
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
            arrows:{
              to: {
                enabled: true,
                type: 'arrow'
              }
            }
        }
       };

       var network = new vis.Network(container, data, options);

       network.on("doubleClick", function (params) {
         if (params.nodes[0]) {
           $scope.gTab = 3 + (params.nodes[0]-2);
           document.getElementById('switchTabButton').click();
         }
       });

       network.fit();
       network.once('initRedraw', function() {
         network.moveTo({offset:{x: (0.5 * 1000),y: (0.5 * 550)}});
       });
     }

     $scope.setTabFocus = function(editor) {
       $timeout(function() {
         functionCodeEditor[editor-3].focus();
       }, 50);
     }

     function getFunctions() {

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {

              'Content-Type': 'application/json'

         },

         data:  JSON.stringify({ "action" : "getFunctions", "data" : { "user" : { "token" : token } } })

       }

       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             $scope.functions = response.data.data.functions;
             sharedData.setFunctions(response.data.data.functions);
           } else {
             console.log("Failure status returned by getFunctions");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctions");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });

       });
     }

     function enableFunctionCodeTabs(workflowJson) {
       for (var i=0;i<10;i++) {
         $scope.showFunctionCodeTab[i] = false;
         functionCodeName[i] = "";
       }
       if (workflowJson.hasOwnProperty('StartAt')) {
         var i = 0;

         Object.keys(workflowJson.States).map(e => {
           if (workflowJson.States[e].Type=='Parallel') {

             Object.keys(workflowJson.States[e].Branches).map(f => {

               Object.keys(workflowJson.States[e].Branches[f].States).map(g => {
                 if (workflowJson.States[e].Branches[f].States[g].Resource) {
                   console.log(workflowJson.States[e].Branches[f].States[g].Resource);

                   for (var key in $scope.functions) {
                     var n = workflowJson.States[e].Branches[f].States[g].Resource.indexOf(':');
                     var resource = workflowJson.States[e].Branches[f].States[g].Resource.substring(0, n != -1 ? n : workflowJson.States[e].Branches[f].States[g].Resource.length);
                     if ($scope.functions[key].name==resource && i<10) {
                       var alreadyLoaded = false;
                       for (var t=0;t<10;t++) {
                         if (functionCodeName[t] == resource) {
                           alreadyLoaded = true;
                         }
                       }
                       if (!alreadyLoaded) {
                         gVer = -1;
                         $scope.showFunctionCodeTab[i] = true;
                         getFunctionCode(resource, $scope.functions[key].id, $scope.functions[key].runtime, functionCodeEditor[i], i);
                         functionCodeName[i] = resource;
                         i++;
                       }
                     }
                   }
                 }
               });
             });
           }

           for (var key in $scope.functions) {
             if (workflowJson.States[e].Resource && $scope.functions[key].name==workflowJson.States[e].Resource && i<10) {
               var alreadyLoaded = false;
               for (var t=0;t<10;t++) {
                 if (functionCodeName[t] == workflowJson.States[e].Resource) {
                   alreadyLoaded = true;
                 }
               }
               if (!alreadyLoaded) {
                 $scope.showFunctionCodeTab[i] = true;
                 getFunctionCode(workflowJson.States[e].Resource, $scope.functions[key].id, $scope.functions[key].runtime, functionCodeEditor[i], i);
                 functionCodeName[i] = workflowJson.States[e].Resource;
                 i++;
               }
             }
           }
         });
       } else {
         for (var i=0; i<workflowJson.functions.length;i++) {
             for (var key in $scope.functions) {
               if ($scope.functions[key].name==workflowJson.functions[i].name && i<10) {
                 $scope.showFunctionCodeTab[i] = true;
                 functionCodeName[i] = workflowJson.functions[i].name;
                 getFunctionCode(workflowJson.functions[i].name, $scope.functions[key].id, $scope.functions[key].runtime, functionCodeEditor[i], i);
               }
             }
         }
       }
     }

     function saveFunctionCodeChanges(functionName, functionId, editor, editorIndex) {

       var session = editor.getSession();
       // base 64 encode function code
       var encodedFunctionCode = btoa(session.getDocument().getValue());

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId, "format" : "text", "chunk" : "0", "code" : encodedFunctionCode } } })
       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Function code sucessfully uploaded.');
             toastr.success('Your function code ' + functionName + ' has been saved successfully!');
             functionCodeBuffer[editorIndex] = session.getDocument().getValue();

           } else {
             console.log("Failure status returned by uploadFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadFunctionCode");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });

       });

     };


     function getFunctionCode(functionName, functionId, functionRuntime, editor, editorIndex) {

       if (editor) {
         var session = editor.getSession();

         editor.$blockScrolling = Infinity;
         editor.focus();
       }

       console.log('Loading function:' + functionName);

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:  JSON.stringify({ "action" : "getFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId } } })

       }
       return $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Function code sucessfully downloaded.');

             // decoding and inserting function code into inline editor
             if (response.data.data.function.code) {
               if (editorIndex == -1) {
                 return atob(response.data.data.function.code);

               } else {
                 if (functionRuntime=="Python 3.6") {
                   editor.getSession().setMode("ace/mode/python");
                 } else if (functionRuntime=="Java") {
                   editor.getSession().setMode("ace/mode/java");
                 }

                 editor.getSession().setValue(atob(response.data.data.function.code));

                 functionCodeBuffer[editorIndex] = atob(response.data.data.function.code);

                 if (codeError) {
                   var functionWithError = codeError.substr(0, codeError.lastIndexOf(':'));

                   if (functionName==functionWithError) {
                     var errorLine = codeError.substr(codeError.lastIndexOf(':')+1, codeError.length-1);

                     $scope.gTab = 3 + editorIndex;
                     $timeout(function() {
                       document.getElementById('switchTabButton').click();
                       var Range = ace.require('ace/range').Range;
                       var marker = editor.session.addMarker(new Range(errorLine-1, 0, errorLine-1, 1), "codeErrorHighlighter", "fullLine");
                       $timeout(function() {
                         editor.gotoLine(errorLine, 0);
                         editor.scrollToLine(errorLine-10);
                       }, 50);
                       //editor.gotoLine(errorLine, 0);
                       //editor.scrollToLine(errorLine);
                       $timeout(function() {
                         editor.session.removeMarker(marker);
                       }, 5000);
                     }, 50);

                   }

                 }
               }
               editor.focus();
             }
           } else {
             console.log("Failure status returned by getFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionCode");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });

       });
     };

     $scope.saveChanges = function(silent) {

       // save function code changes
       for (var i=0; i<10;i++) {
           if ($scope.showFunctionCodeTab[i] == true) {
             for (var key in $scope.functions) {
               if ($scope.functions[key].name==functionCodeName[i] && functionCodeBuffer[i]!=functionCodeEditor[i].getSession().getDocument().getValue()) {
                 saveFunctionCodeChanges(functionCodeName[i], $scope.functions[key].id, functionCodeEditor[i], i);
               }
             }
           }
       }

       if (silent || workflowBuffer != $scope.aceSession.getDocument().getValue()) {
         saveWorkflowChanges(silent);
       }

     }

     $scope.clearInitiatedAction = function() {
       $scope.initiatedAction = "";
     }

     $scope.execute = function() {
       var dirty = false;
       $scope.changedBuffers = "";
       if (workflowBuffer != $scope.aceSession.getDocument().getValue()) {
         dirty = true;
         $scope.changedBuffers = $scope.getWorkflowName();
       }
       for (var i=0;i<10;i++) {
         if ($scope.showFunctionCodeTab[i] == true && functionCodeBuffer[i]!=functionCodeEditor[i].getSession().getDocument().getValue()) {
           dirty = true;
           if ($scope.changedBuffers != "") {
             $scope.changedBuffers += ", ";
           }
           $scope.changedBuffers += functionCodeName[i];
         }
       }
       if (dirty) {
         $scope.initiatedAction = "execute";
         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/workflows/modals/closeWorkflowEditorModal.html',
           size: 'md',
         });
       } else {
         $scope.openWorkflowExecutionModal(sharedProperties.getWorkflowId());
         $timeout(function() {
           document.getElementById('closeButton').click();
         }, 50);
       }
     }

     $scope.deployAndExecute = function() {
       var dirty = false;
       $scope.changedBuffers = "";
       if (workflowBuffer != $scope.aceSession.getDocument().getValue()) {
         dirty = true;
         $scope.changedBuffers = $scope.getWorkflowName();
       }
       for (var i=0;i<10;i++) {
         if ($scope.showFunctionCodeTab[i] == true && functionCodeBuffer[i]!=functionCodeEditor[i].getSession().getDocument().getValue()) {
           dirty = true;
           if ($scope.changedBuffers != "") {
             $scope.changedBuffers += ", ";
           }
           $scope.changedBuffers += functionCodeName[i];
         }
       }
       if (dirty) {
         $scope.initiatedAction = "deployAndExecute";
         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/workflows/modals/closeWorkflowEditorModal.html',
           size: 'md',
         });
       } else {
         $scope.deployAndExecuteWorkflow(sharedProperties.getWorkflowId());
         $timeout(function() {
           document.getElementById('closeButton').click();
         }, 50);
       }
     }

     function saveWorkflowChanges(silent) {

       var silentSave = silent;

       // base 64 encode workflow JSON
       var encodedWorkflowJSON = btoa($scope.aceSession.getDocument().getValue());
       var workflowASLType = "unknown";

       if (!silentSave) {
         try {
           workflowJson = JSON.parse($scope.aceSession.getDocument().getValue());

         } catch(e) {
           // invalid json
           console.log("Invalid workflow JSON.");
           $scope.errorMessage = "Invalid workflow JSON.";

           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });
           $scope.aceWorkflowEditor.focus();
           return;

         }
         //var lcJson = $scope.aceSession.getDocument().getValue().toLowerCase();

         // valid values should be: "unknown", "AWS-compatible", "KNIX-specific"
         // also store the determined workflowASLType during upload of the workflow JSON

         if ($scope.aceSession.getDocument().getValue().includes('"StartAt"')) {
           const ajv = new Ajv({
              schemas: [
                choice.responseJSON,
                fail.responseJSON,
                parallel.responseJSON,
                mapState.responseJSON,
                pass.responseJSON,
                stateMachine.responseJSON,
                state.responseJSON,
                succeed.responseJSON,
                task.responseJSON,
                wait.responseJSON,
              ],
           });
           var valid = ajv.validate('http://asl-validator.cloud/state-machine#', workflowJson);

           if (!valid) {
             console.log("Invalid Amazon States Language (ASL) specification.");
             console.log("Checking KNIX extensions validity...");
               const ajv_knix = new Ajv({
                  schemas: [
                    knix_choice.responseJSON,
                    knix_fail.responseJSON,
                    knix_parallel.responseJSON,
                    knix_mapState.responseJSON,
                    knix_pass.responseJSON,
                    knix_stateMachine.responseJSON,
                    knix_state.responseJSON,
                    knix_succeed.responseJSON,
                    knix_task.responseJSON,
                    knix_wait.responseJSON,
                  ],
               });
               var valid_knix = ajv_knix.validate('http://knix-asl-validator.cloud/state-machine#', workflowJson);
               console.log("valid_knix: " + valid_knix);
               if (!valid_knix)
               {
                 $scope.errorMessage = "Invalid Amazon States Language (ASL) specification and/or KNIX ASL extensions.";
                 $uibModal.open({
                   animation: true,
                   scope: $scope,
                   templateUrl: 'app/pages/workflows/modals/errorModal.html',
                   size: 'md',
                 });
                 $scope.aceWorkflowEditor.focus();
                 return;
               }

               workflowASLType = "KNIX-specific";
           }
           else
           {
               workflowASLType = "AWS-compatible";
           }
         }

         enableFunctionCodeTabs(workflowJson);
         if ($scope.activeTab==1) {
           $scope.gTab = 0;
           $timeout(function() {
             document.getElementById('switchTabButton').click();
             drawWorkflowGraph(workflowJson);
           }, 50);
         } else {
           drawWorkflowGraph(workflowJson);
         }
       } else {
         initializeGraph();
         workflowASLType = "AWS-compatible";
       }

       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadWorkflowJSON", "data" : { "user" : { "token" : token } , "workflow" : { "id" : sharedProperties.getWorkflowId(), "json" : encodedWorkflowJSON, "ASL_type": workflowASLType } } })
       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Workflow JSON sucessfully uploaded.');
             $scope.reloadWorkflows();
             if (silentSave==false) {
               toastr.success('Your workflow JSON has been saved successfully!');
               workflowBuffer = $scope.aceSession.getDocument().getValue();

             }
           } else {
             console.log("Failure status returned by uploadWorkflowJSON");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadWorkflowJSON");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           $uibModal.open({
             animation: true,
             scope: $scope,
             templateUrl: 'app/pages/workflows/modals/errorModal.html',
             size: 'md',
           });

       });

     };

   });
}());
