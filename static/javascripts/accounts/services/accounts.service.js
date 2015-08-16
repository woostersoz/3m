/**
* Accounts
* @namespace mmm.accounts.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.accounts.services')
    .factory('Accounts', Accounts);

  Accounts.$inject = ['$http'];

  /**
  * @namespace Accounts
  * @returns {Factory}
  */
  function Accounts($http) {
    var Accounts = {
      allCompanies: allCompanies,
      //create: create,
      get: get,
      getAll: getAll,
      allAccounts: allAccounts,
      matchAccountName: matchAccountName,
      matchCompanyName:matchCompanyName,
      cleanAccountsBeforeDisplay: cleanAccountsBeforeDisplay
      
    };

    return Accounts;

    ////////////////////

    /**
    * @name all
    * @desc Get all Accounts
    * @returns {Promise}
    * @memberOf mmm.Accounts.services.Accounts
    */
    function allCompanies(company, pageNumber, perPage) {
      return $http.get('/api/v1/company/' + company + '/accounts/companies/?page_number=' + pageNumber + '&per_page=' + perPage);
    }

    function allAccounts(company, pageNumber, perPage) {
        return $http.get('/api/v1/company/' + company + '/accounts/?page_number=' + pageNumber + '&per_page=' + perPage);
      }

    /**
     * @name get
     * @desc Get all Accounts
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Accounts.services.Accounts
     */
    function getAll() {
      return $http.get('/api/v1/companies/');
    }
    
    /**
     * @name get
     * @desc Get the Accounts of a given user
     * @param {string} username The username to get Accounts for
     * @returns {Promise}
     * @memberOf mmm.Accounts.services.Accounts
     */
    function get(company, code) {
        return $http.get('/api/v1/company/' + company + '/accounts/' + code + '/');
      //return $http.get('/api/v1/Accounts/');
    }
    
    function cleanAccountsBeforeDisplay(results) {
    	var currRecord = '';
    	var accounts = [];
		for (var i=0; i < results.length; i++)
	    {
		    currRecord = results[i].accounts;
		    if (currRecord['mkto'])
		    {
		    	for (var key in currRecord['mkto']) // convert first letter to lower case
		    	{
		    		currRecord['mkto'][key.ucfirst()] = currRecord['mkto'][key];	
		    	}
		    	currRecord['mkto']['CreatedDate'] = currRecord['mkto']['CreatedAt']
		    	currRecord['mkto']['sourceSystem'] = 'MKTO';
		    	accounts.push(currRecord['mkto']);
		    }	
		    else if (currRecord['sfdc'])
		    {
		    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
		    	accounts.push(currRecord['sfdc']);
		    }
		    else
		    	toastr.error('Something fishy going on!');
	    	
	    }
		return accounts;
    }
    
    function matchAccountName(company, name, pageNumber, perPage) {
        return $http.get('/api/v1/company/' + company + '/accounts/account-match/' + name + '/?page_number=' + pageNumber + '&per_page=' + perPage);
    }
    
    function matchCompanyName(company, name, pageNumber, perPage) {
        return $http.get('/api/v1/company/' + company + '/accounts/company-match/' + name + '/?page_number=' + pageNumber + '&per_page=' + perPage);
    }
    
  }
})();