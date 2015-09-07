/**
* BinderPage
* @namespace mmm.utils.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.binders.services')
    .factory('BinderPage', BinderPage);

  /**
  * @namespace BinderPage
  */
  function BinderPage(Common, Authentication, Analytics, AnalyticsCharts) {
    /**
    * @name Sticky
    * @desc The factory to be returned
    */
    var allPromisesDone = false; // global variable to check state of promises
	var pages = []; // global variable to hold all pages for a given binder
	    
    var BinderPage = {
      createBinderPage: createBinderPage,
      //deleteNote: deleteNote,
      handleDeletedBinderPage: handleDeletedBinderPage,
      handleSelectedBinderPage: handleSelectedBinderPage,
      formatChartPages: formatChartPages
    };

    return BinderPage;

    ////////////////////
    
    
    function createBinderPage(type) {
    	var page = {
    			id: new Date().getTime(),
    			type: type,
    	        title: Common.capitalizeFirstLetter(type) + ' Page',
    	        body: '',
    	        contentBody: '',
    	        selected: true,
    	        chartType: ''
    	}
    	
    	if (type == 'text') 
    		page.contentTitle = 'Page Title';
    	else if (type == 'chart')
    	{
    		page.contentTitle = 'Chart Title';
    		page.chartFilters = {};
    		page.chartFilters.groupDates = {};
    		page.chartFilters.groupDates.date = {
    				startDate : moment().subtract(6, "days").startOf("day"),
					endDate : moment().endOf("day")
    		};
    	}
    	else if (type == 'dashboard')
    	{
    		page.contentTitle = 'Dashboard Title';
    		page.chartFilters = {};
    		page.chartFilters.groupDates = {};
    		page.chartFilters.groupDates.date = {
    				startDate : moment().subtract(6, "days").startOf("day"),
					endDate : moment().endOf("day")
    		};
    	}
    	return page;
    }
    
    function handleDeletedBinderPage(oldBinderPages, id) {
    	var newBinderPages = [];
    	
    	angular.forEach(oldBinderPages, function(binderPage) {
    		if (binderPage.id !== id) newBinderPages.push(binderPage);
    	});
    	return newBinderPages;
    }
    
    function handleSelectedBinderPage(binderPages, id) {
    	
    	angular.forEach(binderPages, function(binderPage) {
    		if (binderPage.id !== id) {
    			binderPage.selected = false;
    		}
    		else {
    			binderPage.selected = true;
    		}
    	});
    	return binderPages;
    }
    
    function formatChartPages(binderPages) { // key function to add charts to binder chart pages

    	
    	
    	
    	
    	//return pages;
    }
    
    function RetrieveAnalyticsSuccessFn(data, status, headers, config) {
    
    }
    
    function RetrieveAnalyticsErrorFn(data, status, headers, config) {
        
    
    }
  }
})();