/**
* Leads
* @namespace mmm.leads.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.leads.services')
    .factory('Leads', Leads);

  Leads.$inject = ['$http'];

  /**
  * @namespace Leads
  * @returns {Factory}
  */
  function Leads($http) {
    var Leads = {
      all: all,
      create: create,
      get: get
    };

    return Leads;

    ////////////////////

    /**
    * @name all
    * @desc Get all Leads
    * @returns {Promise}
    * @memberOf mmm.Leads.services.Leads
    */
    function all() {
      return $http.get('/api/v1/leads/');
    }


    /**
    * @name create
    * @desc Create a new backtest
    * @param {string} content The content of the new backtest
    * @returns {Promise}
    * @memberOf mmm.Leads.services.Leads
    */
    function create(name, csv_dir, symbol_list, initial_capital,
            start_date, periods, heartbeat,
            header_format, max_iters) { //alert(symbol_list);
      return $http.post('/api/v1/backtest/', {
    	  name : name,
    	  csv_dir : csv_dir,
          symbol_list : symbol_list,
          initial_capital : initial_capital,
          //start_date : start_date,
          periods : periods,
          heartbeat : heartbeat,
          header_format : header_format,
          //max_iters : max_iters,
        
      });
    }

    /**
     * @name get
     * @desc Get all Leads
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Leads.services.Leads
     */
    function get() {
      return $http.get('/api/v1/leads/');
    }
    
    /**
     * @name get
     * @desc Get the Leads of a given user
     * @param {string} username The username to get Leads for
     * @returns {Promise}
     * @memberOf mmm.Leads.services.Leads
     */
    function get(username) { 
      return $http.get('/api/v1/accounts/' + username + '/leads/');
      //return $http.get('/api/v1/Leads/');
    }
  }
})();