/**
* Social
* @namespace mmm.social.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.social.services')
    .factory('Social', Social);

  Social.$inject = ['$http'];

  /**
  * @namespace Social
  * @returns {Factory}
  */
  function Social($http) {
    var Social = {
      getTwitterCategories: getTwitterCategories,
      deleteCategory: deleteCategory,
      updateCategory: updateCategory,
      addCategory: addCategory,
      getTweets: getTweets,
      deleteTweet: deleteTweet,
      updateTweet: updateTweet,
      addTweet: addTweet,
      createTwMasterList: createTwMasterList,
      createTwMasterListFromCategory: createTwMasterListFromCategory,
      getTwMasterLists: getTwMasterLists,
      saveTwMasterList: saveTwMasterList,
      publishTwMasterList: publishTwMasterList,
      getTwHandles: getTwHandles, 
      getTwInteractionsByFilter: getTwInteractionsByFilter,
      getCategorySize: getCategorySize
      
    };

    return Social;

    ////////////////////

    function getTwitterCategories(company) {
      return $http.get('/api/v1/company/' + company + '/social/twitter/categories/');
    }

    function deleteCategory(category, company) {
	    return $http.delete('/api/v1/company/' + company + '/social/twitter/category/' + category.id + '/'); 
	}
    
    function updateCategory(category, company) {
    	return $http.put('/api/v1/company/' + company + '/social/twitter/category/' + category.id + '/', category);
    }
    
    function addCategory(category, company) {
    	return $http.post('/api/v1/company/' + company + '/social/twitter/category/0/', category);
    }
    
    function getTweets(company, pageNumber, perPage) {
        return $http.get('/api/v1/company/' + company + '/social/tweets/?' + 'page_number=' + pageNumber + '&per_page=' + perPage );
    }

    function deleteTweet(tweet, company) {
	    return $http.delete('/api/v1/company/' + company + '/social/tweet/' + tweet.id + '/'); 
	}
    
    function updateTweet(tweet, company, pageNumber, perPage) {
    	return $http.put('/api/v1/company/' + company + '/social/tweet/' + tweet.id + '/?' + 'page_number=' + pageNumber + '&per_page=' + perPage, tweet);
    }
    
    function addTweet(tweet, company, pageNumber, perPage) {
    	return $http.post('/api/v1/company/' + company + '/social/tweet/0/?' + 'page_number=' + pageNumber + '&per_page=' + perPage, tweet);
    }
    
    function createTwMasterList(company) {
    	return $http.get('/api/v1/company/' + company + '/social/twitter/masterlist/0/');
    }
    
    function createTwMasterListFromCategory(company, category, count) {
    	return $http.get('/api/v1/company/' + company + '/social/twitter/masterlist/0/?category=' + category + '&count=' + count);
    }
    
    function getTwMasterLists(company) {
        return $http.get('/api/v1/company/' + company + '/social/twitter/masterlists/');
    }
    
    function saveTwMasterList(company, tweets) {
    	return $http.post('/api/v1/company/' + company + '/social/twitter/masterlist/0/', tweets);
    }
    
    function publishTwMasterList(company, mlId) {
    	return $http.post('/api/v1/company/' + company + '/social/twitter/masterlist/' + mlId + '/publish/');
    }
    
    function getTwHandles(company) {
        return $http.get('/api/v1/company/' + company + '/social/twitter/handles/');
    }
    
    function getTwInteractionsByFilter(company, interactionType, startDate, endDate, queryType, pageNumber, perPage, systemType, chartName) { // called from Analytics
    	return $http.get('/api/v1/company/' + company + '/social/twitter/filter/?interaction_type=' + interactionType + '&start_date=' + startDate + '&end_date=' + endDate + '&query_type=' + queryType + '&page_number=' + pageNumber + '&per_page=' + perPage + '&system_type=' + systemType + '&chart_name=' + chartName);
    }
    
    function getCategorySize(company, category_id) {
        return $http.get('/api/v1/company/' + company + '/social/twitter/category/size/?category_id=' + category_id);
    }
    
  }
})();