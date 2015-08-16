/**
* Websites
* @namespace mmm.websites.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.websites.services')
    .factory('Websites', Websites);

  Websites.$inject = ['$http'];

  /**
  * @namespace Websites
  * @returns {Factory}
  */
  function Websites($http) {
    var Websites = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      cleanWebsitesBeforeDisplay: cleanWebsitesBeforeDisplay,
      filterWebsitesinTable: filterWebsitesinTable,
      getWebsitesByFilter: getWebsitesByFilter,
      getWebsitesByFilterForDistribution: getWebsitesByFilterForDistribution,
      getWebsitesByFilterDuration: getWebsitesByFilterDuration,
      getWebsitesBySourceChannel: getWebsitesBySourceChannel,
      getWebsitesByRevenueSourceChannel: getWebsitesByRevenueSourceChannel
      
    };

    return Websites;

    ////////////////////

    /**
    * @name all
    * @desc Get all Websites
    * @returns {Promise}
    * @memberOf mmm.Websites.services.Websites
    */
    function all(company, pageNumber, perPage) {
      return $http.get('/api/v1/company/' + company + '/websites/?page_number=' + pageNumber + '&per_page=' + perPage);
    }

    /**
     * @name get
     * @desc Get all Websites
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Websites.services.Websites
     */
    function getAll() {
      return $http.get('/api/v1/websites/');
    }
    
    /**
     * @name get
     * @desc Get the Websites of a given user
     * @param {string} username The username to get Websites for
     * @returns {Promise}
     * @memberOf mmm.Websites.services.Websites
     */
    function get(company, code) {
      return $http.get('/api/v1/company/' + company + '/websites/' + code + '/');
      //return $http.get('/api/v1/Websites/');
    }
    
    function getWebsitesByFilter(company, visitorType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName, filters) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/websites/filter/?visitor_type=' + visitorType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName + '&filters=' + JSON.stringify(filters));
    }
    
    function getWebsitesByFilterForDistribution(company, websiteType, seriesType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/websites/filter/?website_type=' + websiteType + '&series_type=' + seriesType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    
    function getWebsitesByFilterDuration(company, websiteType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/websites/filter/duration/?website_type=' + websiteType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getWebsitesBySourceChannel(company, source, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/websites/filter/source/?source=' + source + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getWebsitesByRevenueSourceChannel(company, source, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/websites/filter/revenue-source/?source=' + source + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function filterWebsitesinTable(date, websiteType) {
    	toastr.info("fileter");
    }
    
    function cleanWebsitesBeforeDisplay(results, calculateStatusDuration, fromStatus, toStatus) {
    	var currRecord = '';
    	var websites = [];
		for (var i=0; i < results.length; i++)
	    {
			currRecord = results[i].websites;
			if (currRecord['mkto'] || currRecord['sfdc'] || currRecord['hspt']) // if it is a website record
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
			    	websites.push(currRecord['hspt']);
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
			    	
			    	websites.push(currRecord['mkto']);
			    }	
			    else if (currRecord['sfdc'])
			    {
			    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
			    	currRecord['sfdc']['id'] = currRecord['sfdc']['Id'];
			    	websites.push(currRecord['sfdc']);
			    }
			    else
			    	toastr.error('Something fishy going on!');
			} // if website record
			else  // contact record
			{
				currRecord =  results[i].contacts
				if (currRecord['mkto'] || currRecord['sfdc'] || currRecord['hspt']) // if it is a website record
				{
					if (currRecord['sfdc'])
				    {
				    	currRecord['sfdc']['sourceSystem'] = 'SFDC';
				    	websites.push(currRecord['sfdc']);
				    }
				}
			}
		    
         }
		return websites;
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