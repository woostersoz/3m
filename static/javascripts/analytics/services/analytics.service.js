/**
* Analytics
* @namespace mmm.analytics.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.analytics.services')
    .factory('Analytics', Analytics);

  Analytics.$inject = ['$http'];

  /**
  * @namespace Analytics
  * @returns {Factory}
  */
  function Analytics($http) {
    var Analytics = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      retrieveChart: retrieveChart,
      getChartsByCompany: getChartsByCompany,
      calculateAnalytics: calculateAnalytics,
      getFilterMasterValues: getFilterMasterValues
      
    };

    return Analytics;

    ////////////////////

    /**
    * @name all
    * @desc Get all Analytics
    * @returns {Promise}
    * @memberOf mmm.Analytics.services.Analytics
    */
    function all(company) {
      return $http.get('/api/v1/company/' + company + '/analytics/');
    }

    /**
     * @name get
     * @desc Get all Analytics
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Analytics.services.Analytics
     */
    function getAll() {
      return $http.get('/api/v1/analytics/');
    }
    
    /**
     * @name get
     * @desc Get the Analytics of a given user
     * @param {string} username The username to get Analytics for
     * @returns {Promise}
     * @memberOf mmm.Analytics.services.Analytics
     */
    function get(company, code) {
      return $http.get('/api/v1/company/' + company + '/analytics/' + code + '/');
      //return $http.get('/api/v1/Analytics/');
    }
    
    function retrieveChart(company, chart_name, start_date, end_date, system_type, filters) {
        return $http.get('/api/v1/company/' + company + '/analytics/retrieve/?chart_name=' + chart_name + '&start_date=' + start_date + '&end_date=' + end_date  + '&system_type=' + system_type + '&filters=' + JSON.stringify(filters)); 
    }
    
    function calculateAnalytics(company, chart_name, system_type, chart_title, mode) {
        return $http.get('/api/v1/company/' + company + '/analytics/calculate/?chart_name=' + chart_name + '&system_type=' + system_type + '&chart_title=' + chart_title + '&mode=' + mode); 
    }
    
    function getChartsByCompany(company) {
    	return $http.get('/api/v1/company/' + company + '/analytics/charts/');
    }
    
    function getFilterMasterValues(company, filter_name) {
    	 return $http.get('/api/v1/company/' + company + '/analytics/filters/?filter_name=' + filter_name); 
    }
    
  }
})();