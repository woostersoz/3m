/**
* Dashboards
* @namespace mmm.dashboards.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.dashboards.services')
    .factory('Dashboards', Dashboards);

  Dashboards.$inject = ['$http'];

  /**
  * @namespace Dashboards
  * @returns {Factory}
  */
  function Dashboards($http) {
    var Dashboards = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      retrieveDashboard: retrieveDashboard,
      getDashboardsByCompany: getDashboardsByCompany,
      calculateDashboards: calculateDashboards,
      drilldownContacts: drilldownContacts,
      drilldownDeals: drilldownDeals,
      getDashboardsByCompany: getDashboardsByCompany
      
    };

    return Dashboards;

    ////////////////////

    /**
    * @name all
    * @desc Get all Dashboards
    * @returns {Promise}
    * @memberOf mmm.Dashboards.services.Dashboards
    */
    function all(company) {
      return $http.get('/api/v1/company/' + company + '/dashboards/');
    }

    /**
     * @name get
     * @desc Get all Dashboards
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Dashboards.services.Dashboards
     */
    function getAll() {
      return $http.get('/api/v1/dashboards/');
    }
    
    /**
     * @name get
     * @desc Get the Dashboards of a given user
     * @param {string} username The username to get Dashboards for
     * @returns {Promise}
     * @memberOf mmm.Dashboards.services.Dashboards
     */
    function get(company, code) {
      return $http.get('/api/v1/company/' + company + '/dashboards/' + code + '/');
      //return $http.get('/api/v1/Dashboards/');
    }
    
    function retrieveDashboard(company, dashboard_name, start_date, end_date, system_type) {
        return $http.get('/api/v1/company/' + company + '/dashboards/retrieve/?dashboard_name=' + dashboard_name + '&start_date=' + start_date + '&end_date=' + end_date  + '&system_type=' + system_type); 
    }
    
    function calculateDashboards(company, chart_name, system_type, chart_title, mode) {
        return $http.get('/api/v1/company/' + company + '/dashboards/calculate/?chart_name=' + chart_name + '&system_type=' + system_type + '&chart_title=' + chart_title + '&mode=' + mode); 
    }
    
    function getDashboardsByCompany(company) {
    	//return $http.get('/api/v1/company/' + company + '/dashboards/charts/');
    }
    
    function drilldownContacts(company, chart_name, object, section, channel, system_type, start_date, end_date, current_page, leads_per_page) {
    	return $http.get('/api/v1/company/' + company + '/dashboards/drilldown/?object=' + object + '&section=' + section + '&channel=' + channel + '&system_type=' + system_type + '&start_date=' + start_date + '&end_date=' + end_date + '&page_number=' + current_page + '&per_page=' + leads_per_page + '&chart_name=' + chart_name); 
    }
    
    function drilldownDeals(company, chart_name, object, section, channel, system_type, start_date, end_date, current_page, leads_per_page) {
    	return $http.get('/api/v1/company/' + company + '/dashboards/drilldown/?object=' + object + '&section=' + section + '&channel=' + channel + '&system_type=' + system_type + '&start_date=' + start_date + '&end_date=' + end_date + '&page_number=' + current_page + '&per_page=' + leads_per_page + '&chart_name=' + chart_name); 
    }
    
    function getDashboardsByCompany(company) {
    	return $http.get('/api/v1/company/' + company + '/dashboards/dashboards/');
    }
    
    
    
  }
})();