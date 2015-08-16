/**
* CampaignsController
* @namespace mmm.campaigns.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.campaigns.controllers', ['datatables'])
    .controller('CampaignsController', CampaignsController);
  
  CampaignsController.$inject = ['$scope', 'Campaigns', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$state', '$stateParams', '$document', '$window'];

  /**
  * @namespace CampaignsController
  */
  function CampaignsController($scope, Campaigns, Authentication, $state, $stateParams, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $filter, $document, $window) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.campaigns = []; 
    $scope.campaigns = [];
    $scope.totalCampaigns = 0;
    $scope.campaignsPerPage = 10;
    $scope.currentPage = 1;
    
    if (!(typeof $stateParams == 'undefined')) {
    	if ($stateParams.system)
    	{
    		$scope.code = $stateParams.code; 
    		getCampaignsBySource($scope.code);
    	}
    	else
    	{
    		/*toastr.error("Oops, something went wrong!");
    	    return;*/
    		activate();
    	}
    }
    else {
    	toastr.error("Oops, something went wrong!");
	    return;
    }
    
    
    
/*    $scope.$state = $state;
    $scope.scopeName = $state.current.name*/
    



    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.CampaignsController
    */
    function activate() {   
    	getCampaigns(1);
    	$scope.pagination = { current: 1 };
    	
    }
    
    function getCampaigns(pageNumber)
    {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Campaigns.all(account.company, pageNumber, $scope.campaignsPerPage).then(CampaignsSuccessFn, CampaignsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
   
    function CampaignsSuccessFn(data, status, headers, config) { 
	 if (data.data.results) // they could contain both Mkto and SFDC leads
	 {  
		$scope.totalCampaigns = data.data.count;
 		$scope.thisSetCount = data.data.results.length;
		// initialize the start and end counts shown near pagination control
		$scope.startCampaignCounter = ($scope.currentPage - 1) * $scope.campaignsPerPage + 1;
		$scope.endCampaignCounter = ($scope.thisSetCount < $scope.campaignsPerPage) ? $scope.startCampaignCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.campaignsPerPage;
		
		vm.campaigns = Campaigns.cleanCampaignsBeforeDisplay(data.data.results);
		
	 }
      }
    
    function CampaignsErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Campaigns could not be retrieved');
      }
    
    function getCampaignsBySource(code) {   
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Campaigns.get(account.company, code).then(CampaignsSuccessFn, CampaignsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
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
    
    String.prototype.ucfirst = function() {
    	return this.charAt(0).toUpperCase() + this.substr(1);
    }
    
    $scope.pageChanged = function(newPage) {
    	$scope.currentPage = newPage;
    	getCampaigns(newPage);
    }
    

  }
})();