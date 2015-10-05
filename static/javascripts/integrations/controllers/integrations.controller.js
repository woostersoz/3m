/**
* IntegrationsController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.integrations.controllers')
    .controller('IntegrationsController', IntegrationsController);
  
  IntegrationsController.$inject = ['$scope', 'Integrations', 'Authentication', 'Common', '$location', '$filter', '$window', '$state', '$stateParams', '$document'];

  /**
  * @namespace IntegrationsController
  */
  function IntegrationsController($scope, Integrations, Authentication, Common, $location,  $filter, $window, $state, $stateParams, $document) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.newSystems = []; 
    vm.accessTokens = [];
    
    $scope.addSystem = addSystem;
    $scope.deleteSystem = deleteSystem;
    $scope.authorize = authorize;
    $scope.confirmedDeleteSystem = confirmedDeleteSystem;
    $scope.cancelDeleteSystem = cancelDeleteSystem;
    $scope.editSystem = editSystem;
    
    $scope.retrieve_campaigns = retrieve_campaigns;
    $scope.retrieve_campaigns_daily = retrieve_campaigns_daily;
    $scope.retrieve_leads = retrieve_leads;
    $scope.retrieve_leads_daily = retrieve_leads_daily;
    $scope.retrieve_contacts = retrieve_contacts;
    $scope.retrieve_contacts_daily = retrieve_contacts_daily;
    $scope.retrieve_activities = retrieve_activities;
    $scope.retrieve_activities_daily = retrieve_activities_daily;
    $scope.retrieve_opportunities = retrieve_opportunities;
    $scope.retrieve_opportunities_daily = retrieve_opportunities_daily;

    $scope.meta = meta;
    $scope.$state = $state;
    $scope.scopeName = $state.current.name
    $scope.dataSelection = "";
    
    if ($scope.scopeName == 'goog-test')
    {
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	Integrations.googTest(authenticatedAccount.company);
    }
    
    if ($scope.scopeName == 'fbok-test')
    {
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	Integrations.fbokTest(authenticatedAccount.company);
    }
    
    var source = '';  
    if (!(typeof $stateParams == 'undefined')) {
      if ($stateParams.source)
  	    source = $stateParams.source; 
  	  if ($stateParams.tabname)
  	    $scope.tabname = $stateParams.tabname; 
  	  else
  		$scope.tabname = 'new';  
  	  if ($stateParams.result)
  		  if ($stateParams.result == 'success')
  			  toastr.success("Integration added/edited - Woo hoo!")
  		  else
  			  toastr.error("Ouch, something went wrong!")
  	  if ($stateParams.object && $stateParams.retrievalsource)
  	  {
  		  
  		  var method_name = 'retrieve_' +  $stateParams.object;
  		  eval("$scope." + method_name + "()");
  	  }
  	  if ($scope.scopeName == '/data') 
  	  {
  		Integrations.superGetExistingIntegrations().then(OldIntegrationSuccessFn, OldIntegrationErrorFn);
      }
    }
    else {
    	$scope.tabname = 'new';
    }
    $scope.breadcrumbName = Common.capitalizeFirstLetter($scope.tabname);
    vm.source = source;  
    if (source && source.length > 0 && $stateParams.code && $stateParams.state) // this will match the SFDC and Slack auth URL 
    	getOauthToken(source, $stateParams.code, $stateParams.state, ""); 
    else if (source && source.length > 0 && $stateParams.code) // this will match Buffer, Google and Facebook
    	getOauthToken(source, $stateParams.code, "", ""); 
    else if (source && source.length > 0 && $stateParams.access_token && $stateParams.refresh_token && $stateParams.expires_in) // this will match the Hubspot auth URL
    	getOauthToken(source, $stateParams.access_token, "", $stateParams.refresh_token); 
    else if (source && source.length > 0 && $stateParams.oauth_token && $stateParams.oauth_verifier ) // this will match the twitter oauth signature
    	getOauthToken(source, $stateParams.oauth_token, $stateParams.oauth_verifier, ""); 
    
    
    
    
    $scope.getId = function(system) {
    	return (JSON.parse(system.company_info.record_id).$oid + "_" + system.company_info.code);
    }
    
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
    * @name authorize
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.IntegrationsController
    */
    function authorize(companyInfo) {   
	    if (Authentication.getAuthenticatedAccount()) 
	    	Integrations.authorize(Authentication.getAuthenticatedAccount().company, companyInfo).then(AuthorizeSuccessFn, AuthorizeErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    function AuthorizeSuccessFn(data, status, headers, config) { 
/*    	if (typeof eval('data.data.' + vm.source + '_access_token') != 'undefined')
    	{
    		vm.accessTokens[vm.source] = eval('data.data.' + vm.source + '_access_token');
    		toastr.success(vm.accessTokens[vm.source]);
    	}*/
    	if (typeof data.data.auth_url != 'undefined')
    	{   
            window.location = data.data.auth_url;
    	}
    	else if (typeof data.data.error != 'undefined')
    		toastr.error(data.data.error);
    	else
    	{
    		toastr.success(data.data);
            //$window.location.reload();
    		Integrations.superGetExistingIntegrations().then(OldIntegrationSuccessFn, OldIntegrationErrorFn);
    	}
      }
    
    function AuthorizeErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Authorization could not be completed');
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
    	  Integrations.superGetNewIntegrations().then(IntegrationSuccessFn, IntegrationErrorFn);	
    	  Integrations.superGetExistingIntegrations().then(OldIntegrationSuccessFn, OldIntegrationErrorFn);
    	}
    	
    	
    }
    
    function IntegrationSuccessFn(data, status, headers, config) { 
    	vm.newSystems = data.data;
     }
   
    function IntegrationErrorFn(data, status, headers, config) {
       toastr.error('Could not retrieve any system for integration');
     }
   
    function OldIntegrationSuccessFn(data, status, headers, config) { 
    	vm.existingSystems = data.data;
    	$scope.existingSystems = [];
        for (var i=0, length = vm.existingSystems.length; i < length; i++) {
        	$scope.existingSystems[$scope.getId(vm.existingSystems[i])] = false;
        }
     }
   
    function OldIntegrationErrorFn(data, status, headers, config) {
       toastr.error('Could not retrieve any system for integration');
     }
   
    function getOauthToken(source, code, state, refresh_token) {
        // Redirect if not logged in
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
        if (!authenticatedAccount) {
          $location.url('/');
          toastr.error('You are not authorized to view this page.');
        } else {
        	Integrations.oauthGetToken(source, code, state, authenticatedAccount.company, refresh_token).then(OauthSuccessFn, OauthErrorFn);
        }
    }
    
    function OauthSuccessFn(data, status, headers, config) { 
    	if (typeof eval('data.data.' + vm.source + '_access_token') != 'undefined')
    	{
    		vm.accessTokens[vm.source] = eval('data.data.' + vm.source + '_access_token');
    		toastr.success(vm.accessTokens[vm.source]);
    	    window.location = '/integrations/configured/'
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
   
   function editSystem(system) {
	   Integrations.setNewSystem(system);
	   window.location = '/integrations/edit/' + system.code;
   }
   
   function deleteSystem(system) {
	   /*ngDialog.openConfirm({
		   template: 'modalDialogId',
		   className: 'ngdialog-theme-default'
	   }).
	   then(function (value) {
		   toastr.success("Y");
	   }, function (value) { 
		   toastr.error("N");
	   });*/
       // Redirect if not logged in
   	   var authenticatedAccount = Authentication.getAuthenticatedAccount();
       if (!authenticatedAccount) {
         $location.url('/');
         toastr.error('You are not authorized to delete data.');
       } else {
    	   $scope.existingSystems[$scope.getId(system)] = true;
    	   //toastr.success($scope.getId(system));
       }     
   }
   
   function confirmedDeleteSystem(system) {
	 Integrations.deleteSystem(system).then(ConfirmedDeleteSuccessFn, ConfirmedDeleteErrorFn);
   }
   
   function ConfirmedDeleteSuccessFn(data, status, headers, config) { 
   	if (data.data)
   	{
   		toastr.success("Integration deleted");
   		Integrations.superGetExistingIntegrations().then(OldIntegrationSuccessFn, OldIntegrationErrorFn);
   	}
    }
  
  function ConfirmedDeleteErrorFn(data, status, headers, config) {
      // $location.url('/');
      toastr.error('Integration could not be deleted');
    }
  
  function cancelDeleteSystem(system) {
	  $scope.existingSystems[$scope.getId(system)] = false;
  }
  
  function retrieve_opportunities(code) {
	  	var account = Authentication.getAuthenticatedAccount();
		    if (account) 
		    	Integrations.retrieveOpportunitiesFromSource(account.company, code).then(RetrieveOpportunitiesSuccessFn, RetrieveOpportunitiesErrorFn);
		    else {
		    	toastr.error('You need to login first');
		    	$location.path('/login'); 
		    }
	  }
  
  function retrieve_opportunities_daily(code) {
	  	var account = Authentication.getAuthenticatedAccount();
		    if (account) 
		    	Integrations.retrieveOpportunitiesFromSourceDaily(account.company, code).then(RetrieveOpportunitiesSuccessFn, RetrieveOpportunitiesErrorFn);
		    else {
		    	toastr.error('You need to login first');
		    	$location.path('/login'); 
		    }
	  }
	  
	  function RetrieveOpportunitiesSuccessFn(data, status, headers, config) {
		    if (typeof data.data === "object") {
		    	toastr.info("Starting retrieval of opportunities in background");
		    }
		    else
		    {
		        toastr.error(data.data); 
		    }
	  }

	  function RetrieveOpportunitiesErrorFn(data, status, headers, config) {
	  // $location.url('/');
	      toastr.error('Opportunities could not be retrieved');
	  }
	  
  
  function retrieve_campaigns(code) {
  	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Integrations.retrieveCampaignsFromSource(account.company, code).then(RetrieveCampaignsSuccessFn, RetrieveCampaignsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
  }
  
  function retrieve_campaigns_daily(code) {
	  	var account = Authentication.getAuthenticatedAccount();
		    if (account) 
		    	Integrations.retrieveCampaignsFromSourceDaily(account.company, code).then(RetrieveCampaignsSuccessFn, RetrieveCampaignsErrorFn);
		    else {
		    	toastr.error('You need to login first');
		    	$location.path('/login'); 
		    }
	  }
  
  function RetrieveCampaignsSuccessFn(data, status, headers, config) {
	    if (typeof data.data === "object") {
	    	toastr.info("Starting retrieval of campaigns in background");
	    }
	    else
	    {
	        toastr.error(data.data); 
	    }
  }

  function RetrieveCampaignsErrorFn(data, status, headers, config) {
  // $location.url('/');
      toastr.error('Campaigns could not be retrieved');
  }
  

	  function retrieve_leads(code) {
		  	var account = Authentication.getAuthenticatedAccount();
			    if (account) 
			    	Integrations.retrieveLeadsFromSource(account.company, code).then(RetrieveLeadsSuccessFn, RetrieveLeadsErrorFn);
			    else {
			    	toastr.error('You need to login first');
			    	$location.path('/login'); 
			    }
		  }
	  
	  function retrieve_leads_daily(code) {
		  	var account = Authentication.getAuthenticatedAccount();
			    if (account) 
			    	Integrations.retrieveLeadsFromSourceDaily(account.company, code).then(RetrieveLeadsSuccessFn, RetrieveLeadsErrorFn);
			    else {
			    	toastr.error('You need to login first');
			    	$location.path('/login'); 
			    }
		  }
		  
		  function RetrieveLeadsSuccessFn(data, status, headers, config) {
			    if (typeof data.data === "object") {
			    	toastr.info("Starting retrieval of leads in background");
			    }
			    else
			    {
			        toastr.error(data.data); 
			    }
		  }

		  function RetrieveLeadsErrorFn(data, status, headers, config) {
		  // $location.url('/');
		      toastr.error('Leads could not be retrieved');
		  }
		  
		  function retrieve_contacts(code) {
			  	var account = Authentication.getAuthenticatedAccount();
				    if (account) 
				    	Integrations.retrieveContactsFromSource(account.company, code).then(RetrieveContactsSuccessFn, RetrieveContactsErrorFn);
				    else {
				    	toastr.error('You need to login first');
				    	$location.path('/login'); 
				    }
			  }
		  
		  function retrieve_contacts_daily(code) {
			  	var account = Authentication.getAuthenticatedAccount();
				    if (account) 
				    	Integrations.retrieveContactsFromSourceDaily(account.company, code).then(RetrieveContactsSuccessFn, RetrieveContactsErrorFn);
				    else {
				    	toastr.error('You need to login first');
				    	$location.path('/login'); 
				    }
			  }
			  
			  function RetrieveContactsSuccessFn(data, status, headers, config) {
				    if (typeof data.data === "object") {
				    	toastr.info("Starting retrieval of contacts in background");
				    }
				    else
				    {
				        toastr.error(data.data); 
				    }
			  }

			  function RetrieveContactsErrorFn(data, status, headers, config) {
			  // $location.url('/');
			      toastr.error('Contacts could not be retrieved');
			  }
		  
		  function retrieve_activities(code) {
			  	var account = Authentication.getAuthenticatedAccount();
				    if (account) 
				    	Integrations.retrieveActivitiesFromSource(account.company, code).then(RetrieveActivitiesSuccessFn, RetrieveActivitiesErrorFn);
				    else {
				    	toastr.error('You need to login first');
				    	$location.path('/login'); 
				    }
			  }
		  
		  function retrieve_activities_daily(code) {
			  	var account = Authentication.getAuthenticatedAccount();
				    if (account) 
				    	Integrations.retrieveActivitiesFromSourceDaily(account.company, code).then(RetrieveActivitiesSuccessFn, RetrieveActivitiesErrorFn);
				    else {
				    	toastr.error('You need to login first');
				    	$location.path('/login'); 
				    }
			  }
			  
			  function RetrieveActivitiesSuccessFn(data, status, headers, config) {
				    if (typeof data.data === "object") {
				    	toastr.info("Starting retrieval of activities in background");
				    }
				    else
				    {
				        toastr.error(data.data); 
				    }
			  }

			  function RetrieveActivitiesErrorFn(data, status, headers, config) {
			  // $location.url('/');
			      toastr.error('Activities could not be retrieved');
			  }
		  
		  function meta(code, object) {
			  	var account = Authentication.getAuthenticatedAccount();
				    if (account) 
				    	Integrations.getMetaData(account.company, code, object).then(GetMetaSuccessFn, GetMetaErrorFn);
				    else {
				    	toastr.error('You need to login first');
				    	$location.path('/login'); 
				    }
			  }
			  
			  function GetMetaSuccessFn(data, status, headers, config) {
				    if (typeof data.data === "object") {
				    	toastr.success("Yowza! Metadata retrieved");
				    }
				    else
				    {
				        toastr.error(data.data); 
				    }
			  }

			  function GetMetaErrorFn(data, status, headers, config) {
			  // $location.url('/');
			      toastr.error('Metadata could not be retrieved');
			  }
			  
			  
			  
  
  function isJson(str) {
  	try {
  		JSON.parse(str);
  	}
  	catch(e) {
  		return false;
  	}
  	return true;
  } 
  
  }
})();