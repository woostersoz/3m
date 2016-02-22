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
    	removeItemFromArray: removeItemFromArray,
    	findByAttr: findByAttr,
    	findItemsByAttr: findItemsByAttr,
    	containsItemsByAttr: containsItemsByAttr,
    	capitalizeFirstLetter: capitalizeFirstLetter,
    	capitalizeSentence: capitalizeSentence,
        exportToPdf: exportToPdf,
        getCountriesGeoData: getCountriesGeoData,
        getCountriesData: getCountriesData,
        sortByProperty: sortByProperty,
        generateScreenshot: generateScreenshot
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
    
    function removeItemFromArray(arr, value){
	    var i = arr.length;
	    while(i--){
	       if( arr[i] 
	           && (arr[i] === value ) ){ 

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
    
    function containsItemsByAttr(arr, attr, value){ //looks for string 'value' contained in the 'attr'; returns multiple items as array
	    var i = arr.length;
	    var result = [];
	    while(i--){
	       if( arr[i] 
	           && arr[i].hasOwnProperty(attr) 
	           && (arguments.length > 2 && arr[i][attr].toLowerCase().indexOf(value.toLowerCase()) != -1) ){ 

	           result.push(arr[i]);

	       }
	    }
	    return result;
	    
	}
    
    function capitalizeFirstLetter(stringX) { 
    	return stringX.charAt(0).toUpperCase() + stringX.slice(1);
    }
    
    function capitalizeSentence(stringX) {
    	return stringX.replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); });
    }
    
    function sortByProperty(property) {
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
    
    function exportToPdf(company, object, id, template_name, source_type) {
    	return $http.get('/api/v1/export/pdf/?object=' + object + '&id=' + id + '&company=' + company + '&template_name=' + template_name + '&source_type=' + source_type); //, {responseType: 'arraybuffer'}
    }
    
    function getCountriesData() {
    	return $http.get('/static/data/countries');
    }
    
    function getCountriesGeoData() {
    	return $http.get('/static/data/geo.json');
    }
    
    function generateScreenshot(url) {
    	return $http.get('/capture?url=' + url);
    }
    
    
  }
})();