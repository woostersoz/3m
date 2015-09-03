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
      //create: create,
      get: get,
      getAll: getAll,
      cleanLeadsBeforeDisplay: cleanLeadsBeforeDisplay,
      filterLeadsinTable: filterLeadsinTable,
      getLeadsByFilter: getLeadsByFilter,
      getLeadsByFilterForDistribution: getLeadsByFilterForDistribution,
      getLeadsByFilterDuration: getLeadsByFilterDuration,
      getLeadsBySourceChannel: getLeadsBySourceChannel,
      getLeadsByRevenueSourceChannel: getLeadsByRevenueSourceChannel
      
    };

    return Leads;

    ////////////////////

    /**
    * @name all
    * @desc Get all Leads
    * @returns {Promise}
    * @memberOf mmm.Leads.services.Leads
    */
    function all(company, pageNumber, perPage) {
      return $http.get('/api/v1/company/' + company + '/leads/?page_number=' + pageNumber + '&per_page=' + perPage);
    }

    /**
     * @name get
     * @desc Get all Leads
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Leads.services.Leads
     */
    function getAll() {
      return $http.get('/api/v1/leads/');
    }
    
    /**
     * @name get
     * @desc Get the Leads of a given user
     * @param {string} username The username to get Leads for
     * @returns {Promise}
     * @memberOf mmm.Leads.services.Leads
     */
    function get(company, code) {
      return $http.get('/api/v1/company/' + company + '/leads/' + code + '/');
      //return $http.get('/api/v1/Leads/');
    }
    
    function getLeadsByFilter(company, leadType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/leads/filter/?lead_type=' + leadType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getLeadsByFilterForDistribution(company, leadType, seriesType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/leads/filter/?lead_type=' + leadType + '&series_type=' + seriesType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    
    function getLeadsByFilterDuration(company, leadType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/leads/filter/duration/?lead_type=' + leadType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getLeadsBySourceChannel(company, source, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/leads/filter/source/?source=' + source + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getLeadsByRevenueSourceChannel(company, source, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/leads/filter/revenue-source/?source=' + source + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function filterLeadsinTable(date, leadType) {
    	toastr.info("fileter");
    }
    
    function cleanLeadsBeforeDisplay(results, calculateStatusDuration, fromStatus, toStatus) {
    	var currRecord = '';
    	var leads = [];
		for (var i=0; i < results.length; i++)
	    {   
			if (results[i].leads)
			{
				currRecord = results[i].leads;
				if (currRecord['mkto'] || currRecord['sfdc'] || currRecord['hspt']) // if it is a lead record
				{
				    
				    if (currRecord['hspt'])
				    {
				    	currRecord['hspt']['sourceSystem'] = 'HSPT';
				    	currRecord['hspt']['Email'] = currRecord['hspt']['email_address'];
				    	currRecord['hspt']['FirstName'] = currRecord['hspt']['properties']['firstname'];
				    	currRecord['hspt']['LastName'] = currRecord['hspt']['properties']['lastname'];
				    	currRecord['hspt']['sourceChannel'] = currRecord['hspt']['properties']['hs_analytics_source'];
				    	currRecord['hspt']['sourceChannelDetail'] = currRecord['hspt']['properties']['hs_analytics_source_data_1'];
				    	
				    	currRecord['hspt']['id'] = currRecord['hspt']['vid'];
				    	// duration related fields below
				    	if (currRecord['hspt']['properties']['SL']) 
				    		currRecord['hspt']['SL'] = currRecord['hspt']['properties']['SL'];
				    	if (currRecord['hspt']['properties']['LM']) 
				    		currRecord['hspt']['LM'] = currRecord['hspt']['properties']['LM'];
				    	if (currRecord['hspt']['properties']['MS']) 
				    		currRecord['hspt']['MS'] = currRecord['hspt']['properties']['MS'];
				    	if (currRecord['hspt']['properties']['SO']) 
				    		currRecord['hspt']['SO'] = currRecord['hspt']['properties']['SO'];
				    	if (currRecord['hspt']['properties']['OC']) 
				    		currRecord['hspt']['OC'] = currRecord['hspt']['properties']['OC'];
				    	if (currRecord['hspt']['properties']['last_stage']) 
				    		currRecord['hspt']['last_stage'] = currRecord['hspt']['properties']['last_stage'];
				    	if (currRecord['hspt']['properties']['days_in_this_stage']) 
				    		currRecord['hspt']['days_in_this_stage'] = currRecord['hspt']['properties']['days_in_this_stage'];
				    	leads.push(currRecord['hspt']);
				    }
				    else if (currRecord['sfdc'])
				    {
				    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
				    	currRecord['sfdc']['id'] = currRecord['sfdc']['Id'];
				    	leads.push(currRecord['sfdc']);
				    }
				    else if (currRecord['mkto'])
				    {   
				    	for (var key in currRecord['mkto']) // convert first letter to lower case
				    	{
				    		currRecord['mkto'][ucFirst(key)] = currRecord['mkto'][key];	
				    	}
				    	currRecord['mkto']['sourceSystem'] = 'MKTO';
				    	currRecord['mkto']['id'] = currRecord['mkto']['id'];
				    	currRecord['mkto']['source_status'] = results[i]['source_status'];
				    	currRecord['mkto']['source_created_date'] = results[i]['source_created_date'];
				    	currRecord['mkto']['sourceChannelDetail'] = results[i]['source_source'];
				    	var currActivities = results[i].activities;
				    	if (currActivities['mkto'] && currActivities['mkto'].length > 0) {
				    		currRecord['mkto']['activities'] = currActivities['mkto'];
				    	}
				    	var currStatuses = results[i].statuses;
				    	if (currStatuses['mkto'] && currStatuses['mkto'].length > 0) {
				    		currRecord['mkto']['statuses'] = currStatuses['mkto'];
				    		currRecord['mkto']['statuses'].sort(dynamicSort('-date')); // sort the statuses in descending order of date
				    	}
				    	if (currRecord['mkto']['activities'] && currRecord['mkto']['activities'].length > 0) {
				    		currRecord['mkto']['activities'] = currRecord['mkto']['activities'].filter(deleteActivity);
				    	}
				    	/*if (calculateStatusDuration)
				    	{ 
				    		var startDate = new Date(), toDate = new Date();
				    		for (var i=0, len = currRecord['mkto']['statuses'].length; i < len; i++)
				    		{
				    			if (currRecord['mkto']['statuses'][i].status == fromStatus) // we have found the first status
				    			{
				    				startDate = moment(new Date(currRecord['mkto']['statuses'][i].date));
				    				for (var j = 0; j < i; j++) // look for the toStatus AFTER the fromStatus
				    				{
				    					if (currRecord['mkto']['statuses'][j].status == toStatus)
				    					{
				    						toDate = moment(new Date(currRecord['mkto']['statuses'][j].date));
				    					}
				    				}
				    			}
				    		}
				    		
				    		//console.log(startDate + 'XX' + toDate );
				    		var durationInDays = toDate.diff(startDate, 'days');
				    		currRecord['mkto']['statusChangeDuration'] = durationInDays;
				    		currRecord['mkto']['statusChangeColumnLabel'] = fromStatus + '->' + toStatus;
				    	}*/
				    	
				    	leads.push(currRecord['mkto']);
				    }	
				    
				    else
				    	toastr.error('Something fishy going on!');
				} // if lead record
			}
			else if (results[i].isContact){ // HSPT lead data coming in from Dashboard drilldown
				currRecord = results[i];
				currRecord['sourceSystem'] = 'HSPT';
		    	currRecord['Email'] = currRecord['email'];
		    	currRecord['FirstName'] = currRecord['firstname'];
		    	currRecord['LastName'] = currRecord['lastname'];
		    	currRecord['sourceChannel'] = currRecord['hs_analytics_source'];
		    	currRecord['sourceChannelDetail'] = currRecord['hs_analytics_source_data_1'];
		    	currRecord['sourceChannelCampaign'] = currRecord['hs_analytics_source_data_2'];
		    	
		    	currRecord['id'] = currRecord['vid'];
		    	leads.push(currRecord);
				
			}
			else if (results[i].mkto_id.length > 0) { // MKTO lead data coming in from Dashboard drilldown 
				currRecord = results[i];
				currRecord['id'] = currRecord['mkto_id'];
				
			}
			else if (results[i].sfdc_id.length > 0) { // MKTO lead data coming in from Dashboard drilldown 
				currRecord = results[i];
				currRecord['id'] = currRecord['sfdc_id'];
				
			}
			else  // contact record
			{
				currRecord =  results[i].contacts
				if (currRecord['mkto'] || currRecord['sfdc'] || currRecord['hspt']) // if it is a lead record
				{
					if (currRecord['sfdc'])
				    {
				    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
				    	leads.push(currRecord['sfdc']);
				    }
				}
			}
		    
         }
		return leads;
    }
    
    function ucFirst(string) {
    	var firstLetter = string.substr(0, 1);
    	return firstLetter.toUpperCase() + string.substr(1);
    }
    
    function dynamicSort(property) {
        var sortOrder = 1;
        if(property[0] === "-") {
            sortOrder = -1;
            property = property.substr(1);
        }
        return function (a,b) {
            var result = (a[property] < b[property]) ? -1 : (a[property] > b[property]) ? 1 : 0;
            return result * sortOrder;
        }
    }
    
    function deleteProperty(array, property, value) { // generic function
    	var i = array.length;
    	while (i--) {
    		if (array[i].property == value)
    			array.splice(i, 1);
    	}
    	return array;
    }
    
    function deleteActivity(obj) { // delete change data value type activities from Mkto array
    	if ('activityTypeId' in obj && obj.activityTypeId != 13)
    		return true;
    }
    
  }
})();