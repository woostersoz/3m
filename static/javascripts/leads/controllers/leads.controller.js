/**
* LeadsController
* @namespace mmm.leads.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.leads.controllers', ['datatables'])
    .controller('LeadsController', LeadsController);
  
  LeadsController.$inject = ['$scope', 'Leads', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$document', '$window', 'Common', '$state', '$stateParams'];

  /**
  * @namespace LeadsController
  */
  function LeadsController($scope, Leads, Authentication, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances,  $filter, $document, $window, Common, $state, $stateParams) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.leads = []; 
    $scope.leads = [];
    $scope.totalLeads = 0;
    $scope.leadsPerPage = 10;
    $scope.currentPage = 1;
    $scope.leads_with_company = 0;
    $scope.leads_without_company = 0;
    $scope.stages = [];
    $scope.sources = [];
    
/*    DTInstances.getLast().then(function (dtInstance) {
        vm.dtInstance = dtInstance;
    });*/
    
/*    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withPaginationType('full')
       .withOption('rowCallback', rowCallback)
       .withOption('order', [3, 'desc']);
*/
    $scope.showingContact = [];
    for (var i=0, length = vm.leads.length; i < length; i++) {
    	$scope.showingContact[vm.leads[i].id] = false;
    }
    
    $scope.showContactDetails = function(lead) {
    	$scope.showingContact[lead.id] = true;
    }
    
    $scope.hideContactDetails = function(lead) {
    	$scope.showingContact[lead.id] = false;
    }
    
    if ($scope.showLeads === false)
    	return false;
    
    if (!(typeof $stateParams == 'undefined')) {
    	if ($stateParams.system)
    	{
    		$scope.code = $stateParams.code; 
    		getLeadsBySource($scope.code);
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
    * @memberOf mmm.symbols.controllers.LeadsController
    */
    function activate() {   
    	getLeads(1);
    	$scope.pagination = { current: 1 };
    }
    
    function getLeads(pageNumber) {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Leads.all(account.company, pageNumber, $scope.leadsPerPage).then(LeadsSuccessFn, LeadsErrorFn);
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
    
    function LeadsSuccessFn(data, status, headers, config) { 
    	 if (data.data.results) // they could contain  Mkto, SFDC or HSPT leads
    	 {  
    		$scope.totalLeads = data.data.count;
    		$scope.thisSetCount = data.data.results.length;
    		$scope.leads_with_company = data.data.total_with_company;
    		$scope.leads_without_company = data.data.total_without_company;
    		var stages = data.data.stages;
    		$scope.stages = [];
    		for (var key in stages) {
    			if (stages.hasOwnProperty(key)) {
    				$scope.stages.push(Common.capitalizeFirstLetter(key) + ' - ' + stages[key]);
    			}
    		}
    		var sources = data.data.sources;
    		$scope.sources = [];
    		for (var key in sources) {
    			if (sources.hasOwnProperty(key)) {
    				$scope.sources.push(Common.capitalizeFirstLetter(key) + ' - ' + sources[key]);
    			}
    		}
			// initialize the start and end counts shown near pagination control
			$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
		    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
			
    		vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results);
    	 }
      }
    
    function LeadsErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Contacts could not be retrieved');
      }
    

    function getLeadsBySource(code) {   
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Leads.get(account.company, code).then(LeadsSuccessFn, LeadsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    $scope.pageChanged = function(newPage) {
    	$scope.currentPage = newPage;
    	getLeads(newPage);
    }
    
    

  }
})();