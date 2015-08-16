(function () {
  'use strict';

angular
    .module('mmm.integrations.services')
    .service('IntegrationService', function () {
        var newSystem = {};

        return {
            saveNewSystem:function(data) {
            	newSystem = data;
                console.log(data);
            },
            getNewSystemx:function() { console.log(newSystem);
                return newSystem;
            }
        };
    });

})();