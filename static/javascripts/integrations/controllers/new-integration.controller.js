/**
* New-IntegrationController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.integrations.controllers')
    .controller('NewIntegrationController', NewIntegrationController);
  
  NewIntegrationController.$inject = ['$scope', 'Integrations',  'Authentication', '$location', '$filter', '$window', '$state', '$stateParams', '$document', 'djangoForm'];

  /**
  * @namespace NewIntegrationController
  */
  function NewIntegrationController($scope, Integrations, Authentication, $location, $filter, $window, $state, $stateParams, $document, djangoForm) {
    var vm = this;
    vm.systems = [];
    
    vm.isAuthenticated = Authentication.isAuthenticated();
    
    if (!(typeof $stateParams == 'undefined')) {
    	if ($stateParams.code)
    		$scope.code = $stateParams.code; 
    	else
    	{
    		toastr.error("Oops, something went wrong!");
    	    return;
    	}
    }
    else {
    	toastr.error("Oops, something went wrong!");
	    return;
    }
    
    $scope.$state = $state;
    $scope.scopeName = $state.current.name
    $scope.editMode = false;
    
    $scope.cancel = cancel;
    
/*    $scope.$on('$locationChangeStart',function(evt, absNewUrl, absOldUrl) {
    	
    });
  */
   	activate();
 
    
    
	  function activate() { 
		  
		  $scope.htmlString = "";
		  
		  var authenticatedAccount = Authentication.getAuthenticatedAccount();
		  
		  if (!authenticatedAccount) {
	          $location.url('/');
	          toastr.error('You are not authorized to view this page.');
	      } 
		  else 
	      {  
	          $scope.systems = Integrations.getNewSystem();
	          if ($scope.scopeName == 'integrations-new')
	          {
	        	  $scope.editMode = false;  
		  	  	  Integrations.createNewIntegration($scope.systems[0].code).then(NewIntegrationSuccessFxn, NewIntegrationErrorFxn);
		      }
	          else if ($scope.scopeName == 'integrations-edit')
	          {
	        	  $scope.editMode = true;
	        	  Integrations.editSystem($scope.systems[0]).then(NewIntegrationSuccessFxn, NewIntegrationErrorFxn);
		      }	  
	      }
      }

	  function NewIntegrationSuccessFxn(data, status, headers, config) { 
		  $scope.templateHtml = data.data;
		  $scope.htmlString = "changed";
	  }
	  
      function NewIntegrationErrorFxn(data, status, headers, config) {
		  
	  }
      
      function EditSuccessFn(data, status, headers, config) { 
  	   	if (data.data)
  	   	{
  	   		toastr.success("Integration edited");
  	   	    $window.location.href = '/integrations/configured/success';
  	   	}
  	  }
  	  
    function EditErrorFn(data, status, headers, config) {
  	      // $location.url('/');
  	      toastr.error('Integration could not be edited');
  	    }
      
      function cancel() {
    	  $window.history.back();
    	  //$window.location.href = '/integrations/new';
      }
  
      $scope.submit = function() { 
          if ($scope.integration) {
        	  Integrations.postFormData($scope.integration, $scope.systems[0].code).then(PostIntegrationSuccessFxn, PostIntegrationErrorFxn);
          }
          return false;
      };
    
	  function PostIntegrationSuccessFxn(data, status, headers, config) {
		  //if (!djangoForm.setErrors($scope.integration_form, data.data.errors)) {
              // on successful post, redirect onto success page
              //$window.location.href = data.success_url;
			  //$window.location.href = '/integrations/configured/success';
		  if (data.data.errors)
		  {   
			  var errorMsg = '';
			  for (var x in data.data.errors)
			  {
				  if (data.data.errors.hasOwnProperty(x))
					  errorMsg+= x + " complains - " + eval("data.data.errors." + x + "[0]") + " ";
			  }
			  toastr.error("Error: " + errorMsg);		  
		  }
		  else 
		  {
			  $window.location.href = '/integrations/configured/success';
			  toastr.success(data.data);
		  }
	  }
	  
      function PostIntegrationErrorFxn(data, status, headers, config) {
		  toastr.error("Error: " + data.data);
	  }
 }
})();