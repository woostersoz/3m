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
      authorize: authorize,
      oauthGetToken: oauthGetToken,
      superGetNewIntegrations: superGetNewIntegrations,
      superGetExistingIntegrations: superGetExistingIntegrations,
      setNewSystem: setNewSystem,
      getNewSystem: getNewSystem,
      createNewIntegration: createNewIntegration,
      postFormData: postFormData,
      deleteSystem: deleteSystem,
      editSystem: editSystem,
      retrieveCampaignsFromSource: retrieveCampaignsFromSource,
      retrieveCampaignsFromSourceDaily: retrieveCampaignsFromSourceDaily,
      retrieveLeadsFromSource: retrieveLeadsFromSource,
      retrieveLeadsFromSourceDaily: retrieveLeadsFromSourceDaily,
      retrieveContactsFromSource: retrieveContactsFromSource,
      retrieveContactsFromSourceDaily: retrieveContactsFromSourceDaily,
      retrieveActivitiesFromSource: retrieveActivitiesFromSource,
      retrieveActivitiesFromSourceDaily: retrieveActivitiesFromSourceDaily,
      retrieveOpportunitiesFromSource: retrieveOpportunitiesFromSource,
      retrieveOpportunitiesFromSourceDaily: retrieveOpportunitiesFromSourceDaily,
      getMetaData: getMetaData,
      getLeadStatuses: getLeadStatuses,
      googTest: googTest, 
      fbokTest: fbokTest,
      retrieveLeadStatusMapping: retrieveLeadStatusMapping,
      saveLeadStatusMapping: saveLeadStatusMapping
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
    function authorize(company, companyInfo) { 
      var urlString = "?" + Object.keys(companyInfo).map(function(prop) {
    	  return [prop, companyInfo[prop]].map(encodeURIComponent).join("=");
      }).join("&");
      return $http.get('/api/v1/company/' + company + '/integration/authorize/' + urlString);
    }
    
    function oauthGetToken(source, code, state, company, refresh_token) {
      return $http.get('/api/v1/oauth/' + source + '/?code=' + code + '&state=' + state + '&company=' + company  + '&refresh_token=' + refresh_token);	
    }
    
    function superGetNewIntegrations() { 
      return $http.get('/api/v1/company/integrations/new/');
    }
    
    function superGetExistingIntegrations() { 
        return $http.get('/api/v1/company/integrations/existing/');
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
    	return $http.get('/api/v1/company/form/' + systemCode + '/');
    }
    
    function postFormData(content, systemCode) {
    	return $http.post('/api/v1/company/form/'  + systemCode + '/', content);
    }
    
    function deleteSystem(system) {
        var record_id = JSON.parse(system.company_info.record_id).$oid; 
	    return $http.delete('/api/v1/company/integration/' + record_id + '/' + system.code + '/'); //+ system.company_info.access_token + '/'
	}
    
    function editSystem(system) {
        var record_id = JSON.parse(system.company_info.record_id).$oid; 
	    return $http.get('/api/v1/company/integration/' + record_id + '/' + system.code + '/'); //+ system.company_info.access_token + '/'
	}   
    
    function retrieveCampaignsFromSource(company, code) {
        return $http.get('/api/v1/company/' + company + '/campaigns/retrieve/?code=' + code); //company/' + company + '/campaigns/
    }
    
    function retrieveCampaignsFromSourceDaily(company, code) {
        return $http.get('/api/v1/company/' + company + '/campaigns/retrieve/daily/?code=' + code); //company/' + company + '/campaigns/
    }
    
    function retrieveLeadsFromSource(company, code) {
        return $http.get('/api/v1/company/' + company + '/leads/retrieve/?code=' + code); 
    }
    
    function retrieveLeadsFromSourceDaily(company, code) {
        return $http.get('/api/v1/company/' + company + '/leads/retrieve/daily/?code=' + code); 
    }
    
    function retrieveContactsFromSource(company, code) {
        return $http.get('/api/v1/company/' + company + '/contacts/retrieve/?code=' + code); 
    }
    
    function retrieveContactsFromSourceDaily(company, code) {
        return $http.get('/api/v1/company/' + company + '/contacts/retrieve/daily/?code=' + code); 
    }
    
    function retrieveActivitiesFromSource(company, code) {
        return $http.get('/api/v1/company/' + company + '/activities/retrieve/?code=' + code); 
    }
    
    function retrieveActivitiesFromSourceDaily(company, code) {
        return $http.get('/api/v1/company/' + company + '/activities/retrieve/daily/?code=' + code); 
    }
    
    function retrieveOpportunitiesFromSource(company, code) {
        return $http.get('/api/v1/company/' + company + '/opportunities/retrieve/?code=' + code); 
    }
    
    function retrieveOpportunitiesFromSourceDaily(company, code) {
        return $http.get('/api/v1/company/' + company + '/opportunities/retrieve/daily/?code=' + code); 
    }
    
    function getMetaData(company, code, object) {
        return $http.get('/api/v1/company/' + company + '/integrations/metadata/?code=' + code + '&object=' + object); 
    }
    
    function getLeadStatuses(company) {
        return $http.get('/api/v1/company/' + company + '/integrations/metadata/lead/statuses/'); 
    }
    
    function googTest(company) {
        return $http.get('/api/v1/oauth/goog-test/?company=' + company);	
      }
    
    function fbokTest(company) {
        return $http.get('/api/v1/oauth/fbok-test/?company=' + company);	
      }
    
    function retrieveLeadStatusMapping(company) {
        return $http.get('/api/v1/company/' + company + '/integrations/leadstatus/'); //company/' + company + '/campaigns/
    }
    
    function saveLeadStatusMapping(company, mapping) {
    	return $http.post('/api/v1/company/' + company + '/integrations/leadstatus/', {'mapping' : mapping}); //company/' + company + '/campaigns/
    }
  }
})();