/**
* CompanyController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.company.controllers')
    .controller('CompanyController', CompanyController);
  
  CompanyController.$inject = ['$scope', 'Company', 'Authentication', '$location', '$filter', '$window', '$state', '$stateParams', '$document', 'Common', 'Integrations'];

  /**
  * @namespace CompanyController
  */
  function CompanyController($scope, Company, Authentication, $location, $filter, $window, $state, $stateParams, $document, Common, Integrations) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    var authenticatedAccount = Authentication.getAuthenticatedAccount();
    vm.leadCount = 0;
    vm.campaignCount = 0;
    //$scope.getLeadCount = getLeadCount;
    //$scope.getCampaignCount = getCampaignCount;
    
    
    $scope.$state = $state;
    $scope.scopeName = $state.current.name;
    
    
    if (!(typeof $stateParams == 'undefined')) {
        if ($stateParams.source)
    	    source = $stateParams.source; 
    	  if ($stateParams.tabname)
    	  {
    	    $scope.tabname = $stateParams.tabname; 
    	  }
    	  
    	  else
    		$scope.tabname = 'statuses'; //details
    }
    else {
    	$scope.tabname = 'statuses'; //details
    }
    
    if ($scope.tabname == 'statuses') 
    	Integrations.retrieveLeadStatusMapping(authenticatedAccount.company).then(LeadStatusMappingSuccessFn, LeadStatusMappingErrorFn);
    
    $scope.breadcrumbName = Common.capitalizeFirstLetter($scope.tabname);
    
    $scope.rev_stages = [{'stage': 'premql', 'name': 'Raw Leads'}, {'stage': 'mql', 'name': 'MQL'}, {'stage': 'sal', 'name': 'SAL'}, {'stage': 'sql', 'name': 'SQL'}, {'stage': 'opps', 'name': 'Deals'}, {'stage': 'closedwon', 'name': 'Won'}, {'stage': 'recycle', 'name': 'Recycle'}];
    $scope.entered_lead_statuses = {'premql_statuses': [], 'mql_statuses': [], 'sal_statuses': [], 'sql_statuses': [], 'opps_statuses':[], 'closedwon_statuses': [], 'recycle_statuses': []};                     
  
    $scope.tabs = [
              	  //{ link: '/setup/details', label: 'Details', name: 'details', active:false},
              	  { link: '/setup/statuses', label: 'Statuses', name: 'statuses', active:false}
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
    
    $scope.saveLeadStatusMapping = saveLeadStatusMapping;
    
    $scope.cancelLeadStatusMapping = function() {
    	$location.path('/dashboards'); 
    }
    
    
    
    activate();
    
    function activate() { // show the initial integrations screen
    	
    	$scope.htmlString = "";
    	
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	if (!authenticatedAccount) 
    	{
    	  toastr.error('Your company cannot be identified');
    	  $location.url('/');
    	}
    	else 
    	{ 
    	  //Company.getLeadCount(authenticatedAccount.company).then(LeadCountSuccessFn, LeadCountErrorFn);	
    	  //Company.getCampaignCount(authenticatedAccount.company).then(CampaignCountSuccessFn, CampaignCountErrorFn);
    		Integrations.getLeadStatuses(authenticatedAccount.company).then(LeadStatusesSuccessFn, LeadStatusesErrorFn);
    	}
    	
    	// call the screenshot function and pass the URL
    	if ($state.current.name == 'screenshot') {
    		Common.generateScreenshot($stateParams.url);
    		console.log('Capture ' + $stateParams.url);
    	}
    	
    	
    }
    
    
    function LeadStatusMappingSuccessFn(data, status, headers, config) { 
    	$scope.status_mappings_done = false;
    	if (data.data.status_mappings)
    	{
    		for (var key in $scope.entered_lead_statuses)
    		{
    			if ($scope.entered_lead_statuses.hasOwnProperty(key)) {
    				if (data.data.status_mappings.hasOwnProperty(key)) // fill list from existing mappings
    					$scope.entered_lead_statuses[key] = data.data.status_mappings[key];
    			}
    		}
    		
    		$scope.status_mappings_done = true;
    		
    		if (!$scope.availableLeadStatusesFiltered)
	    		filterAvailableLeadStatuses();
    	}
    	else 
    		toastr.error('Could not retrieve status mappings');
    }
    
    function LeadStatusMappingErrorFn(data, status, headers, config) {  
    	
    }
    
    function LeadStatusesSuccessFn(data, status, headers, config) { 
    	if (data.data.error)
    		toastr.error(data.data.error)
    	else if (data.data.statuses)
    	{
	    	$scope.lead_statuses = data.data.statuses;
	    	$scope.lead_status_system = data.data.source_system; 
	    	if (!$scope.availableLeadStatusesFiltered)
	    		filterAvailableLeadStatuses();
	    	$scope.models = {selected:null, lists: {"Available Statuses": $scope.lead_statuses}};
    	}
     }
   
    function LeadStatusesErrorFn(data, status, headers, config) {
       toastr.error('Could not get lead statuses');
     }
    
    function filterAvailableLeadStatuses() {
    	if ($scope.lead_statuses == undefined || !$scope.status_mappings_done) return;
		for (var key in $scope.entered_lead_statuses) // remove items from available status
		{
			if ($scope.entered_lead_statuses.hasOwnProperty(key)) {
	    	for (var i=0; i < $scope.entered_lead_statuses[key].length; i++ ) 
				{
					$scope.lead_statuses = Common.removeItemFromArray($scope.lead_statuses, $scope.entered_lead_statuses[key][i]);
				}
			}
		}
		$scope.availableLeadStatusesFiltered = true;
	}
    
    function LeadCountSuccessFn(data, status, headers, config) { 
    	vm.leadCount = data.data.count;
     }
   
    function LeadCountErrorFn(data, status, headers, config) {
       toastr.error('Could not count leads');
     }
   
    function CampaignCountSuccessFn(data, status, headers, config) { 
    	vm.campaignCount = data.data.count;
     }
   
    function CampaignCountErrorFn(data, status, headers, config) {
       toastr.error('Could not count campaigns');
     }
     
    $scope.loadStatuses = function($query) { //console.log('fire');
    	return Common.containsItemsByAttr($scope.lead_statuses, 'status', $query);
        /*return  $scope.lead_statuses.filter(function(status) {
        	return status.status.toLowerCase().indexOf($query.toLowerCase()) != -1;
        });*/
    };
    
    function saveLeadStatusMapping() {
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	if (!authenticatedAccount) 
    	{
    	  toastr.error('Your company cannot be identified');
    	  $location.url('/');
    	}
    	else 
    	{ 
    		Integrations.saveLeadStatusMapping(authenticatedAccount.company, $scope.entered_lead_statuses).then(LeadStatusMappingSuccess, LeadStatusMappingError);
    	}
    }
    
    function LeadStatusMappingSuccess(data, status, headers, config) { 
    	if (data.data.success)
    	   toastr.success('Lead status mapping saved');
    	else toastr.error('Lead status mapping could not be saved');
    }
    
    function LeadStatusMappingError(data, status, headers, config) { 
    	toastr.error('Lead status mapping could not be saved');
    }
    
  
  }
})();