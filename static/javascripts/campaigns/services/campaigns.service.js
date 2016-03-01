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
      cleanCampaignsBeforeDisplay: cleanCampaignsBeforeDisplay,
      getEventsByCampaignEmailEventType: getEventsByCampaignEmailEventType,
      getEventsByEmailCTA: getEventsByEmailCTA
      
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
		    	/*for (var key in currRecord['mkto']) // convert first letter to lower case
		    	{
		    		currRecord['mkto'][key.ucfirst()] = currRecord['mkto'][key];	
		    	}*/
		    	currRecord['mkto']['createdDate'] = moment(currRecord['mkto']['createdAt'], "YYYY-MM-DDTHH:mm:ssZ+0000").format();
		    	currRecord['mkto']['sourceSystem'] = 'MKTO';
		    	campaigns.push(currRecord['mkto']);
		    }	
		    else if (currRecord['sfdc'])
		    {
		    	currRecord['sfdc']['name'] = currRecord['sfdc']['Name'];
		    	currRecord['sfdc']['description'] = currRecord['sfdc']['Description'];
		    	currRecord['sfdc']['type'] = currRecord['sfdc']['Type'];
		    	currRecord['sfdc']['status'] = currRecord['sfdc']['Status'];
		    	currRecord['sfdc']['num_leads'] = currRecord['sfdc']['NumberOfLeads'];
		    	currRecord['sfdc']['num_contacts'] = currRecord['sfdc']['NumberOfContacts'];
		    	currRecord['sfdc']['num_opps'] = currRecord['sfdc']['NumberOfOpportunities'];
		    	currRecord['sfdc']['url'] = "http://login.salesforce.com/" + currRecord['sfdc']['Id'];
		    	currRecord['sfdc']['createdDate'] = moment(currRecord['sfdc']['CreatedDate'], "YYYY-MM-DDTHH:mm:ss.000+0000").format();
		    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
		    	campaigns.push(currRecord['sfdc']);
		    }
		    else
		    	toastr.error('Something fishy going on!');
			
			
	    	
	    }
		return campaigns;
    }
    
    function getEventsByCampaignEmailEventType(company, eventType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName, selectedCampaignGuid, emailId) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/campaigns/filter/events/?event_type=' + eventType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName + '&campaign_guid=' + selectedCampaignGuid + '&email_id=' + emailId);
    }
    
    
    function getEventsByEmailCTA(company, eventType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName, url) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/campaigns/filter/ctas/?event_type=' + eventType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName + '&url=' + url);
    }
  }
})();