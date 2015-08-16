/**
* New-IntegrationController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.integrations.controllers')
    .controller('NewIntegrationController', NewIntegrationController);
  
  NewIntegrationController.$inject = ['$scope', 'Integrations',  'Authentication', '$location', 'ngDialog', '$filter', '$window', '$routeParams', '$document'];

  /**
  * @namespace NewIntegrationController
  */
  function NewIntegrationController($scope, Integrations, Authentication, $location, ngDialog, $filter, $window, $routeParams, $document) {
    var vm = this;
    vm.systems = [];
    
    vm.isAuthenticated = Authentication.isAuthenticated();
    activate();
    
	  function activate() { 
		  
		  var authenticatedAccount = Authentication.getAuthenticatedAccount();
		  
		  if (!authenticatedAccount) {
	          $location.url('/');
	          toastr.error('You are not authorized to view this page.');
	        } else {  
	          $scope.systems = Integrations.getNewSystem();
	  	  	  console.log($scope.systems);
	  	  	  Integrations.createNewIntegration($scope.systems[0].code).then(NewIntegrationSuccessFxn, NewIntegrationErrorFxn);
	        }
      }

	  function NewIntegrationSuccessFxn(data, status, headers, config) {
		  
	  }
	  
      function NewIntegrationErrorFxn(data, status, headers, config) {
		  
	  }
  
    
 }
})();