/**
* CampaignsController
* @namespace mmm.campaigns.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.campaigns.controllers', ['datatables'])
    .controller('CampaignsController', CampaignsController);
  
  CampaignsController.$inject = ['$scope', 'Campaigns', 'Authentication', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$location', 'ngDialog', '$filter'];

  /**
  * @namespace CampaignsController
  */
  function CampaignsController($scope, Campaigns, Authentication, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $location, ngDialog, $filter) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.campaigns = []; 
    vm.xclickHandler = xclickHandler;
    
    DTInstances.getLast().then(function (dtInstance) {
        vm.dtInstance = dtInstance;
    });
    
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withPaginationType('full')
       .withOption('rowCallback', rowCallback)
       .withOption('order', [3, 'desc']);  //.withDisplayLength(2); .withDOM('pitrfl').
    	
    vm.dtColumns = [
                    DTColumnDefBuilder.newColumnDef(0).notSortable(),
                    DTColumnDefBuilder.newColumnDef(1),
                    DTColumnDefBuilder.newColumnDef(0),
                    DTColumnDefBuilder.newColumnDef(0),
                    DTColumnDefBuilder.newColumnDef(0),
                    DTColumnDefBuilder.newColumnDef(0),
                    DTColumnDefBuilder.newColumnDef(0)
                    ];
                    
	
    $scope.editingData = [];
    for (var i=0, length = vm.campaigns.length; i < length; i++) {
    	$scope.editingData[vm.campaigns[i].id] = false;
    }
    
    $scope.showRowDetails = function(campaigns) {  
    	$scope.editingData[campaigns.id] = true;  
    	var tr = $(this).closest('tr');  
    	var row = vm.dtInstance.row(tr); 
    };
    
    $scope.hideRowDetails = function(campaigns) {   
    	$scope.editingData[campaigns.id] = false;  
    };
    
    $scope.cancel = function(campaigns) {
    	$scope.editingData[campaigns.id] = false;  
    };
    
    
    
    function xclickHandler(nRow, data, backtest) {
    	//alert(row.id);
    	//$scope.editingData[row.id] = true;
    	//alert($scope.editingData[row.id]);
    	DTInstances.getLast().then(function (dtInstance) {
    		var row = dtInstance.DataTable.row($('#' +nRow.id));
    		if (row.child.isShown()) {
    			$('div.child_row_slider', row.child()).slideUp( function() {
        			row.child.hide();
        			$scope.editingData[nRow.id] = false;
    			})
    		}
    		else {
    			row.child(format(row.data(), backtest)).show();
    			$scope.editingData[nRow.id] = true;
    			$('div.child_row_slider', row.child()).slideDown();
    		}
    	})
    }
    
    function format(d, backtest) {
    	var dataHandlerFilter = $filter('dataHandler');
    	var executionHandlerFilter = $filter('executionHandler');
    	var portfolioFilter = $filter('portfolio');
    	var strategyFilter = $filter('strategy');
    	
    	return '<div class="child_row_slider"><table class="child_row" cellpadding="5" cellspacing="0" border="0">' +
    	       '<tr>' +
	           '<td>Strategy: ' + strategyFilter(backtest.strategy) + '</td>' +
	           '<td>Portfolio: ' + portfolioFilter(backtest.portfolio) + '</td>' +
	           '</tr>' +
    	       '<tr>' +
    	       '<td>Data Handler: ' + dataHandlerFilter(backtest.data_handler) + '</td>' +
    	       '<td>Execution Handler: ' + executionHandlerFilter(backtest.execution_handler) + '</td>' +
    	       '</tr>' +
    	       '</table></div>';
    }
    
    
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) { 
	    $('td', nRow).unbind('click');
	    $('td', nRow).bind('click', function () { 
	    	$scope.$apply(function() {
	    		vm.xclickHandler(nRow, aData, vm.campaigns[nRow._DT_RowIndex]);
	    	});
	    });
	    return nRow;
    }
 
    activate();


    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.CampaignsController
    */
    function activate() {   
	    if (Authentication.getAuthenticatedAccount()) 
	    	Campaigns.get(Authentication.getAuthenticatedAccount().username).then(CampaignsSuccessFn, CampaignsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    function CampaignsSuccessFn(data, status, headers, config) { 
         vm.campaigns = data.data; 
      }
    
    function CampaignsErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Campaigns could not be retrieved');
      }
    

  }
})();