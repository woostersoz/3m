/**
* Stickies
* @namespace mmm.utils.directives
*/
(function () {
  'use strict';

  var app = angular
    .module('mmm.utils.directives', []);
//    .directive('newIntegration', newIntegration);

  app.directive('sticky', function() {
	 
	 var linker = function(scope, element, attrs) {
		 element.draggable({
			 stop: function(event, ui) {
				 if (!element.cssStyle)
					 element.cssStyle = {};
				 scope.$apply(function() {
					 element.cssStyle.left = ui.position.left + 'px';
					 element.cssStyle.top = ui.position.top + 'px';
				 })
				 
				 
			 }
		 });
		 
		 //element.css('left10px');
		 //element.css('top50px');
		 
		 element.hide().fadeIn('slow');
		 
	 };
	 var controller = function($scope) {
		 $scope.updateNote = function(note) {
			 
		 };
		 $scope.deleteNote = function(id) {
			 $scope.ondelete({
				id: id 
			 });
		 }
	 };
	 return {
		 restrict: 'A',
		 scope: {
			 ondelete: '&',
			 note:'='
		 },
		 link: linker,
		 controller: controller
	 };
  });
})();