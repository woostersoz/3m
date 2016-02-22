/**
* Views
* @namespace mmm.views.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.views.services')
    .factory('Views', Views);

  Views.$inject = ['$http'];

  /**
  * @namespace Views
  * @returns {Factory}
  */
  function Views($http) {
    var Views = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      retrieveView: retrieveView,
      getViewsByCompany: getViewsByCompany, 
      calculateViews: calculateViews,
      getFilterMasterValues: getFilterMasterValues,
      getSuperFilters: getSuperFilters
      
    };

    return Views;

    ////////////////////

    /**
    * @name all
    * @desc Get all Views
    * @returns {Promise}
    * @memberOf mmm.Views.services.Views
    */
    function all(company) {
      return $http.get('/api/v1/company/' + company + '/views/');
    }

    /**
     * @name get
     * @desc Get all Views
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Views.services.Views
     */
    function getAll() {
      return $http.get('/api/v1/views/');
    }
    
    /**
     * @name get
     * @desc Get the Views of a given user
     * @param {string} username The username to get Views for
     * @returns {Promise}
     * @memberOf mmm.Views.services.Views
     */
    function get(company, code) {
      return $http.get('/api/v1/company/' + company + '/views/' + code + '/');
      //return $http.get('/api/v1/Views/');
    }
    
    function retrieveView(company, view_name, start_date, end_date, system_type, pageNumber, perPage, filters, superFilters, subview) {
        return $http.get('/api/v1/company/' + company + '/views/retrieve/?view_name=' + view_name + '&start_date=' + start_date + '&end_date=' + end_date  + '&system_type=' + system_type + '&page_number=' + pageNumber + '&per_page=' + perPage + '&filters=' + JSON.stringify(filters) + '&superfilters=' + JSON.stringify(superFilters) + '&subview=' + subview); 
    }
    
    function calculateViews(company, chart_name, system_type, chart_title, mode) {
        return $http.get('/api/v1/company/' + company + '/views/calculate/?chart_name=' + chart_name + '&system_type=' + system_type + '&chart_title=' + chart_title + '&mode=' + mode); 
    }
    
    function getViewsByCompany(company) {
    	return $http.get('/api/v1/company/' + company + '/views/views/');
    }
    
    function getFilterMasterValues(company, filter_name) {
    	 return $http.get('/api/v1/company/' + company + '/views/filters/?filter_name=' + filter_name); 
    }
    
    function getSuperFilters(company, object_type, system_type) {
    	return $http.get('/api/v1/company/' + company + '/views/superfilters/?object_type=' + object_type + '&system_type=' + system_type); 
    }
  }
})();