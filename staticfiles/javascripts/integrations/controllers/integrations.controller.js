/**
* IntegrationsController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.integrations.controllers')
    .controller('IntegrationsController', IntegrationsController);
  
  IntegrationsController.$inject = ['$scope', 'Integrations', 'Authentication', '$location', 'ngDialog', '$filter', '$window', '$routeParams', '$document'];

  /**
  * @namespace IntegrationsController
  */
  function IntegrationsController($scope, Integrations, Authentication, $location, ngDialog, $filter, $window, $routeParams, $document) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.systems = []; 
    vm.accessTokens = [];
    
    
    var source = '';
    if (!(typeof $routeParams == 'undefined')) {
  	  source = $routeParams.source; 
  	  if ($routeParams.tabname)
  	    $scope.tabname = $routeParams.tabname; 
  	  else
  		$scope.tabname = 'new';  
    }
    else {
    	$scope.tabname = 'new';
    }
    vm.source = source;
    
    $scope.addSystem = addSystem;
    $scope.sfdcSubmit = sfdcSubmit;
    
/*    $scope.$on('$viewContentLoaded', function(){   
	    //setActiveTab();
    });

    $scope.$watch(function() { return $location.url(); }, function(url) {
    	if (url) { 
    		//setActiveTab();
    	}
    });*/
    
    $scope.tabs = [
             	  { link: '/integrations/new', label: 'New', name: 'new', active:false},
             	  { link: '/integrations/configured', label: 'Configured', name: 'configured', active:false}
             	               ];
    
    if (!($scope.selectedTab))
    {
       for (var i=0; i < $scope.tabs.length; i++) { 
  		   if ($scope.tabs[i].name == $scope.tabname)
  		   {
  			 $scope.selectedTab = $scope.tabs[i];
  		   }
  	   }
    }
    	
    
	$scope.setSelectedTab = function(tab) {  
	    $scope.selectedTab = tab;
	    //loop($scope.tabs, tab.name)
    }

    $scope.tabClass = function(tab) { 
		if ($scope.selectedTab == tab) {
			return "active";
		}
		else {
			return "";
		}
    }
    
    activate();

    /**
    * @name sfdcSubmit
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.IntegrationsController
    */
    function sfdcSubmit() {   
	    if (Authentication.getAuthenticatedAccount()) 
	    	Integrations.sfdcAuthorize(Authentication.getAuthenticatedAccount().username).then(AuthorizeSuccessFn, AuthorizeErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    function AuthorizeSuccessFn(data, status, headers, config) { 
    	if (typeof eval('data.data.' + vm.source + '_access_token') != 'undefined')
    	{
    		vm.accessTokens[vm.source] = eval('data.data.' + vm.source + '_access_token');
    		toastr.success(vm.accessTokens[vm.source]);
    	}
    	else if (typeof data.data.auth_url != 'undefined')
            window.location = data.data.auth_url;
    	else if (typeof data.data.error != 'undefined')
    		toastr.error(data.data.error);
         //$window.location.reload();
      }
    
    function AuthorizeErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Authorization URL could not be retrieved');
      }
    
    function activate() { // show the initial integrations screen
    	
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	if (!authenticatedAccount) 
    	{
    	  toastr.error('Your company cannot be identified');
    	  $location.url('/');
    	}
    	else 
    	{
    	  Integrations.superGetIntegrations().then(IntegrationSuccessFn, IntegrationErrorFn);	
    	}
    }
    
    function IntegrationSuccessFn(data, status, headers, config) { 
    	vm.systems = data.data;
     }
   
   function IntegrationErrorFn(data, status, headers, config) {
       toastr.error('Could not retrieve systems for integration');
     }
   
    function getOauthToken() {
        // Redirect if not logged in
        if (!authenticatedAccount) {
          $location.url('/');
          toastr.error('You are not authorized to view this page.');
        } else {
        	Integrations.oauthGetToken(source).then(OauthSuccessFn, OauthErrorFn);
        }
    }
    
    function OauthSuccessFn(data, status, headers, config) { 
    	if (typeof eval('data.data.' + vm.source + '_access_token') != 'undefined')
    	{
    		vm.accessTokens[vm.source] = eval('data.data.' + vm.source + '_access_token');
    		toastr.success(vm.accessTokens[vm.source]);
    	}
     }
   
   function OauthErrorFn(data, status, headers, config) {
       // $location.url('/');
       toastr.error('Access token could not be retrieved');
     }
   
   function loop(obj, selectedName) {
	   for (var i=0; i < obj.length; i++) {
		   if (obj[i].name == selectedName)
			   obj[i].active = true;
		   else
			   obj[i].active = false;
	   }
   }
   
   function addSystem(system) {
	   Integrations.setNewSystem(system);
	   window.location = '/integrations/new/' + system.code;
   }
   
  }
})();