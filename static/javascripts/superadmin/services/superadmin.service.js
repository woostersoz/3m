/**
* Superadmin
* @namespace mmm.superadmin.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.superadmin.services')
    .factory('Superadmin', Superadmin);

  Superadmin.$inject = ['$http'];

  /**
  * @namespace Superadmin
  * @returns {Factory}
  */
  function Superadmin($http) {
    var Superadmin = {
      mongonaut: mongonaut,
      getJobs: getJobs
      
    };

    return Superadmin;

    ////////////////////

  
    function mongonaut(userid, fullUrl) {
    	/*if (~fullUrl.indexOf('/edit') || ~fullUrl.indexOf('/add') || ~fullUrl.indexOf('/delete'))
    		return $http.post(fullUrl);
    	else*/
            return $http.get(fullUrl);
    }
    
    function getJobs(company, pageNumber, perPage) {
    	return $http.get('/api/v1/company/' + company + '/superadmin/jobs/?page_number=' + pageNumber + '&per_page=' + perPage);
    }
   
    
  }
})();