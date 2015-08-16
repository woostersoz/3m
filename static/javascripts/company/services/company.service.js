/**
* Company
* @namespace mmm.company.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.company.services')
    .factory('Company', Company);

  Company.$inject = ['$http', '$window'];

  /**
  * @namespace Company
  * @returns {Factory}
  */
  function Company($http, $window) {
	  
	var KEY = '3m.newSystem';
	
    var Company = {
      getLeadCount: getLeadCount,
      getCampaignCount: getCampaignCount,
      getCompanies: getCompanies,
      getCompany: getCompany,
      getCompanyIntegration: getCompanyIntegration, 
      startCompanyInitialRun: startCompanyInitialRun
    };

    return Company;

    ////////////////////
    
   
    function getLeadCount(company) {
        return $http.get('/api/v1/company/' + company + '/count/?object=lead'); //company/' + company + '/campaigns/
    }
    
    function getCampaignCount(company, code) {
        return $http.get('/api/v1/company/' + company + '/count/?object=campaign'); 
    }
    
    function getCompanies() {
    	return $http.get('/api/v1/company/companies/');
    }
    
    function getCompany(company) {
    	return $http.get('/api/v1/company/' + company + '/');
    }
    
    function getCompanyIntegration(company) {
    	return $http.get('/api/v1/company/' + company + '/integration/');
    }
    
    function startCompanyInitialRun(company, startDate) {
    	return $http.get('/api/v1/company/' + company + '/data/initial/?start_date=' + startDate);
    }
    
  }
})();