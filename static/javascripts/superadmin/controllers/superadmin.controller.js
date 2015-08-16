/**
* SuperadminController
* @namespace mmm.superadmin.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.superadmin.controllers', ['datatables'])
    .controller('SuperadminController', SuperadminController);
  
  SuperadminController.$inject = ['$scope', 'Superadmin', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$state', '$stateParams', '$document', '$window', '$compile', 'Company', '$modal', 'Common'];

  /**
  * @namespace SuperadminController
  */
  function SuperadminController($scope, Superadmin, Authentication, $state, $stateParams, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $filter, $document, $window, $compile, Company, $modal, Common) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.superadmin = []; 
    $scope.superadmin = [];
    $scope.totalSuperadmin = 0;
    $scope.superadminPerPage = 10;
    $scope.totalLogs = 0;
    $scope.logsPerPage = 10;
    $scope.currentPage = 1;
    vm.companies = [];
    vm.jobs = [];
    $scope.confirm_retrieve_all_data = confirm_retrieve_all_data;
    
    $scope.showingJob = [];
    for (var i=0, length = vm.jobs.length; i < length; i++) {
    	$scope.showingJob[vm.jobs[i].id] = false;
    }
    
    $scope.showJob = function(job) {
    	$scope.showingJob[job.id] = true;
    }
    
    $scope.hideJob = function(job) {
    	$scope.showingJob[job.id] = false;
    }
    
    $scope.opts = {
			/*ranges : {
				'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
				'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
				'This Month' : [ moment().startOf("month"),
				                 moment().endOf("day") ]
			},*/
			singleDatePicker: true,
			showDropdowns: true
	};
    
    $scope.groupDates = {};
	$scope.groupDates.date = {
			//startDate : moment().subtract(6, "days").startOf("day"),
			//startDate : moment().endOf("day"),
			//endDate : moment().endOf("day")
			startDate: null,
			endDate: null
	};

	
	//$scope.startDate = $scope.groupDates.date.startDate;
	//$scope.endDate = $scope.groupDates.date.endDate;
	
	$scope.$watch('groupDates.date', function(newDate, oldDate) { 
		if (!newDate || !oldDate) return;
		var startDate = 0;
		if ((newDate.startDate) && (newDate != oldDate)) {
			startDate = moment(newDate.startDate).startOf('day');
			$scope.startDate = startDate;
			//toastr.success($scope.startDate.unix());
		}
	});
    
    if (~$state.$$url.indexOf('/mongonaut'))
    {   
    	if ($state.$$url == '/mongonaut')
    		$state.$$url = '/mongonaut/';
    	mongonaut($state.$$url);
    }
    else if ($state.$$url == '/superadmin-jobs') {
    	startSuperadminData();
    }
    else if ($state.$$url == '/superadmin-logs') {
    	startSuperadminJobs(1);
    	$scope.pagination = { current: 1 };
    }
    	
    


    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.SuperadminController
    */
    function activate() {   
    	getSuperadmin(1);
    	$scope.pagination = { current: 1 };
    	
    }
    
    function startSuperadminData() {
    	var account = Authentication.getAuthenticatedAccount();
    	if (account.is_superadmin) {
    		Company.getCompanies().then(CompaniesSuccessFn, CompaniesErrorFn);
    	}
    	else {
    		window.location = "/";
    		toastr.error("You are not authorized to view this page");
    	}
    }
    
    function CompaniesSuccessFn(data, status, headers, config) { 
    	if (data.data) {
    		vm.companies = data.data;
    	}
    	else {
    		toastr.error('Could not retrieve companies');
    	}
    }
    
    function CompaniesErrorFn(data, status, headers, config) { 
    	toastr.error('Could not retrieve companies');
    }
    
    function mongonaut(fullUrl) {
    	var account = Authentication.getAuthenticatedAccount();
    	if (account.is_superadmin)
    		{
    		   Superadmin.mongonaut(account.id, fullUrl).then(MongonautSuccessFn, MongonautErrorFn);
    		   //window.location = '/mongonaut/'
    		}
    	else {
    		window.location = "/";
    		toastr.error("You are not authorized to view this page");
    	}
    }
    
    function MongonautSuccessFn(data, status, headers, config) { 
    	var scope = angular.element('#mongonaut-div').scope();
    	$scope.templateHtml = data.data;
		$scope.htmlString = "changed";
		scope.$apply;
    }
    
    function MongonautErrorFn(data, status, headers, config) { 
    	
    }
    
    function getSuperadmin(pageNumber)
    {
    	var superadmin = Authentication.getAuthenticatedAccount();
	    if (superadmin) 
	    	Superadmin.all(superadmin.company, pageNumber, $scope.superadminPerPage).then(SuperadminSuccessFn, SuperadminErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
   
    function SuperadminSuccessFn(data, status, headers, config) { 
	 if (data.data.results) // they could contain both Mkto and SFDC leads
	 {  
		$scope.totalSuperadmin = data.data.count;
 		$scope.thisSetCount = data.data.results.length;
		// initialize the start and end counts shown near pagination control
		$scope.startSuperadminCounter = ($scope.currentPage - 1) * $scope.superadminPerPage + 1;
		$scope.endSuperadminCounter = ($scope.thisSetCount < $scope.superadminPerPage) ? $scope.startSuperadminCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.superadminPerPage;
		
		//vm.superadmin = Superadmin.cleanSuperadminBeforeDisplay(data.data.results);
		vm.superadmin = data.data.results;
		
	 }
      }
    
    function SuperadminErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Superadmin could not be retrieved');
      }
    
    function getSuperadminBySource(code) {   
    	var superadmin = Authentication.getAuthenticatedAccount();
	    if (superadmin) 
	    	Superadmin.get(superadmin.company, code).then(SuperadminSuccessFn, SuperadminErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    function confirm_retrieve_all_data() {
    	var company = Common.findByAttr(vm.companies, 'id', $scope.company.id);
    	$scope.company.name = company['name'];
    	$scope.company.company_id = company['company_id'];
    	Company.getCompanyIntegration($scope.company.company_id).then(getCompanyIntegrationSuccess, getCompanyIntegrationError);
    	
    }
    
    function getCompanyIntegrationSuccess(data, status, headers, config) { 
    	//toastr.info();
    	if (data.data) {
    		$scope.companyIntegration = data.data;
    		if ($scope.companyIntegration == null) {
    			toastr.error('Something went wrong!');
    			return false;
    		}
    		else if ($scope.companyIntegration['initial_run_in_process']) {
    				toastr.error('Initial data extract still in process for this company');
    				return false;
    			}
    		else { // go ahead with reconfirming
    			var modalInstance = $modal
    			.open({
    				templateUrl : 'confirmation.html',
    				controller : modalController,
    				scope : $scope,
    				resolve : {
    					
    					
    				}
    			});
    	    	 modalInstance.result.then(function() {
    	    	    	Company.startCompanyInitialRun($scope.company.company_id, $scope.startDate).then(startCompanyInitialRunSuccess, startCompanyInitialRunError);
    	    	    }, function () { 
    	    	    	
    	    	 });
    		}
    	}
    }
    
    function getCompanyIntegrationError(data, status, headers, config) { 
    	
    }
    
    function startCompanyInitialRunSuccess(data, status, headers, config) { 
    	
    }

    function startCompanyInitialRunError(data, status, headers, config) { 
    	
    }
   
  
  var modalController = function($scope, $modalInstance) {

		
		$scope.ok = function() {
			
				$modalInstance.close();
		};
		$scope.cancel = function() {
			$modalInstance.dismiss('cancel');
		};
	}
    
   
    
    function startSuperadminJobs(pageNumber) {
    	var account = Authentication.getAuthenticatedAccount();
    	if (account.is_superadmin) {
    		Superadmin.getJobs(account.company, pageNumber, $scope.logsPerPage).then(JobsSuccessFn, JobsErrorFn);
    	}
    	else {
    		window.location = "/";
    		toastr.error("You are not authorized to view this page");
    	}
    }
    
    function JobsSuccessFn(data, status, headers, config) { 
    	if (data.data) {
    		vm.jobs = data.data.results;
    		$scope.totalLogs = data.data.totalCount;
     		$scope.thisSetCount = data.data.results.length;
    		// initialize the start and end counts shown near pagination control
    		$scope.startJobCounter = ($scope.currentPage - 1) * $scope.logsPerPage + 1;
    		$scope.endJobCounter = ($scope.thisSetCount < $scope.logsPerPage) ? $scope.startJobCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.logsPerPage;
    		
    		$scope.numberJobs = $scope.totalLogs;
    		$scope.numberJobsInitial = data.data.initialCount;
    		$scope.numberJobsDelta = data.data.deltaCount;
    		$scope.numberJobsSuccess = data.data.totalCountSuccess;
    		$scope.numberJobsFailure = data.data.totalCountFailure;
    		$scope.numberInitialJobsSuccess = data.data.initialCountSuccess;
    		$scope.numberInitialJobsFailure = data.data.totalCountFailure;
    		$scope.numberDeltaJobsSuccess = data.data.deltaCountSuccess;
    		$scope.numberDeltaJobsFailure = data.data.deltaCountFailure;
    		
    	}
    	else {
    		toastr.error('Could not retrieve jobs');
    	}
    }
    
    function JobsErrorFn(data, status, headers, config) { 
    	if (data.data)
    		toastr.error(data.data);
    	else
    	    toastr.error('Could not retrieve jobs');
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
    	if ($state.$$url == '/superadmin-jobs') 
    	   getSuperadmin(newPage);
    	else if ($state.$$url == '/superadmin-logs') 
    	startSuperadminJobs(newPage);
    }
    
    
    

  }
})();