/*! ngBackStretchCarousel - an AngularJS directive
 * Useses jQuery backstretch with an image selector, swipe effects and
 * ajax reader for the images
 * Depends on jQuery and AngularJs.. Lazy to make and dependency file
 * 
 * Copyright (c) 2014 Antti Stenvall; Licensed MIT 
 * 
 * Example use
 *  - in template
 *    <div ng-controller='temp' ng-back-stretch-carousel></div>
 *    
 *  - in controller
 *  app.controller('temp', ['$scope', '$http', function($scope, $http) {
 *     $scope.images = [];
 *     $http({
 *       method: 'get',
 *       url: 'rest/gimmeMyImageData'
 *     }).success(function(data) {      
 *       $scope.images = data.images;
 *     });
 *   }]);    
 * 
 * */

var app = angular
    .module('mmm.authentication.directives', []);

app.directive('ngBackStretchCarousel', ['$swipe', function($rootScope, $swipe) {
  var directive = {}; // init directive
  directive.restrict = 'A'; // one just uses ng-back-stretch-carousel attribute to utilize this
  directive.compile = function(element, attributes) {
    var linkFunction = function($scope, element, atttributes) {
      // change the height of the element to the parent's height
      var height = element.parent()[0].parentNode.scrollHeight;
      $(element).css('height', height);
      // follow changes in $scope.images and when it changes, init backstretch
      // this allows initiation with $http ajax request that asks for the files
      $scope.$watch('images', function(images) {
        if (images.length === 0) { // do nothing is images is empty array
          return;
        }
        // remove old if it exists
        if ($(element).children() !== null) {
          //$($(element).children()).remove();
        }
        // add backstretch
        $(element).backstretch(images, {duration: 3000, fade: 700});
        var index = 0; // set which one is running
        // bind swipes left and right 
        /*(function() {
          // introduce swipe local variables
          var endAction, startX, deltaX;
          $swipe.bind(element, {
            start: function(coords) {
              endAction = null;
              startX = coords.x;
            },
            cancel: function(e) {
              endAction = null;
              e.stopPropagation();
            },
            end: function(coords, e) {
              if (endAction === 'prev') {
                index = index === 0 ? $scope.images.length - 1 : index - 1;
              } else if (endAction === 'next') {
                index = index === ($scope.images.length - 1) ? 0 : index + 1;
              }
              if (endAction !== null) {
                $(element).backstretch('show', index);
              }
              e.stopPropagation();
            },
            move: function(coords) {
              deltaX = coords.x - startX;
              var deltaXRatio = deltaX / element[0].clientWidth;
              // swipe thresholds are determined here
              if (deltaXRatio > 0.2) {
                endAction = 'next';
              } else if (deltaXRatio < -0.2) {
                endAction = 'prev';
              } else {
                endAction = null;
              }
            }
          });
        })(); */
        // Add carousel action list here
        var div = document.createElement('div');
        // bind event to backstretch.before (could be as well after, but this gives faster response to click)
        $(window).on('backstretch.before', function(e, instance, i) {
          var elements = $(div).children();
          $(elements).removeClass('active');
          $(elements[i]).addClass('active');
          index = i;
        });
        $(div).addClass('ngBackStretchCarouselList')
                .appendTo(element);
        var clicker = function(el, ind) {
          $(el).bind('click touch', function() {
            $(element).backstretch('show', ind);
          });
        }
        for (var i = 0; i < images.length; i++) {
          var a = document.createElement('a');
          if (i === 0) {
            $(a).addClass('active');
          }
          $(a).appendTo(div);
          (function(element, ind) {
            clicker(element, ind);
          })(a, i);
        }
      });
    }
    return linkFunction;
  }
  return directive;
}]);