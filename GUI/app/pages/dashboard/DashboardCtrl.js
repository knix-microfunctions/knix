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

(function () {
    'use strict';
 
    angular.module('MfnWebConsole.pages.dashboard')
    .controller('DashboardCtrl', DashboardCtrl);

    var versionNumber = "";

    /** @ngInject */
    function DashboardCtrl($scope, $http, sharedProperties) {
    
        var urlPath = sharedProperties.getUrlPath();

        if (!versionNumber) {

            var req = {
              method: 'POST',
              url: urlPath,
              headers: {
                   'Content-Type': 'application/json'
              },
     
              data:   JSON.stringify({ "action" : "version", "data" : ""})
     
            }
     
            $http(req).then(function successCallback(response) {
     
                if (response.data.status=="success") {
                  versionNumber = "Version " + response.data.data.message;
                } else {
                  console.log("Failure status returned by version request");
                  console.log("Message:" + response.data.data.message);
                  
                }
            }, function errorCallback(response) {
                console.log("Error occurred during version request");
                console.log("Response:" + response);
                
            });
        
        }

        $scope.getVersionNumber = function() {
            return versionNumber;
        }
    }   

})();