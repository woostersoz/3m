/**
* Campaigns
* @namespace mmm.campaigns.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.campaigns.services')
    .factory('Campaigns', Campaigns);

  Campaigns.$inject = ['$http'];

  /**
  * @namespace Campaigns
  * @returns {Factory}
  */
  function Campaigns($http) {
    var Campaigns = {
      all: all,
      create: create,
      get: get
    };

    return Campaigns;

    ////////////////////

    /**
    * @name all
    * @desc Get all Campaigns
    * @returns {Promise}
    * @memberOf mmm.Campaigns.services.Campaigns
    */
    function all() {
      return $http.get('/api/v1/campaigns/');
    }


    /**
    * @name create
    * @desc Create a new backtest
    * @param {string} content The content of the new backtest
    * @returns {Promise}
    * @memberOf mmm.Campaigns.services.Campaigns
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
     * @desc Get all Campaigns
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Campaigns.services.Campaigns
     */
    function get() {
      return $http.get('/api/v1/campaigns/');
    }
    
    /**
     * @name get
     * @desc Get the Campaigns of a given user
     * @param {string} username The username to get Campaigns for
     * @returns {Promise}
     * @memberOf mmm.Campaigns.services.Campaigns
     */
    function get(username) { 
      return $http.get('/api/v1/accounts/' + username + '/campaigns/');
      //return $http.get('/api/v1/Campaigns/');
    }
  }
})();