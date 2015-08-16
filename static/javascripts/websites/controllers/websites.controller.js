/**
* WebsitesController
* @namespace mmm.websites.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.websites.controllers', ['datatables'])
    .controller('WebsitesController', WebsitesController);
  
  WebsitesController.$inject = ['$scope', 'Websites', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$document', '$window', 'Common', '$state', '$stateParams'];

  /**
  * @namespace WebsitesController
  */
  function WebsitesController($scope, Websites, Authentication, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances,  $filter, $document, $window, Common, $state, $stateParams) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.websites = []; 
    $scope.websites = [];
    $scope.totalWebsites = 0;
    $scope.websitesPerPage = 10;
    $scope.currentPage = 1;
    $scope.websites_with_company = 0;
    $scope.websites_without_company = 0;
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
    for (var i=0, length = vm.websites.length; i < length; i++) {
    	$scope.showingContact[vm.websites[i].id] = false;
    }
    
    $scope.showContactDetails = function(website) {
    	$scope.showingContact[website.id] = true;
    }
    
    $scope.hideContactDetails = function(website) {
    	$scope.showingContact[website.id] = false;
    }
    
    if ($scope.showWebsites === false)
    	return false;
    
    if (!(typeof $stateParams == 'undefined')) {
    	if ($stateParams.system)
    	{
    		$scope.code = $stateParams.code; 
    		getWebsitesBySource($scope.code);
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
    * @memberOf mmm.symbols.controllers.WebsitesController
    */
    function activate() {   
    	getWebsites(1);
    	$scope.pagination = { current: 1 };
    }
    
    function getWebsites(pageNumber) {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Websites.all(account.company, pageNumber, $scope.websitesPerPage).then(WebsitesSuccessFn, WebsitesErrorFn);
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
    
    function WebsitesSuccessFn(data, status, headers, config) { 
    	 if (data.data.results) // they could contain  Mkto, SFDC or HSPT websites
    	 {  
    		$scope.totalWebsites = data.data.count;
    		$scope.thisSetCount = data.data.results.length;
    		$scope.websites_with_company = data.data.total_with_company;
    		$scope.websites_without_company = data.data.total_without_company;
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
			$scope.startWebsiteCounter = ($scope.currentPage - 1) * $scope.websitesPerPage + 1;
		    $scope.endWebsiteCounter = ($scope.thisSetCount < $scope.websitesPerPage) ? $scope.startWebsiteCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.websitesPerPage;
			
    		vm.websites = Websites.cleanWebsitesBeforeDisplay(data.data.results);
    	 }
      }
    
    function WebsitesErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Websites could not be retrieved');
      }
    

    function getWebsitesBySource(code) {   
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Websites.get(account.company, code).then(WebsitesSuccessFn, WebsitesErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    $scope.pageChanged = function(newPage) {
    	$scope.currentPage = newPage;
    	getWebsites(newPage);
    }
    
    

  }
})();