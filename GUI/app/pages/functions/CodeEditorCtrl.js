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
  angular.module('MfnWebConsole').controller('CodeEditorCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties, sharedData) {

     var urlPath = sharedProperties.getUrlPath();

     var zipDirectory = "";
     var uploadStatus = "";
     var chunkSize = 1024 * 1024; // 1MB
     var encodedZipFile = "";
     var currentChunk = 0;
     var numChunks = 0;
     var codeEditorModalVisible = true;


     var dataPrefix = sharedProperties.getDataPrefix();

     var mfnAPI = [ {"word" : "log(\"\")", "score" : 1008 },
                     {"word" : "get(\"\")", "score" : 1007}, {"word" : "put()", "score" : 1006}, {"word" : "delete(\"\")", "score" : 1005} ];
     var mfnAPITooltip = [ {"command" : "log()", "ttip" : "<b>log(text)</b><br><br>Log text. Uses the instance id to indicate which function instance logged the text.<br><br><b>Args:</b><br>text (string): text to be logged.<br><br><b>Returns:</b><br>None.<br><br><b>Raises:</b><br>MicroFunctionsUserLogException: if there are any errors in the logging function."},
     {"command" : "put()", "ttip" : "<b>put(key, value, is_private=False, is_queued=False)</b><br><br>Access to data layer to store a data item in the form of a (key, value) pair.<br>By default, the put operation is reflected on the data layer immediately.<br>If the put operation is queued (i.e., is_queued = True), the data item is put into the transient data table.<br>If the key was previously deleted by the function instance, it is removed from the list of items to be deleted.<br>When the function instance finishes, the transient data items are committed to the data layer.<br><br><b>Args:</b><br>key (string): the key of the data item<br>value (string): the value of the data item<br>is_private (boolean): whether the item should be written to the private data layer of the workflow; default: False<br>is_queued (boolean): whether the put operation should be reflected on the data layer after the execution finish; default: False<br><br><b>Returns:</b><br>None<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key and/or value are not strings."},
     {"command" : "get(\"\")", "ttip" : "<b>get(key, is_private=False)</b><br><br>Access to data layer to load the value of a given key. The key is first checked in the transient deleted items.<br>If it is not deleted, the key is then checked in the transient data table. If it is not there,<br>it is retrieved from the global data layer. As a result, the value returned is consistent with what this function<br>instance does with the data item. If the data item is not present in either the transient data table<br>nor in the global data layer, an empty string (i.e., \"\") will be returned.<br>If the function used put() and delete() operations with is_queued = False (default), then the checks<br>of the transient table will result in empty values, so that the item will be retrieved<br>from the global data layer.<br><br><b>Args:</b><br>key (string): the key of the data item<br>is_private (boolean): whether the item should be read from the private data layer of the workflow; default: False<br><br><b>Returns:</b><br>value (string): the value of the data item; empty string if the data item is not present.<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key is not a string."},
    {"command" : "delete(\"\")", "ttip" : "<b>delete(key, is_private=False, is_queued=False)</b><br><br>Access to data layer to delete data item associated with a given key.<br>By default, the delete operation is reflected on the data layer immediately.<br>If the delete operation is queued (i.e., is_queued = True), the key is removed from the transient data table.<br>It is also added to the list of items to be deleted from the global data layer when the function instance finishes.<br><br><b>Args:</b><br>key (string): the key of the data item<br>is_private (boolean): whether the item should be deleted from the private data layer of the workflow; default: False<br>is_queued (boolean): whether the delete operation should be reflected on the data layer after the execution finish; default: False<br><br><b>Returns:</b><br>None<br><br><b>Raises:</b><br>MicroFunctionsDataLayerException: when the key is not a string."}
    ];

     var zip = new JSZip();

     $scope.functions = sharedData.getFunctions();
     if (!$scope.functions) {
       getFunctions();
     }

     var functionBuffer = "";
     var requirementsBuffer = "";
     $scope.sObjects = [ ];
     $scope.changedBuffers = "";
     getStorageObjectsList();

     $scope.getFunctionIndex = function(functionId) {

       for (var key in $scope.functions) {
         if ($scope.functions[key].id==functionId) {
           return key;
         }
       }
       return -1;
     };

     $scope.functionId = sharedProperties.getFunctionId();

     $scope.functionName = sharedProperties.getFunctionName();

     $scope.functionVersion = 0;

     $scope.functionRuntime = sharedProperties.getFunctionRuntime();

     $scope.initiatedAction = "";

     if ($scope.functions[$scope.getFunctionIndex($scope.functionId)].versions) {
       $scope.functionVersion = $scope.functions[$scope.getFunctionIndex($scope.functionId)].versions.length;
     }

     var functionCodeBlueprintPython = '#!/usr/bin/python\r\n\r\ndef handle(event, context):\r\n\r\n    return ""';
     var functionCodeBlueprintJava = 'import org.microfunctions.mfnapi.MicroFunctionsAPI;\r\n\r\npublic class ' + $scope.functionName + '\r\n{\r\n\tpublic Object handle(Object event, MicroFunctionsAPI context)\r\n\t{\r\n\t\treturn "";\r\n\t}\r\n}';

     function getFunctions() {

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
              'Content-Type': 'application/json'
         },

         data:   JSON.stringify({ "action" : "getFunctions", "data" : { "user" : { "token" : token } } })

       }

       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             $scope.functions = response.data.data.functions;
             sharedData.setFunctions(response.data.data.functions);
           } else {
             console.log("Failure status returned by getFunctions");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctions");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     }


     $scope.file_changed = function(element) {
       var file = element.files[0];
       if (file.name.endsWith(".py") || file.name.endsWith(".java")) {
         var reader = new FileReader();
         document.getElementById("uploadStatus").innerHTML = "Uploading <b>" + file.name + "</b>...";

         document.getElementById("downloadFunctionButton").style.display = 'none';
         document.getElementById("downloadZipButton").style.display = 'none';

         reader.onload = function(e){
           $scope.$apply(function(){
             $scope.aceSession.setValue(reader.result);
             $scope.saveChanges(false);
             uploadStatus = "Last uploaded file: <b>" + file.name + "</b>";
             document.getElementById("uploadStatus").innerHTML = uploadStatus;
             document.getElementById("downloadFunctionButton").style.display = 'inline';
           });
         };
         reader.readAsText(file);
       } else if (file.name.endsWith(".zip") || file.name.endsWith(".jar")) {
          uploadStatus = "Uploading <b>" + file.name + "</b>...";
          document.getElementById("uploadStatus").innerHTML = uploadStatus;
          $scope.progressBar = 0;
          $scope.progressCounter = $scope.progressBar;
          document.getElementById("progBar").style.display = 'inline';
          document.getElementById("downloadFunctionButton").style.display = 'none';
          document.getElementById("downloadZipButton").style.display = 'none';

          var reader = new FileReader();

          reader.onload = function(e){
            $scope.$apply(function(){
              var zipFile = reader.result.slice(reader.result.indexOf("base64,") + "base64,".length);
              numChunks = Math.ceil(zipFile.length / chunkSize)-1;
              $scope.uploadZipFile(zipFile, file.name, zipFile.length, 0, numChunks);

            });
          };
          reader.readAsDataURL(file);

          JSZip.loadAsync(file)
          .then(function(zip) {
              zipDirectory = "<br><br><table border='1'>";
              zip.forEach(function (relativePath, zipEntry) {
                  if (!zipEntry.name.endsWith('/')) {
                    zipDirectory += "<tr><td style='padding: 5px 5px 5px 5px;'>" + zipEntry.name + "</td><td style='padding: 5px 5px 5px 5px;'>" + (zipEntry._data.uncompressedSize / 1024.0).toFixed(2) + " KB</td><td style='padding: 5px 5px 5px 5px;'>" + zipEntry.date + "</td></tr>";
                  }
                  if (zipEntry.name == sharedProperties.getFunctionName() + ".py" || zipEntry.name == sharedProperties.getFunctionName() + ".java") {
                    zip.file(zipEntry.name).async("string").then(function (data) {
                      $scope.aceSession.setValue(data);
                      $scope.saveChanges(false);
                    });
                  }

              });
              zipDirectory += "</table>"

            }, function (e) {
              console.log("Error reading uploaded ZIP file:" + e);
            });
       }
     };

     $scope.aceLoaded = function(_editor) {

       $scope.aceSession = _editor.getSession();
       $scope.aceCodeEditor = _editor;
       _editor.on("blur", function() { _editor.completer.detach(); });

       _editor.completers.push({
              getCompletions: function(editor, session, pos, prefix, callback) {

                  var line = session.getLine(editor.getCursorPosition().row);

                  var wordList = [{}];
                  var metaLabel = "";

                  if (undefined !== line) {

                    if (line.includes('context.delete') || line.includes('context.get') || line.includes('context.put')) {
                      wordList = $scope.sObjects;
                      metaLabel = "Storage Object";
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

                }
              }
          });

        _editor.commands.on("afterExec", function (e) {
          if (e.command.name == "insertstring" && (/^[\w.]$/.test(e.args) || /^[\w\(]$/.test(e.args) || /^[\w']$/.test(e.args) || /^[\w"]$/.test(e.args))) {
            _editor.execCommand("startAutocomplete");
          }
        });

        complNum = _editor.completers.length;

       _editor.$blockScrolling = Infinity;
       _editor.focus();

       $scope.getFunctionZipMetadata();

       console.log('Loading function:' + sharedProperties.getFunctionName());
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data: JSON.stringify({ "action" : "getFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId() } } })

       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Function code sucessfully downloaded.');

             // decoding and inserting function code into inline editor
             if (response.data.data.function.code) {
               _editor.getSession().setValue(atob(response.data.data.function.code));
               functionBuffer = atob(response.data.data.function.code);
             } else {
               if ($scope.functionRuntime=="Python 3.6") {
                 _editor.getSession().setValue(functionCodeBlueprintPython);
                 functionBuffer = functionCodeBlueprintPython;
               } else {
                 _editor.getSession().setValue(functionCodeBlueprintJava);
                 functionBuffer = functionCodeBlueprintJava;
               }
               $scope.saveChanges(true);
             }
             _editor.focus();
           } else {
             console.log("Failure status returned by getFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionCode");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

     function getStorageObjectsList() {

       var urlPath = sharedProperties.getUrlPath();
       var token = $cookies.get('token');

      var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : { "data_type": "kv", "parameters": { "action": "listkeys", "start": 0, "count": 2000 } } } })
       }

       $http(req).then(function successCallback(response) {

           $scope.sObjects.length = 0;

           for (var i=0;i<response.data.length;i++) {
               $scope.sObjects.push({"word" : response.data[i], "score": 1000});
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

     function getFunctionCode(functionName, functionVersion, functionId) {

       $scope.aceCodeEditor.$blockScrolling = Infinity;
       $scope.aceCodeEditor.focus();


       console.log('Loading function:' + functionName);

       var token = $cookies.get('token');

       var req;

       if (functionVersion!=-1) {

         req = {
           method: 'POST',
           url: urlPath,
           headers: {
             'Content-Type': 'application/json'
           },

           data:   JSON.stringify({ "action" : "getFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId, "version" : functionVersion } } })

         };

       } else {
         $scope.functionVersion = $scope.functions[$scope.getFunctionIndex(functionName)].versions.length;
         req = {
           method: 'POST',
           url: urlPath,
           headers: {
             'Content-Type': 'application/json'
           },

           data:   JSON.stringify({ "action" : "getFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId } } })
         };
       }
       return $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Function code sucessfully downloaded.');
             if (functionVersion!=-1) {
               $scope.functionVersion = functionVersion;
             }

             // decoding and inserting function code into inline editor
             if (response.data.data.function.code) {
               $scope.aceSession.setValue(atob(response.data.data.function.code));
               $scope.aceCodeEditor.focus();
             }
           } else {
             console.log("Failure status returned by getFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionCode");
           console.log("Response:" + response);

           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

     $scope.loadFunction = function(version) {
       getFunctionCode($scope.functionName, version, $scope.functionId);
     }

     $scope.clearInitiatedAction = function() {
       $scope.initiatedAction = "";
     }

     $scope.aceDependenciesLoaded = function(_editor) {

       $scope.aceDependenciesSession = _editor.getSession();
       $scope.aceDependenciesEditor = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.focus();

       if ($scope.functionRuntime=="Python 3.6") {
         _editor.getSession().setMode("ace/mode/text");
         document.getElementById('requirementsLabel').innerHTML = "List of libraries required by this function (in the format of a pip requirements.txt file):";
         document.getElementById("uploadLabel").innerHTML = "You can upload a file containing your Python function code here or a zip file containing your function code and/or other files your code depends on.";
         document.getElementById("uploadBtn").setAttribute("accept", ".py,.zip");
       } else if ($scope.functionRuntime=="Java") {
        _editor.getSession().setMode("ace/mode/xml");
        document.getElementById('requirementsLabel').innerHTML = "List of libraries required by this function (in the format of Maven pom.xml dependencies):";
        document.getElementById("uploadLabel").innerHTML = "You can upload a file containing your Java function code here or a jar/zip file containing your function code and/or other files your code depends on.";
        document.getElementById("uploadBtn").setAttribute("accept", ".java,.zip,.jar");
       }

       console.log('Loading dependencies for function:' + sharedProperties.getFunctionName());
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:   JSON.stringify({ "action" : "getFunctionRequirements", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId() } } })

       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             console.log('Function code depedencies sucessfully downloaded.');

             // decoding and inserting function code dependencies into inline editor
             if (response.data.data.function.requirements) {
               _editor.getSession().setValue(atob(response.data.data.function.requirements));
               requirementsBuffer = atob(response.data.data.function.requirements);
             } else {
               _editor.getSession().setValue("");
               requirementsBuffer = "";
             }
             _editor.focus();
           } else {
             console.log("Failure status returned by getFunctionRequirements");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionRequirements");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }
       });
     };

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceCodeEditor.focus();
       }, 350);

     }

     $scope.setFocusDependencies = function() {
       $timeout(function() {
         $scope.aceDependenciesEditor.focus();
       }, 350);

     }

     $scope.getFunctionName = function() {
       return sharedProperties.getFunctionName();
     }

     $scope.getFunctionVersion = function(id) {
       return $scope.functionVersion;
     };

     $scope.test = function() {

       var dirty = false;
       $scope.changedBuffers = "";
       if (functionBuffer != $scope.aceSession.getDocument().getValue()) {
         dirty = true;
         $scope.changedBuffers = $scope.functionName;
       }
       if (requirementsBuffer != $scope.aceDependenciesSession.getDocument().getValue()) {
         dirty = true;
         if ($scope.changedBuffers != "") {
           $scope.changedBuffers += ", ";
         }
         $scope.changedBuffers += "Function Requirements";
       }

       if (dirty) {
         $scope.initiatedAction = "test";
         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/functions/modals/closeCodeEditorModal.html',
           size: 'md',
         });
       } else {
         $scope.testFunction($scope.getFunctionIndex($scope.functionId));
         $timeout(function() {
           document.getElementById('closeButton').click();
         }, 50);
       }
     }

     $scope.closeDialog = function() {

       var dirty = false;
       $scope.changedBuffers = "";
       if (functionBuffer != $scope.aceSession.getDocument().getValue()) {
         dirty = true;
         $scope.changedBuffers = $scope.functionName;
       }
       if (requirementsBuffer != $scope.aceDependenciesSession.getDocument().getValue()) {
         dirty = true;
         if ($scope.changedBuffers != "") {
           $scope.changedBuffers += ", ";
         }
         $scope.changedBuffers += "Function Requirements";
       }

       if (dirty) {
         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/functions/modals/closeCodeEditorModal.html',
           size: 'md',
         });
       } else {
         $timeout(function() {
           document.getElementById('closeButton').click();
         }, 50);

       }
     }

     $scope.getLanguage = function() {
       if ($scope.functionRuntime=="Python 3.6") {
         return "python"
       } else if ($scope.functionRuntime=="Java") {
         return "java"
       }
     }

     $scope.closeModal = function() {
       if ($scope.initiatedAction=="test") {
         $scope.testFunction($scope.getFunctionIndex($scope.functionId));
       }
       $scope.initiatedAction = "";
       $timeout(function() {
         document.getElementById('closeButton').click();
       }, 50);
     }

     $scope.uploadZipMetadata = function(metadata, numChunks) {

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:   JSON.stringify({ "action" : "uploadFunctionZipMetadata", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId(), "format" : "zipMetadata", "chunks" : numChunks, "metadata" : btoa(metadata) } } })

       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('ZIP metadata sucessfully uploaded.');
           } else {
             console.log("Failure status returned by uploadFunctionZipMetadata");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadFunctionZipMetadata");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     };

     $scope.uploadZipFile = function(file, fileName, fileSize, currentChunk, numChunks) {

       var startOffset = (currentChunk*chunkSize);
       var endOffset = fileSize;
       if ((currentChunk+1)*chunkSize >fileSize) {
         endOffset = fileSize;
       } else {
         endOffset = (currentChunk+1)*chunkSize;
       }


       // base 64 encode function code
       var encodedZipFile = file;

       var token = $cookies.get('token');

       var encodedChunk = file.slice(startOffset, endOffset );

       var req = {
         method: 'POST',
         uploadEventHandlers: {
           progress: function (e) {
               if (e.lengthComputable) {
                  $scope.progressBar = Math.floor(((startOffset + e.loaded) / fileSize) * 100);
                  $scope.progressCounter = $scope.progressBar;
               }
             }
         },
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:   JSON.stringify({ "action" : "uploadFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId(), "format" : "zip", "chunk" : currentChunk, "code" : encodedChunk } } })

       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             if (currentChunk<numChunks) {
                currentChunk += 1;
                $scope.uploadZipFile(file, fileName, fileSize, currentChunk, numChunks);
             } else {
               console.log('ZIP file sucessfully uploaded.');
               toastr.success('Your ZIP file has been uploaded successfully!');
               $scope.reloadFunctions();
               currentChunk = 0;
               uploadStatus = "Last uploaded file: <b>" + fileName + "</b>";
               document.getElementById("metaData").innerHTML = uploadStatus + zipDirectory;
               document.getElementById("progBar").style.display = 'none';
               $scope.progressBar = 0;
               $scope.progressCounter = $scope.progressBar;
               document.getElementById("downloadZipButton").style.display = 'inline';
               document.getElementById("downloadFunctionButton").style.display = 'inline';
               $scope.uploadZipMetadata(uploadStatus + zipDirectory, numChunks + 1);
             }

           } else {
             console.log("Failure status returned by uploadFunctionCode/zip");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadFunctionCode/zip");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     };

     $scope.getFunctionZipMetadata = function() {

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:   JSON.stringify({ "action" : "getFunctionZipMetadata", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId()} } })

       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Zip metadata sucessfully retrieved.');
             document.getElementById("downloadZipButton").style.display = 'inline';
             if (response.data.data.function.metadata.length > 1) {
               console.log("metaData:" + response.data.data.function.metadata.length);
               numChunks = response.data.data.function.chunks;
               document.getElementById("metaData").innerHTML = atob(response.data.data.function.metadata);
               document.getElementById("downloadZipButton").style.display = 'inline';
             }
           } else {
             console.log("Failure status returned by getFunctionZipMetadata");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionZipMetadata");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     };

     $scope.downloadZip = function() {
       zipFile = "";
       $scope.getFunctionZip(0, numChunks);
     }

     $scope.getEditorHeading = function() {
       if ($scope.functionRuntime == "Python 3.6") {
         return "Python Code";
       } else if ($scope.functionRuntime == "Java") {
         return "Java Code";
       }
     }

     $scope.getFunctionZip = function(currentChunk, numChunks) {

       document.getElementById("downloadFunctionButton").style.display = 'none';
       document.getElementById("downloadZipButton").style.display = 'none';
       document.getElementById("uploadStatus").innerHTML = "Downloading zip file...";
       document.getElementById("progBar").style.display = 'inline';
       $scope.progressBar = Math.floor((currentChunk/(numChunks-1))*100);
       $scope.progressCounter = $scope.progressBar;
       var token = $cookies.get('token');

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:   JSON.stringify({ "action" : "getFunctionZip", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId(), "chunk" : currentChunk } } })

       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             zipFile += response.data.data.function.code;
             if (currentChunk<numChunks-1) {

                currentChunk += 1;

                $scope.getFunctionZip(currentChunk, numChunks);
             } else {
               document.getElementById("progBar").style.display = 'none';
               $scope.progressBar = 0;
               $scope.progressCounter = $scope.progressBar;
               document.getElementById("downloadFunctionButton").style.display = 'inline';
               document.getElementById("downloadZipButton").style.display = 'inline';
               console.log('Function Zip file sucessfully downloaded.');
               // initiating download
               var binaryString = window.atob(zipFile);
               var binaryLen = binaryString.length;
               var bytes = new Uint8Array(binaryLen);
               for (var i = 0; i < binaryLen; i++) {
                 var ascii = binaryString.charCodeAt(i);
                 bytes[i] = ascii;
               }
               var blob = new Blob([bytes]);
               var link = document.createElement('a');
               link.href = window.URL.createObjectURL(blob);
               var fileName = sharedProperties.getFunctionName() + ".zip";
               link.download = fileName;
               document.body.appendChild(link);
               link.click();
               document.body.removeChild(link);
             }
           } else {
             document.getElementById("progBar").style.display = 'none';
             $scope.progressBar = 0;
             $scope.progressCounter = $scope.progressBar;
             document.getElementById("downloadFunctionButton").style.display = 'inline';
             document.getElementById("downloadZipButton").style.display = 'inline';
             console.log("Failure status returned by getFunctionZip");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during getFunctionZip");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     }

     $scope.downloadFunctionCode = function() {
       var element = document.createElement('a');
       element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent($scope.aceSession.getDocument().getValue()));
       if ($scope.functionRuntime=="Python 3.6") {
         element.setAttribute('download', sharedProperties.getFunctionName() + ".py");
       } else if ($scope.functionRuntime=="Java") {
         element.setAttribute('download', sharedProperties.getFunctionName() + ".java");
       }

       element.style.display = 'none';
       document.body.appendChild(element);

       element.click();

       document.body.removeChild(element);
     }

     $scope.saveRequirementsFile = function() {

       var encodedFunctionRequirements = btoa($scope.aceDependenciesSession.getDocument().getValue());

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:   JSON.stringify({ "action" : "uploadFunctionRequirements", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId(), "requirements" : encodedFunctionRequirements } } })
       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Function requirements sucessfully uploaded.');
             requirementsBuffer = $scope.aceDependenciesSession.getDocument().getValue();
           } else {
             console.log("Failure status returned by uploadFunctionRequirements");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadFunctionRequirments");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     };

     $scope.$on('$destroy', function(){
         codeEditorModalVisible = false;
     });

     $scope.saveChanges = function(silent) {
       // base 64 encode function code
       var encodedFunctionCode = btoa($scope.aceSession.getDocument().getValue());
       var silentSave = silent;

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : sharedProperties.getFunctionId(), "format" : "text", "chunk" : "0", "code" : encodedFunctionCode } } })
       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Function code sucessfully uploaded.');
             console.log(response.data.data);
             $scope.functionVersion = response.data.data.function.version_latest;
             functionBuffer = $scope.aceSession.getDocument().getValue();
             if (silentSave==false) {
               toastr.success('Your function code has been saved successfully!');
             }
             $scope.reloadFunctions();
           } else {
             console.log("Failure status returned by uploadFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (codeEditorModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during uploadFunctionCode");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (codeEditorModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     };

   });
}());
