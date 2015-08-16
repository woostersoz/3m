/**
* AccountsController
* @namespace mmm.accounts.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.accounts.controllers', ['datatables'])
    .controller('AccountsController', AccountsController);
  
  AccountsController.$inject = ['$scope', 'Accounts', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$state', '$stateParams', '$document', '$window'];

  /**
  * @namespace AccountsController
  */
  function AccountsController($scope, Accounts, Authentication, $state, $stateParams, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $filter, $document, $window) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.accounts = []; 
    $scope.accounts = [];
    $scope.totalAccounts = 0;
    $scope.accountsPerPage = 10;
    $scope.currentPage = 1;
    $scope.accountName = '';
    $scope.companyName = '';
    $scope.mode = '';
    
    $scope.searchAccountsByName = searchAccountsByName;
    $scope.resetSearchAccountsByName = function() {
    	$scope.accountName = '';
    	$scope.mode = 'all-accounts';
    	getAccounts(1);
    }
    
    $scope.searchCompaniesByName = searchCompaniesByName;
    $scope.resetSearchCompaniesByName = function() {
    	$scope.companyName = '';
    	$scope.mode = 'all-companies';
    	getCompanies(1);
    }
    
    if (!(typeof $stateParams == 'undefined')) {
    	if ($stateParams.system)
    	{
    		$scope.code = $stateParams.code; 
    		getAccountsBySource($scope.code);
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
    
    if (~$state.$$url.indexOf('/companies'))
    {   
    	$scope.mode = 'all-companies';
    	getCompanies(1);
    }
    else if ($state.$$url == '/accounts') {
    	$scope.mode = 'all-accounts';
    	getAccounts(1);
    }
    else if ($state.$$url == '/name') {
    	//Accounts.matchName();
    }
    
    $scope.showingAccount = [];
    for (var i=0, length = vm.accounts.length; i < length; i++) {
    	$scope.showingAccount[vm.accounts[i].id] = false;
    }
    
    $scope.showAccountDetails = function(account) {
    	$scope.showingAccount[account.id] = true;
    }
    
    $scope.hideAccountDetails = function(account) {
    	$scope.showingAccount[account.id] = false;
    }
    
    $scope.showingCompany = [];
    for (var i=0, length = vm.accounts.length; i < length; i++) {
    	$scope.showingCompany[vm.accounts[i]._id] = false;
    }
    
    $scope.showCompanyDetails = function(account) {
    	$scope.showingCompany[account._id] = true;
    }
    
    $scope.hideCompanyDetails = function(account) {
    	$scope.showingCompany[account._id] = false;
    }
    
/*    $scope.$state = $state;
    $scope.scopeName = $state.current.name*/
    



    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.AccountsController
    */
    function activate() {   
    	//getCompanies(1);
    	$scope.pagination = { current: 1 };
    	
    }
    
    function getCompanies(pageNumber)
    {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Accounts.allCompanies(account.company, pageNumber, $scope.accountsPerPage).then(CompaniesSuccessFn, CompaniesErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
   
    function CompaniesSuccessFn(data, status, headers, config) { 
	 if (data.data.results) 
	 {  
		$scope.totalAccounts = data.data.count;
 		$scope.thisSetCount = data.data.results.length;
		// initialize the start and end counts shown near pagination control
		$scope.startAccountCounter = ($scope.currentPage - 1) * $scope.accountsPerPage + 1;
		$scope.endAccountCounter = ($scope.thisSetCount < $scope.accountsPerPage) ? $scope.startAccountCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.accountsPerPage;
		
		//vm.accounts = Accounts.cleanAccountsBeforeDisplay(data.data.results);
		vm.accounts = data.data.results;
		
	 }
      }
    
    function CompaniesErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Companies could not be retrieved');
      }
    
    function getAccounts(pageNumber)
    {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Accounts.allAccounts(account.company, pageNumber, $scope.accountsPerPage).then(AccountsSuccessFn, AccountsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
   
    function AccountsSuccessFn(data, status, headers, config) { 
	 if (data.data.results) 
	 {  
		$scope.totalAccounts = data.data.count;
 		$scope.thisSetCount = data.data.results.length;
		// initialize the start and end counts shown near pagination control
		$scope.startAccountCounter = ($scope.currentPage - 1) * $scope.accountsPerPage + 1;
		$scope.endAccountCounter = ($scope.thisSetCount < $scope.accountsPerPage) ? $scope.startAccountCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.accountsPerPage;
		
		//vm.accounts = Accounts.cleanAccountsBeforeDisplay(data.data.results);
		vm.accounts = data.data.results;
		
	 }
      }
    
    function AccountsErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Accounts could not be retrieved');
      }
    
    function getAccountsBySource(code) {   
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Accounts.get(account.company, code).then(AccountsSuccessFn, AccountsErrorFn);
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
    	if ($scope.mode == 'all-companies')
    	   getCompanies(newPage);
    	else if ($scope.mode == 'all-accounts')
    	   getAccounts(newPage);
    	else if ($scope.mode == 'search-companies')
    		searchCompaniesByName();
    	else if ($scope.mode == 'search-accounts')
    		searchAccountsByName();
    	
    }
    
    function searchAccountsByName() {
    	var trimmedAccountName = $scope.accountName.trim();
    	if (trimmedAccountName.length ==  0)
    	{   
    		$scope.mode = 'all-accounts';
    		getAccounts(1);
    	}
    	else if (trimmedAccountName.length < 3) {
    		toastr.error('Please enter at least 3 letters to search');
    		return false;
    	}
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) {
	    	$scope.mode = 'search-accounts';
	    	Accounts.matchAccountName(account.company, trimmedAccountName, $scope.currentPage, $scope.accountsPerPage).then(AccountsSuccessFn, AccountsErrorFn);
	    }
    }
    
    function searchCompaniesByName() {
    	var trimmedCompanyName = $scope.companyName.trim();
    	if (trimmedCompanyName.length ==  0)
    	{
    		$scope.mode = 'all-companies';
    		getCompanies(1);
    	}
    	else if (trimmedCompanyName.length < 3) {
    		toastr.error('Please enter at least 3 letters to search');
    		return false;
    	}
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) {
	    	$scope.mode = 'search-companies';
	    	Accounts.matchCompanyName(account.company, trimmedCompanyName, $scope.currentPage, $scope.accountsPerPage).then(CompaniesSuccessFn, CompaniesErrorFn);
	    }
    }
    
    function searchAccountsSuccessFn(data, status, headers, config) {
        toastr.error('Accounts could not be retrieved');
    }
    
    function searchAccountsErrorFn(data, status, headers, config) {
        toastr.error('Accounts could not be retrieved');
    }

  }
})();