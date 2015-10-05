/**
* SocialController
* @namespace mmm.social.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.social.controllers', ['datatables'])
    .controller('SocialController', SocialController);
  
  SocialController.$inject = ['$scope', 'Social', 'Authentication', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter', '$state', '$stateParams', '$document', '$window', 'Common'];

  /**
  * @namespace SocialController
  */
  function SocialController($scope, Social, Authentication, $state, $stateParams, $location, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $filter, $document, $window, Common) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.tw_categories = [];
    vm.social = []; 
    $scope.social = [];
   
    $scope.deleteCategory = deleteCategory;
    $scope.confirmedDeleteCategory = confirmedDeleteCategory;
    $scope.cancelDeleteCategory = cancelDeleteCategory;
    //$scope.editCategory = editCategory;
    $scope.deleteTweet = deleteTweet;
    $scope.confirmedDeleteTweet = confirmedDeleteTweet;
    $scope.cancelDeleteTweet = cancelDeleteTweet;
    
    $scope.editingData = [];
    $scope.addRow = false;
    $scope.newCategory = {};
    $scope.tw_categories = [];
    $scope.newTweet = {};
    $scope.selected = {}; // for creation of ML by specific category
    $scope.tweets = [];
    $scope.newTwMl = {};
    $scope.newTwMl.tweets = [];
    $scope.newTwMl.tw_handle = '';
    $scope.newTwMl.buffer_profile_id = '';
    $scope.tw_ml = [];
    $scope.createTwML = false;
    $scope.selected_tw_handle = {};
    
    $scope.totalMl = 0;
    $scope.mlPerPage = 10;
    $scope.totalInteractions = 0;
    $scope.interactionsPerPage = 10;
    $scope.currentPage = 1;
    
    $scope.showingMl = [];
    for (var i=0, length = $scope.tw_ml.length; i < length; i++) {
    	$scope.showingMl[$scope.tw_ml[i].id] = false;
    }
    
    $scope.showMl = function(ml) {
    	$scope.showingMl[ml.id] = true;
    }
    
    $scope.hideMl = function(ml) {
    	$scope.showingMl[ml.id] = false;
    }
    
    $scope.createTwMl = createTwMasterList;
    $scope.createTwMlFromCategory = createTwMasterListFromCategory;
    $scope.getCategorySize = getCategorySize;
    
    function getCategorySize() {
    	var account = Authentication.getAuthenticatedAccount();
    	Social.getCategorySize(account.company, $scope.selected.category.id).then(CategorySizeSuccess, CategorySizeError);
    }
    
    function CategorySizeSuccess(data, status, headers, config) { 
    	
    	if (data.data.category_count) 
    	{
    	   $scope.selected.category.size = data.data.category_count;
    	   $scope.selected.category.count = data.data.category_count; // initialize .count to the same value as .size
    	}
    	else
    		toastr.error('Could not get category size');
    
    }
    
    function CategorySizeError(data, status, headers, config) { 
    	toastr.error('Could not get category size');
        
    }
    
    $scope.discardTwMl = function() {
    	$scope.createTwML = false;
    	$scope.newTwMl = {};
    }
    
    $scope.deleteMlTweet = function(mlTweetId) {
    	$scope.newTwMl.tweets = Common.removeByAttr($scope.newTwMl.tweets, 'tweet_id', mlTweetId);
    }
    
    $scope.saveTwMl = saveTwMasterlist;
    
    $scope.savePublishTwMl = savePublishTwMasterlist;
    
    $scope.publishMl = function(twMlID) {
    	onlyPublishMl(twMlID);
    }
    
    $scope.addNewRow = function() {
    	$scope.addRow = true;
    	
    }
    
    $scope.cancelAdd = function() {
    	$scope.addRow = false;
    }
    
    $scope.addTweet = function(tweet) {
    	$scope.addRow = false;
    	var account = Authentication.getAuthenticatedAccount();
    	Social.addTweet(tweet, account.company, $scope.currentPage, $scope.interactionsPerPage).then(TweetsAdminSuccessFn,TweetsAdminErrorFn);
    	
    }
    
    $scope.editTweet = function(tweet) {

    	$scope.editingData[tweet.id] = true;  
    	
    };
    
    $scope.updateTweet = function(tweet) {
    	$scope.editingData[tweet.id] = false; 
    	var account = Authentication.getAuthenticatedAccount();
    	Social.updateTweet(tweet, account.company, $scope.currentPage, $scope.interactionsPerPage).then(TweetsAdminSuccessFn,TweetsAdminErrorFn);
    };
    
    $scope.cancelTweet = function(tweet) {
    	$scope.editingData[tweet.id] = false;  
    };
    
    $scope.addCategory = function(category) {
    	$scope.addRow = false;
    	var account = Authentication.getAuthenticatedAccount();
    	Social.addCategory(category, account.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
    	
    }
    
    $scope.editCategory = function(category) {

    	$scope.editingData[category.id] = true;  
    	
    };
    
    $scope.updateCategory = function(category) {
    	$scope.editingData[category.id] = false; 
    	var account = Authentication.getAuthenticatedAccount();
    	Social.updateCategory(category, account.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
    };
    
    $scope.cancelCategory = function(category) {
    	$scope.editingData[category.id] = false;  
    };
   
    
    if ($state.$$url == '/twitter-admin')
    {
    	twitterAdmin();
    }
    else if ($state.$$url == '/tweets')
    {
    	tweets();
    }
    else if ($state.$$url == '/twitter-master-list')
    {
    	getTwMasterLists(1);
   	}


    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.SocialController
    */
    function activate() {   
    
    	
    }
    
    function twitterAdmin()
    {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Social.getTwitterCategories(account.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
   
    function TwitterAdminSuccessFn(data, status, headers, config) { 
     $scope.newCategory = {};
     if (data.data) // contains Tw Categories
	 {  
		vm.tw_categories = data.data;
    	$scope.tw_categories = [];
    	var weight = 0;
        for (var i=0, length = vm.tw_categories.length; i < length; i++) {
        	$scope.tw_categories[vm.tw_categories[i].id] = false;
        	weight += vm.tw_categories[i].weight;
        }
        
        if (weight != 100)
        	toastr.error("The category weights don't add up to 100");
		
        for (var i=0, length = vm.tw_categories; i < length; i++) {
        	$scope.editingData[vm.tw_categories[i].id] = false;
        }
	 }
	 else
		 toastr.error("Something went wrong!");
      }
    
    function TwitterAdminErrorFn(data, status, headers, config) {
    	$scope.newCategory = {};
        toastr.error('Twitter admin data could not be retrieved');
      }
    
    function deleteCategory(category) {
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
        if (!authenticatedAccount) {
          $location.url('/');
          toastr.error('You are not authorized to delete data.');
        } else {
     	   $scope.tw_categories[category.id] = true;
        }     
    }
    
    function confirmedDeleteCategory(category) {
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
        if (!authenticatedAccount) {
          $location.url('/');
          toastr.error('You are not authorized to delete data.');
        } else {
    	  Social.deleteCategory(category, authenticatedAccount.company).then(ConfirmedDeleteSuccessFn, ConfirmedDeleteErrorFn);
        }
    }
    
    function ConfirmedDeleteSuccessFn(data, status, headers, config) { 
    	if (data.data)
    	{
    		toastr.success("Category deleted");
    		var authenticatedAccount = Authentication.getAuthenticatedAccount();
    		Social.getTwitterCategories(authenticatedAccount.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
    	}
     }
   
   function ConfirmedDeleteErrorFn(data, status, headers, config) {
       // $location.url('/');
	   if (data.data)
		   toastr.error(data.data);
	   else
           toastr.error('Category could not be deleted');
     }
   
   function cancelDeleteCategory(category) {
		  $scope.tw_categories[category.id] = false;
	  }
   
   function tweets()
   {
   	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    {
	    	Social.getTweets(account.company, $scope.currentPage, $scope.interactionsPerPage).then(TweetsAdminSuccessFn,TweetsAdminErrorFn);
	    	Social.getTwitterCategories(account.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
	    }
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
   }
   
  
   function TweetsAdminSuccessFn(data, status, headers, config) { 
	 $scope.newTweet = {};
	 if (data.data) // contains Tweets
	 {  
		vm.tweets = data.data.results;
		$scope.totalCount = data.data.totalCount;
		$scope.lastDateCreated = data.data.lastDateCreated;
		$scope.firstDateCreated = data.data.firstDateCreated;
		$scope.totalInteractions = data.data.totalCount;
		$scope.thisSetCount = data.data.results.length;
		// initialize the start and end counts shown near pagination control
		$scope.startInteractionCounter = ($scope.currentPage - 1) * $scope.interactionsPerPage + 1;
	    $scope.endInteractionCounter = ($scope.thisSetCount < $scope.interactionsPerPage) ? $scope.startInteractionCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.interactionsPerPage;
		
		for (var i=0, length = vm.tweets; i < length; i++) {
        	$scope.editingData[vm.tweets[i].id] = false;
        }
	 }
	 else
		 toastr.error("Something went wrong!");
     }
   
   function TweetsAdminErrorFn(data, status, headers, config) {
	   $scope.newTweet = {};
	   if (data.data)
		   toastr.error(data.data);
	   else
           toastr.error('Tweets could not be retrieved');
     }
   
   function deleteTweet(tweet) {
   	var authenticatedAccount = Authentication.getAuthenticatedAccount();
       if (!authenticatedAccount) {
         $location.url('/');
         toastr.error('You are not authorized to delete data.');
       } else {
    	   $scope.tweets[tweet.id] = true;
       }     
   }
   
   function confirmedDeleteTweet(tweet) {
   	var authenticatedAccount = Authentication.getAuthenticatedAccount();
       if (!authenticatedAccount) {
         $location.url('/');
         toastr.error('You are not authorized to delete data.');
       } else {
   	  Social.deleteTweet(tweet, authenticatedAccount.company).then(ConfirmedTweetDeleteSuccessFn, ConfirmedTweetDeleteErrorFn);
       }
   }
   
   function ConfirmedTweetDeleteSuccessFn(data, status, headers, config) { 
   	if (data.data)
   	{
   		toastr.success("Tweet deleted");
   		var authenticatedAccount = Authentication.getAuthenticatedAccount();
   		Social.getTweets(authenticatedAccount.company, $scope.currentPage, $scope.interactionsPerPage).then(TweetsAdminSuccessFn,TweetsAdminErrorFn);
   		Social.getTwitterCategories(authenticatedAccount.company).then(TwitterAdminSuccessFn,TwitterAdminErrorFn);
   	}
    }
  
  function ConfirmedTweetDeleteErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
           toastr.error('Tweet could not be deleted');
    }
  
  function cancelDeleteTweet(tweet) {
		  $scope.tweets[tweet.id] = false;
	  }
    
  
  function getTwMasterLists(pageNumber)
  {
  	var account = Authentication.getAuthenticatedAccount();
	    if (account) {
	    	Social.getTwMasterLists(account.company).then(getTwMasterListSuccessFn,getTwMasterListErrorFn);
	    	$scope.pagination = { current: 1 };
	    }
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
  }
  
  $scope.pageChanged = function(newPage) {
  	$scope.currentPage = newPage;
  	getTwMasterLists(newPage);
  }
 
  function getTwMasterListSuccessFn(data, status, headers, config) { 
	 $scope.tw_ml = data.data.results;
	 $scope.totalCount = data.data.totalCount;
	 $scope.numPublished = data.data.numPublished;
	 $scope.totalTwCount = data.data.totalTwCount;
	 
     $scope.newTwMl = {};
     $scope.createTwML = false;
  }
  
  function getTwMasterListErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
          toastr.error('Could not retrieve master lists');
    }

  function createTwMasterList()
  {
	$scope.select_by_category = false;
  	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Social.createTwMasterList(account.company).then(createTwMasterListSuccessFn,createTwMasterListErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
  }
  
  function createTwMasterListFromCategory()
  {
	twitterAdmin();
	var category = "";
	var count = 'Undefined';
	if ($scope.selected.category == undefined)
		category = 'Undefined';
	else if ($scope.selected.category.id == "")
		category = 'Undefined';
	else
	{
		category = $scope.selected.category.id;
		count = $scope.selected.category.count;
	}
	$scope.select_by_category = true;
  	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    	Social.createTwMasterListFromCategory(account.company, category, count).then(createTwMasterListSuccessFn,createTwMasterListErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
  }
  
 
  function createTwMasterListSuccessFn(data, status, headers, config) { 
	  var account = Authentication.getAuthenticatedAccount();
	  if (data.data) {
		  //$scope.tw_ml = data.data;
          $scope.newTwMl.tweets = data.data;
          $scope.createTwML = true;
          if ($scope.select_by_category && $scope.newTwMl.tweets.length > 0) // if called from select by category, set the dropdown value to selected category
          {	
        	  if (!$scope.selected.category)
        		 $scope.selected.category = {};
        	  $scope.selected.category.id = $scope.newTwMl.tweets[0].category_id;
        	  $scope.selected.category.count = $scope.newTwMl.tweets.length;
        	  if (!$scope.selected.category.size)
        	     $scope.selected.category.size = $scope.newTwMl.tweets.length;
          }
          Social.getTwHandles(account.company).then(createTwHandlesSuccessFn,createTwHandlesErrorFn);
	  }
	  else
          toastr.error('Master List could not be created');
  }
  
  function createTwMasterListErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
          toastr.error('Master List could not be created');
    }

  function createTwHandlesSuccessFn(data, status, headers, config) {
	  if (data.data.results)
		  $scope.tw_handles = data.data.results;
	  else if (data.data.error)
		  toastr.error(data.data.error);
	  else
          toastr.error('Twitter handles could not be retrieved');
    }

  function createTwHandlesErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
          toastr.error('Twitter handles could not be retrieved');
    }

  function saveTwMasterlist() {
	  var account = Authentication.getAuthenticatedAccount();
	  if (account) 
	  { 
		if ($scope.selected_tw_handle.id == null)
		{
			toastr.error('Choose a Twitter handle before saving the master list');
			return false;
		}	
		var list = {};
		list.tweets = $scope.newTwMl.tweets;
		$scope.newTwMl.buffer_profile_id = $scope.selected_tw_handle.id;
		$scope.newTwMl.tw_handle = $scope.selected_tw_handle.service_username;
	  	Social.saveTwMasterList(account.company, $scope.newTwMl).then(saveTwMasterListSuccessFn, saveTwMasterListErrorFn);
	  }
	  else {
	  	toastr.error('You need to login first');
	  	$location.path('/login'); 
	  }
  }
  
  function saveTwMasterListSuccessFn(data, status, headers, config) { 
      
	  if (data.data) {
		  //$scope.tw_ml = data.data;
          $scope.newTwMlID = data.data.id;
          getTwMasterLists(1);
	  }
	  else
          toastr.error('Master List could not be saved');
  }
  
  function saveTwMasterListErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
          toastr.error('Master List could not be saved');
    }
  
  function savePublishTwMasterlist() {
	  var account = Authentication.getAuthenticatedAccount();
	  if (account) 
	  {
	    if ($scope.selected_tw_handle.id == null)
		{
			toastr.error('Choose a Twitter handle before saving the master list');
			return false;
		}	
		var list = {};
		list.tweets = $scope.newTwMl;
		$scope.newTwMl.buffer_profile_id = $scope.selected_tw_handle.id;
		$scope.newTwMl.tw_handle = $scope.selected_tw_handle.service_username;
	  	Social.saveTwMasterList(account.company, $scope.newTwMl).then(savePublishTwMasterListSuccessFn, savePublishTwMasterListErrorFn);
	  }
	  else {
	  	toastr.error('You need to login first');
	  	$location.path('/login'); 
	  }
  }
  
function savePublishTwMasterListSuccessFn(data, status, headers, config) { 
      
	  if (data.data) {
		  //$scope.tw_ml = data.data;
          $scope.newTwMlID = data.data.id;
          var account = Authentication.getAuthenticatedAccount();
          Social.publishTwMasterList(account.company, $scope.newTwMlID).then(publishTwMasterListSuccessFn, publishTwMasterListErrorFn);
	  }
	  else
          toastr.error('Master List could not be saved');
  }
  
  function savePublishTwMasterListErrorFn(data, status, headers, config) {
	  if (data.data)
		   toastr.error(data.data);
	   else
          toastr.error('Master List could not be saved');
    }
	 
  function publishTwMasterListSuccessFn(data, status, headers, config) { 
      getTwMasterLists(1);
      toastr.success('Master List scheduled for publishing');
  }
  
  function publishTwMasterListErrorFn(data, status, headers, config) { 
	  
  }
  
  function onlyPublishMl(twMlID)
  {
	 var account = Authentication.getAuthenticatedAccount();
     Social.publishTwMasterList(account.company, twMlID).then(publishTwMasterListSuccessFn, publishTwMasterListErrorFn);
  }
  
  $scope.pageChanged = function(newPage) {
		$scope.currentPage = newPage;
		tweets();
  }
  
  	  
  }
})();