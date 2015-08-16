/**
* Messages
* @namespace mmm.messages.directives
*/
(function () {
  'use strict';

  var app = angular
    .module('mmm.messages.directives', []);
//    .directive('newIntegration', newIntegration);

  app.directive('modalSnapshot', ['$compile',
                                   function($compile) {
                                     return {
                                    	 restrict: 'A',
                                    	 template: '',
                                    	 scope: {
                                    		 snapshotHtml: "="
                                    	 },
                                    	 link: function(scope, element, attrs) { 
                                    		 //var elementTmp = angular.element(scope.$parent.snapshotHtml);
                                    		 //var newElement = $compile(elementTmp)(scope);
                                    		 //element.append(newElement);
                                    	 angular.element(element).html(scope.$parent.snapshotHtml);
                                    	 }
                                     }
                                   }
                                 ]);
})();