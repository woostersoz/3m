/**
* Common
* @namespace mmm.common.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.common.services')
    .factory('Common', Common);

  Common.$inject = ['$http'];

  /**
  * @namespace Social
  * @returns {Factory}
  */
  function Common($http) {
    var Common = {
    	removeByAttr: removeByAttr, 
    	findByAttr: findByAttr,
    	findItemsByAttr: findItemsByAttr,
    	capitalizeFirstLetter: capitalizeFirstLetter,
        exportToPdf: exportToPdf,
        getCountriesGeoData: getCountriesGeoData,
        getCountriesData: getCountriesData
    };

    return Common;

    ////////////////////

    function removeByAttr(arr, attr, value){
	    var i = arr.length;
	    while(i--){
	       if( arr[i] 
	           && arr[i].hasOwnProperty(attr) 
	           && (arguments.length > 2 && arr[i][attr] === value ) ){ 

	           arr.splice(i,1);

	       }
	    }
	    return arr;
	}
    
    function findByAttr(arr, attr, value){
	    var i = arr.length;
	    while(i--){
	       if( arr[i] 
	           && arr[i].hasOwnProperty(attr) 
	           && (arguments.length > 2 && arr[i][attr] === value ) ){ 

	           return arr[i]

	       }
	    }
	    
	}
    
    function findItemsByAttr(arr, attr, value){ //returns multiple items as array
	    var i = arr.length;
	    var result = [];
	    while(i--){
	       if( arr[i] 
	           && arr[i].hasOwnProperty(attr) 
	           && (arguments.length > 2 && arr[i][attr] === value ) ){ 

	           result.push(arr[i]);

	       }
	    }
	    return result;
	    
	}
    
    function capitalizeFirstLetter(stringX) { 
    	return stringX.charAt(0).toUpperCase() + stringX.slice(1);
    }
    
    function exportToPdf(company, object, id) {
    	return $http.get('/api/v1/export/pdf/?object=' + object + '&id=' + id + '&company=' + company, {responseType: 'arraybuffer'});
    }
    
    function getCountriesData() {
    	return $http.get('/static/data/countries');
    }
    
    function getCountriesGeoData() {
    	return $http.get('/static/data/geo.json');
    }
    
    
  }
})();