/**
 * @author v.lugovksy
 * created on 16.12.2015
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.theme.components')
      .controller('MsgCenterCtrl', MsgCenterCtrl);

  /** @ngInject */
  function MsgCenterCtrl($scope, $sce, $cookies) {
    $scope.users = {
      0: {
        name: '',
      }
    };

    $scope.notifications = [
    ];

    $scope.messages = [
    ];

    $scope.logOut = function() {
      document.cookie = "token=-1; path=/;";
      //$cookies.remove('token');
      console.log('Logging out...');
      document.location.href="auth.html";
    }

    $scope.getEmail = function() {
      return $cookies.get('email');
    }

    $scope.getMessage = function(msg) {
      var text = msg.template;
      if (msg.userId || msg.userId === 0) {
        text = text.replace('&name', '<strong>' + $scope.users[msg.userId].name + '</strong>');
      }
      return $sce.trustAsHtml(text);
    };
  }
})();
