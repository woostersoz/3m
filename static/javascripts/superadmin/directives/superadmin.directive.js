/**
* Posts
* @namespace mysite.posts.directives
*/
(function () {
  'use strict';

  var app = angular
    .module('mmm.superadmin.directives', []);
//    .directive('newIntegration', newIntegration);

  app.directive('mongonaut', ['$compile',
                                   function($compile) {
                                     return function(scope, element, attrs) {
                                       scope.$watch(
                                         function(scope) {
                                           // watch the 'mongonaut' expression for changes
                                           return scope.$eval(attrs.mongonaut);
                                         },
                                         function(value) {
                                           // when the 'newIntegration' expression changes
                                           // assign it into the current DOM
                                           element.html(scope.templateHtml);

                                           // compile the new DOM and link it to the current
                                           // scope.
                                           // NOTE: we only compile .childNodes so that
                                           // we don't get into infinite loop compiling ourselves
                                           $compile(element.contents())(scope);
                                         }
                                       );
                                     };
                                   }
                                 ]);
})();