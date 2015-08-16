/**
* Integrations
* @namespace mmm.integrations.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.integrations.services')
    .factory('Integrations', Integrations);

  Integrations.$inject = ['$http', '$window'];

  /**
  * @namespace Integrations
  * @returns {Factory}
  */
  function Integrations($http, $window) {
	  
	var KEY = '3m.newSystem';
	
    var Integrations = {
      all: all,
      get: get, 
      sfdcAuthorize: sfdcAuthorize,
      oauthGetToken: oauthGetToken,
      superGetIntegrations: superGetIntegrations,
      setNewSystem: setNewSystem,
      getNewSystem: getNewSystem,
      createNewIntegration: createNewIntegration
    };

    return Integrations;

    ////////////////////
    
    
    /**
    * @name all
    * @desc Get all Integrations
    * @returns {Promise}
    * @memberOf mmm.Integrations.services.Integrations
    */
    function all() {
      return $http.get('/api/v1/integrations/');
    }

    /**
     * @name get
     * @desc Get all Integrations
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Integrations.services.Integrations
     */
    function get() {
      return $http.get('/api/v1/integrations/');
    }
    
    /**
     * @name get
     * @desc Get the Integrations of a given user
     * @param {string} username The username to get Integrations for
     * @returns {Promise}
     * @memberOf mmm.Integrations.services.Integrations
     */
    function get(username) { 
      return $http.get('/api/v1/accounts/' + username + '/integrations/');
      //return $http.get('/api/v1/Integrations/');
    }
    
    /**
     * @name sfdcauthorize
     * @desc Get the authoirzation url from SFDC
     * @param {string} 
     * @returns {Promise}
     * @memberOf mmm.Integrations.services.Integrations
     */
    function sfdcAuthorize(username) { 
      return $http.get('/api/v1/accounts/' + username + '/sfdcauthorize/');
    }
    
    function oauthGetToken(source) {
      return $http.get('/api/v1/oauth/' + source + '/');	
    }
    
    function superGetIntegrations() { 
      return $http.get('/api/v1/superadmin/systems/');
    }
    
    function getNewSystem() { 
        var mydata = $window.sessionStorage.getItem(KEY);
        if (mydata) {
        	mydata = JSON.parse(mydata);
        }
        //console.log(mydata);
        return mydata || [];
    }
    
    function setNewSystem(systemx) { 
/*    	var mydata = $window.sessionStorage.getItem(KEY);
    	if (mydata) {
    		mydata = JSON.parse(mydata);
    	}
    	else {
    		mydata = [];
    	}*/
    	var mydata = [];
    	mydata.push(systemx);
        $window.sessionStorage.setItem(KEY, JSON.stringify(mydata));
    }
    
    function createNewIntegration(systemCode) {
    	return $http.get('/api/v1/company/new/' + systemCode + '/');
    }
  }
})();