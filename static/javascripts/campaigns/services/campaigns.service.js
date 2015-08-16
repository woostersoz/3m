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
      //create: create,
      get: get,
      getAll: getAll,
      cleanCampaignsBeforeDisplay: cleanCampaignsBeforeDisplay
      
    };

    return Campaigns;

    ////////////////////

    /**
    * @name all
    * @desc Get all Campaigns
    * @returns {Promise}
    * @memberOf mmm.Campaigns.services.Campaigns
    */
    function all(company, pageNumber, perPage) {
      return $http.get('/api/v1/company/' + company + '/campaigns/?page_number=' + pageNumber + '&per_page=' + perPage);
    }


    /**
     * @name get
     * @desc Get all Campaigns
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Campaigns.services.Campaigns
     */
    function getAll() {
      return $http.get('/api/v1/campaigns/');
    }
    
    /**
     * @name get
     * @desc Get the Campaigns of a given user
     * @param {string} username The username to get Campaigns for
     * @returns {Promise}
     * @memberOf mmm.Campaigns.services.Campaigns
     */
    function get(company, code) {
        return $http.get('/api/v1/company/' + company + '/campaigns/' + code + '/');
      //return $http.get('/api/v1/Campaigns/');
    }
    
    function cleanCampaignsBeforeDisplay(results) {
    	var currRecord = '';
    	var campaigns = [];
		for (var i=0; i < results.length; i++)
	    {
		    currRecord = results[i].campaigns;
		    if (currRecord['mkto'])
		    {
		    	for (var key in currRecord['mkto']) // convert first letter to lower case
		    	{
		    		currRecord['mkto'][key.ucfirst()] = currRecord['mkto'][key];	
		    	}
		    	currRecord['mkto']['CreatedDate'] = currRecord['mkto']['CreatedAt']
		    	currRecord['mkto']['sourceSystem'] = 'MKTO';
		    	campaigns.push(currRecord['mkto']);
		    }	
		    else if (currRecord['sfdc'])
		    {
		    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
		    	campaigns.push(currRecord['sfdc']);
		    }
		    else
		    	toastr.error('Something fishy going on!');
	    	
	    }
		return campaigns;
    }
    
  }
})();