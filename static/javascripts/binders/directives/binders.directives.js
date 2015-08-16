/**
* BinderPage
* @namespace mmm.binders.directives
*/
(function () {
  'use strict';

  var app = angular
    .module('mmm.binders.directives', []);
//    .directive('newIntegration', newIntegration);

  app.directive('binderpage', function($compile) {
	 
	 var linker = function(scope, element, attrs) {
		 element.draggable({
             start: function(event, ui) {
				 element.addClass('draggable');
			 },
			 stop: function(event, ui) {
				 element.removeClass('draggable');
			 }
		 });
		 
		 element.hide().fadeIn('slow');
		 
	 };
	 var controller = function($scope) {
		 $scope.updateBinderPage = function(page) {
			 
		 };
		 $scope.deleteBinderPage = function(id) {
			 $scope.ondelete({
				id: id 
			 });
		 }
		 $scope.showPageContent = function(page) {  
			 $scope.onshowcontent({
				 pages: pages
			 });
		 }
		 
	 };
	 
	 return {
		 restrict: 'A',
		 scope: {
			 ondelete: '&',
			 onshowcontent: '&',
			 page:'='
		 },
		 link: linker,
		 controller: controller
	 };
  });
})();