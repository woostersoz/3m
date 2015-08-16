/**
* CompanyController
* @namespace mmm.integrations.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.company.controllers')
    .controller('CompanyController', CompanyController);
  
  CompanyController.$inject = ['$scope', 'Company', 'Authentication', '$location', '$filter', '$window', '$state', '$stateParams', '$document'];

  /**
  * @namespace CompanyController
  */
  function CompanyController($scope, Company, Authentication, $location, $filter, $window, $state, $stateParams, $document) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.leadCount = 0;
    vm.campaignCount = 0;
    //$scope.getLeadCount = getLeadCount;
    //$scope.getCampaignCount = getCampaignCount;
    
    
    $scope.$state = $state;
    $scope.scopeName = $state.current.name
  
    
    
    activate();
    
    function activate() { // show the initial integrations screen
    	
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
    	if (!authenticatedAccount) 
    	{
    	  toastr.error('Your company cannot be identified');
    	  $location.url('/');
    	}
    	else 
    	{ 
    	  Company.getLeadCount(authenticatedAccount.company).then(LeadCountSuccessFn, LeadCountErrorFn);	
    	  Company.getCampaignCount(authenticatedAccount.company).then(CampaignCountSuccessFn, CampaignCountErrorFn);
    	}
    	
    	
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
   
  
  }
})();