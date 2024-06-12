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
  angular.module('MfnWebConsole').controller('WorkflowImportCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties, sharedData) {

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
    var knix_task = $.getJSON("lib/knix-asl-validator/schemas/task.json", function (json) {
    });

    var knix_choice = $.getJSON("lib/knix-asl-validator/schemas/choice.json", function (json) {
    });

    var knix_fail = $.getJSON("lib/knix-asl-validator/schemas/fail.json", function (json) {
    });

    var knix_mapState = $.getJSON("lib/knix-asl-validator/schemas/map.json", function (json) {
    });

    var knix_parallel = $.getJSON("lib/knix-asl-validator/schemas/parallel.json", function (json) {
    });

    var knix_wait = $.getJSON("lib/knix-asl-validator/schemas/wait.json", function (json) {
    });

    var knix_state = $.getJSON("lib/knix-asl-validator/schemas/state.json", function (json) {
    });

    var knix_stateMachine = $.getJSON("lib/knix-asl-validator/schemas/state-machine.json", function (json) {
    });

    var knix_pass = $.getJSON("lib/knix-asl-validator/schemas/pass.json", function (json) {
    });

    var knix_succeed = $.getJSON("lib/knix-asl-validator/schemas/succeed.json", function (json) {
    });
   

     var urlPath = sharedProperties.getUrlPath();

     var workflowJson = "";
     var workflowName = "";
     var wJson = "";
     var zipDirectory = "";
     var uploadStatus = "";
     var chunkSize = 1024 * 1024; // 1MB
     var encodedZipFile = "";
     var currentChunk = 0;
     var numChunks = 0;
     var functionIterator = 0;
     var workflowImportModalVisible = true;
     var functionList = new Array();
     var functionRuntime = new Array();
     var existingFiles = new Array();

     var token = $cookies.get('token');

     var dataPrefix = sharedProperties.getDataPrefix();

     var zip = new JSZip();
     var zipSize = 0;
     var downloadSize = 0;
     var fZip = new Array();
     var fZipDirectory = new Array();
     var fCode = new Array();
     var fRequirements = new Array();
     var totalProg = 0;
     var importError = false;
     $scope.fileList = "";

     $scope.functions = sharedData.getFunctions();
     if (!$scope.functions) {
       getFunctions();
     }

     $scope.workflows = sharedData.getWorkflows();

     if (!$scope.workflows) {
       getWorkflows();
     }

     if ($scope.workflowToBeImported) {
       document.getElementById("uploadButton").style.display = 'none';
       document.getElementById("zipFormat").style.display = 'none';
       uploadStatus = "Downloading <b>" + $scope.workflowToBeImported + "</b>";
       document.getElementById("uploadStatus").innerHTML = uploadStatus;
       document.getElementById("progBar").style.display = 'inline';
       JSZipUtils.getBinaryContent("app/pages/docs/usecases/" + $scope.workflowToBeImported, {
         callback: function(err, data) {
           if(err) {
              console.log(err);
              document.getElementById("uploadStatus").innerHTML = "An error occurred while importing the workflow.<p><br>" + err;
           } else {
               document.getElementById("uploadStatus").innerHTML = "Importing <b>" + $scope.workflowToBeImported + "</b>";
               totalProg = downloadSize;
               if (!$scope.workflows || !$scope.functions) {
                 setTimeout(function(){ readZipFile(data); }, 2500);
               } else {
                 readZipFile(data);
               }

           }
         },
         progress: function(e) {
           //console.log(e);
           zipSize = e.total + (4*(e.total/3));
           downloadSize = e.total;
           $scope.progressBar = Math.floor((e.loaded / (e.total + (4*(e.total/3)))) * 100);
           $scope.progressCounter = $scope.progressBar;
         }
       });

     }

     $scope.file_changed = function(element) {
       var file = element.files[0];

        uploadStatus = "Importing <b>" + file.name + "</b>";
        document.getElementById("uploadStatus").innerHTML = uploadStatus;
        $scope.progressBar = 0;
        $scope.progressCounter = $scope.progressBar;
        document.getElementById("progBar").style.display = "inline";

        var reader = new FileReader();

        reader.onload = function(e){
          $scope.$apply(function(){
            var zipFile = reader.result.slice(reader.result.indexOf("base64,") + "base64,".length);
            zipSize = zipFile.length;
            console.log('zipSize:' + zipSize);
          });
        };
        reader.readAsDataURL(file);
        readZipFile(file);

     };

     function readZipFile(file) {
       JSZip.loadAsync(file)
       .then(function(zip) {
           zipDirectory = "<table border='1'>";

           zip.forEach(function (relativePath, zipEntry) {

               if (!zipEntry.name.endsWith('/')) {
                 zipDirectory += "<tr><td style='padding: 5px 5px 5px 5px;'>" + zipEntry.name + "</td><td style='padding: 5px 5px 5px 5px;'>" + (zipEntry._data.uncompressedSize / 1024.0).toFixed(2) + " KB</td><td style='padding: 5px 5px 5px 5px;'>" + zipEntry.date + "</td></tr>";
               }
               if (!zipEntry.name.includes('/') && zipEntry.name.endsWith('.json'))
               {
                 workflowName = zipEntry.name.substring(0, zipEntry.name.indexOf(".json"));
                 zip.file(zipEntry.name).async("string").then(function (data) {

                   workflowJson = data;
                   wJson = JSON.parse(data);
                   // check if workflow to be imported already exists
                   if (wJson) {
                     functionList = [];
                     functionRuntime = [];
                     existingFiles = [];
                     fZip = [];
                     for (var key in $scope.workflows) {
                       if ($scope.workflows[key].name == workflowName) {
                         existingFiles.push(workflowName);
                       }
                     }
                     parseWorkflowJson(wJson);
                     if (existingFiles.length>0) {
                       $scope.fileList = "";
                       for (var i=0; i<existingFiles.length;i++) {
                         if ($scope.fileList.length>0) {
                           $scope.fileList += ", ";
                         }
                         $scope.fileList += existingFiles[i];
                       }

                       $uibModal.open({
                         animation: true,
                         scope: $scope,
                         templateUrl: 'app/pages/workflows/modals/overwriteImportWorkflowModal.html',
                         size: 'md',
                       });
                     } else {
                       $scope.importWorkflow();
                     }
                     for (var i=0; i<functionList.length;i++) {
                       fZip[i] = new JSZip();
                       fZip[i] = zip.folder(functionList[i]);
                       fZipDirectory[i] =  "<br><br><table border='1'>";
                       fZip[i].forEach(function (relativePath, zipEntry) {
                         var fileName = zipEntry.name.substring(zipEntry.name.indexOf("/") + 1);

                         if (fileName == functionList[i] + '.py') {
                           functionRuntime[i] = "Python 3.6";
                           (function(i) {
                             zip.file(functionList[i] + '/' + functionList[i] + '.py').async("string").then(function (data) {
                               fCode[i] = data;
                             });
                           })(i);
                         } else if (fileName == functionList[i] + '.java') {
                          functionRuntime[i] = "Java";
                          (function(i) {
                            zip.file(functionList[i] + '/' + functionList[i] + '.java').async("string").then(function (data) {
                              fCode[i] = data;
                            });
                          })(i);
                         }

                         if (fileName == 'requirements.txt') {
                           (function(i) {

                             zip.file(functionList[i] + '/requirements.txt').async("string").then(function (data) {
                               fRequirements[i] = data;
                             });
                           })(i);
                         }
                         if (!zipEntry.name.endsWith('/')) {
                           fZipDirectory[i] += "<tr><td style='padding: 5px 5px 5px 5px;'>" + fileName + "</td><td style='padding: 5px 5px 5px 5px;'>" + (zipEntry._data.uncompressedSize / 1024.0).toFixed(2) + " KB</td><td style='padding: 5px 5px 5px 5px;'>" + zipEntry.date + "</td></tr>";
                         }
                       });
                       fZipDirectory[i] += "</table>";

                     }
                   }
                 });
               }

           });
           zipDirectory += "</table>";

           document.getElementById("metaData").innerHTML = zipDirectory;
           document.getElementById("zipFormat").style.display = 'none';
           document.getElementById("uploadButton").style.display = 'none';

         }, function (e) {
           document.getElementById("currentOperation").style.display = "none";
           document.getElementById("bar").style.display = "none";
           document.getElementById("metaData").style.visibility = "hidden";
           document.getElementById("uploadStatus").innerHTML = "An error occurred while importing workflow <b>" + workflowName + "</b> and its dependencies.<p><br>The zip file could not be read.";
           console.log("Error reading uploaded ZIP file:" + e);
         });
     }

     $scope.importWorkflow = function() {

       createWorkflow(workflowName);

     }


     function newFunction(functionIterator) {

       if (functionIterator < functionList.length) {
         (function(functionIterator) {
           fZip[functionIterator].generateAsync({type:"blob", compression: "DEFLATE", compressionOptions: { level: 9 }})
           .then(function (blob) {

             var reader = new FileReader();
             reader.readAsDataURL(blob);
             reader.onloadend = function() {
               
               createFunction(functionList[functionIterator], functionRuntime[functionIterator], fZipDirectory[functionIterator], reader.result.slice(reader.result.indexOf("base64,") + "base64,".length));
             }
           });
         })(functionIterator);
       } else {
         $scope.progressBar = 100;
         $scope.progressCounter = 100;
         document.getElementById("currentOperation").style.display = "none";
         document.getElementById("bar").style.display = "none";
         document.getElementById("metaData").style.visibility = "hidden";
         if (!importError) {
           document.getElementById("uploadStatus").innerHTML = "Successfully imported workflow <b>" + workflowName + "</b> and all its dependencies.";
           toastr.success('The workflow ' + workflowName + ' has been imported successfully!');
         } else {
           document.getElementById("uploadStatus").innerHTML = "An error occurred while importing workflow <b>" + workflowName + "</b> and its dependencies.";
         }
       }
     }

     function parseWorkflowJson(workflowJson) {

       if (workflowJson.hasOwnProperty('StartAt')) {

         Object.keys(workflowJson.States).map(e => {
           if (workflowJson.States[e].Type=='Parallel') {

             Object.keys(workflowJson.States[e].Branches).map(f => {

               Object.keys(workflowJson.States[e].Branches[f].States).map(g => {
                 if (workflowJson.States[e].Branches[f].States[g].Resource) {
                   var n = workflowJson.States[e].Branches[f].States[g].Resource.indexOf(':');
                   var resource = workflowJson.States[e].Branches[f].States[g].Resource.substring(0, n != -1 ? n : workflowJson.States[e].Branches[f].States[g].Resource.length);

                   var alreadyExists = false;
                   for (var i=0; i<functionList.length;i++) {
                     if (functionList[i]==resource) {
                       alreadyExists = true;
                     }
                   }
                   if (!alreadyExists) {
                    functionList.push(resource);
                    for (var key in $scope.functions) {
                      if ($scope.functions[key].name == resource) {
                        existingFiles.push(resource);
                      }
                    }
                  }
                 }
               });
             });
           }

           if (workflowJson.States[e].Resource) {
             var n = workflowJson.States[e].Resource.indexOf(':');
             var resource = workflowJson.States[e].Resource.substring(0, n != -1 ? n : workflowJson.States[e].Resource.length);

             functionList.push(resource);
             for (var key in $scope.functions) {

               if ($scope.functions[key].name == resource) {
                 existingFiles.push(resource);
               }
             }
           }
         });
       } else {
         for (var i=0; i<workflowJson.functions.length;i++) {
             functionList.push(workflowJson.functions[i].name);
             for (var key in $scope.functions) {
               if ($scope.functions[key].name==workflowJson.functions[i].name) {
                 existingFiles.push(workflowJson.functions[i].name);
               }
             }
         }
       }
     }


     function uploadZipMetadata (functionId, metadata, numChunks) {

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadFunctionZipMetadata", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId, "format" : "zipMetadata", "chunks" : numChunks, "metadata" : btoa(metadata) } } })

       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('ZIP metadata sucessfully uploaded.');
             functionIterator++;
             newFunction(functionIterator);
           } else {
             importError = true;
             console.log("Failure status returned by uploadFunctionZipMetadata");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (workflowImportModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           importError = true;
           console.log("Error occurred during uploadFunctionZipMetadata");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (workflowImportModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     }

     function uploadZipFile(file, fileName, fileSize, functionId, functionZipDirectory, currentChunk, numChunks) {



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
       //console.log('encodedC:' + encodedChunk);
       //console.log('Chunk:' + atob(encodedChunk));

       var req = {
         method: 'POST',
         uploadEventHandlers: {
           progress: function (e) {
               if (e.lengthComputable) {
                  $scope.progressBar = Math.floor(((totalProg + startOffset + e.loaded) / zipSize) * 100);
                  $scope.progressCounter = $scope.progressBar;
               }
             }
         },
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },

         data:  JSON.stringify({ "action" : "uploadFunctionCode", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId, "format" : "zip", "chunk" : currentChunk, "code" : encodedChunk } } })

       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             if (currentChunk<numChunks) {
                currentChunk += 1;
                uploadZipFile(file, fileName, fileSize, functionId, functionZipDirectory, currentChunk, numChunks);
             } else {
               console.log('ZIP file sucessfully uploaded.');
               totalProg += fileSize;

               currentChunk = 0;
               uploadZipMetadata(functionId, functionZipDirectory, numChunks+1);

               /*uploadStatus = "Last uploaded Zip file: <b>" + fileName + "</b>";
               document.getElementById("zipContents").innerHTML = uploadStatus + zipDirectory;
               document.getElementById("progBar").style.display = 'none';
               $scope.progressBar = 0;
               $scope.progressCounter = $scope.progressBar;
               document.getElementById("downloadZipButton").style.display = 'inline';
               document.getElementById("downloadFunctionButton").style.display = 'inline';
               $scope.uploadZipMetadata(uploadStatus + zipDirectory, numChunks + 1);
               */
             }

           } else {
             importError = true;
             console.log("Failure status returned by uploadFunctionCode/zip");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (workflowImportModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           importError = true;
           console.log("Error occurred during uploadFunctionCode/zip");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (workflowImportModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     }

     function getWorkflows() {

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
              'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "getWorkflows", "data" : { "user" : { "token" : token } } })
       }

       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {

             $scope.workflows = response.data.data.workflows;
             /*for (var i=0;i<$scope.workflows.length;++i) {
               if ($scope.workflows[i].name.startsWith('sand-internal-')) {
                 $scope.deployWorkflow(i, 'undeploy');
                 $scope.deleteWorkflow(i);
                 $scope.workflows.splice(i, 1);
               }
             }*/


             sharedData.setWorkflows(response.data.data.workflows);
           } else {
             importError = true;
             console.log("Failure status returned by getWorkflows");
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
           importError = true;
           console.log("Error occurred during getWorkflows");
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
             importError = true;
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
           importError = true;
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

     function createFunction(functionName, functionRuntime, functionZipDirectory, functionZip) {

       var token = $cookies.get('token');

       console.log('creating new function ' + functionName);
       document.getElementById("currentOperation").innerHTML = "Creating function <b>" + functionName + "</b>...";

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {

          'Content-Type': 'application/json'

         },

	       data:  JSON.stringify({ "action" : "addFunction", "data" : { "user" : { "token" : token } , "function" : { "name" : functionName, "runtime" : functionRuntime, "gpu_usage": functionGpuusage, "gpu_mem_usage": functionGpuMemusage  } } })

       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {
             var functionId  = response.data.data.function.id;
             console.log('new function id:' + response.data.data.function.id);

             var numChunks = Math.ceil(functionZip.length / chunkSize)-1;
             console.log('numChunks:' + numChunks);
             // set shared function data to null to force reload of function list on Function view
             sharedData.setFunctions(null);
             if (fCode[functionIterator]) {
               uploadFunctionCode(functionId, fCode[functionIterator]);
               uploadZipFile(functionZip, functionName, functionZip.length, functionId, functionZipDirectory, 0, numChunks);
             } else {
               document.getElementById("currentOperation").style.display = "none";
               document.getElementById("bar").style.display = "none";
               document.getElementById("metaData").style.visibility = "hidden";
               document.getElementById("uploadStatus").innerHTML = "An error occurred while importing workflow <b>" + workflowName + "</b> and its dependencies.<p><br>The zip archive does not contain the following function: <b>" + functionName + "/" + functionName + ".py</b>";
             }


           } else {
             importError = true;
             console.log("Failure status returned by addFunction");
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
           importError = true;
           console.log("Error occurred during addFunction");
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


     function createWorkflow(workflowName) {

       var token = $cookies.get('token');

       console.log('creating new workflow ' + workflowName);
       document.getElementById("currentOperation").innerHTML = "Creating workflow <b>" + workflowName + "</b>...";

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
          'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "addWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "name" : workflowName } } })
       }
       $http(req).then(function successCallback(response) {

           if (response.data.status=="success") {

             console.log('new workflow id:' + response.data.data.workflow.id);

             uploadWorkflow(response.data.data.workflow.id, workflowJson);
             $scope.reloadWorkflows();


           } else {
             importError = true;
             console.log("Failure status returned by addWorkflow");
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
           importError = true;
           console.log("Error occurred during addWorkflow");
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


     function uploadWorkflow(workflowId, workflowJson) {

       // base 64 encode workflow JSON
       var encodedWorkflowJSON = btoa(workflowJson);

       try {
         wJson = JSON.parse(workflowJson);

       } catch(e) {
         // invalid json
         console.log("Invalid workflow JSON.");
         importError = true;
         $scope.errorMessage = "Invalid workflow JSON.";

         $uibModal.open({
           animation: true,
           scope: $scope,
           templateUrl: 'app/pages/workflows/modals/errorModal.html',
           size: 'md',
         });

         return;

       }

       var workflowASLType = "unknown";

       if (workflowJson.includes('"StartAt"')) {
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
        var valid = ajv.validate('http://asl-validator.cloud/state-machine#', wJson);

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
            var valid_knix = ajv_knix.validate('http://knix-asl-validator.cloud/state-machine#', wJson);
            console.log("valid_knix: " + valid_knix);
            if (!valid_knix)
            {
              importError = true;
              $scope.errorMessage = "Invalid Amazon States Language (ASL) specification and/or KNIX ASL extensions.";
              $uibModal.open({
                animation: true,
                scope: $scope,
                templateUrl: 'app/pages/workflows/modals/errorModal.html',
                size: 'md',
              });
              return;
            }

            workflowASLType = "KNIX-specific";
        }
        else
        {
            workflowASLType = "AWS-compatible";
        }
      }

      var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadWorkflowJSON", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId, "json" : encodedWorkflowJSON, "ASL_type": workflowASLType } } })
       }
       $http(req).then(function successCallback(response) {

         if (response.data.status=="success") {
             console.log('Workflow JSON sucessfully uploaded.');
             newFunction(functionIterator);
         } else {
             importError = true;
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
           importError = true;
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

     }



     function uploadFunctionRequirements(functionId, functionRequirements) {
       var encodedFunctionRequirements = btoa(functionRequirements);

       var token = $cookies.get('token');
       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "uploadFunctionRequirements", "data" : { "user" : { "token" : token } , "function" : { "id" : functionId, "requirements" : encodedFunctionRequirements } } })
       }
       $http(req).then(function successCallback(response) {

       if (response.data.status=="success") {
             console.log('Function requirements sucessfully uploaded.');
           } else {
             importError = true;
             console.log("Failure status returned by uploadFunctionRequirements");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (workflowImportModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           importError = true;
           console.log("Error occurred during uploadFunctionRequirments");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (workflowImportModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     }

     $scope.$on('$destroy', function(){
         workflowImportModalVisible = false;
         if ($scope.workflowToBeImported) {
           $scope.workflowToBeImported = "";
           var landingUrl = "http://" + window.location.host + window.location.pathname + '#' + window.location.hash.substr(1);
           window.location.href = landingUrl;
         }
     });

     function uploadFunctionCode(functionId, functionCode) {
       // base 64 encode function code
       var encodedFunctionCode = btoa(functionCode);

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
             if (fRequirements[functionIterator]) {
               uploadFunctionRequirements(functionId, fRequirements[functionIterator]);
             }
           } else {
             importError = true;
             console.log("Failure status returned by uploadFunctionCode");
             console.log("Message:" + response.data.data.message);
             $scope.errorMessage = response.data.data.message;
             if (workflowImportModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           importError = true;
           console.log("Error occurred during uploadFunctionCode");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (workflowImportModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     }
   });
}());
