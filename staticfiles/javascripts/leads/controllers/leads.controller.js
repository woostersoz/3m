/**
* LeadsController
* @namespace mmm.leads.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.leads.controllers', ['datatables'])
    .controller('LeadsController', LeadsController);
  
  LeadsController.$inject = ['$scope', 'Leads', 'Authentication', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$location', 'ngDialog', '$filter'];

  /**
  * @namespace LeadsController
  */
  function LeadsController($scope, Leads, Authentication, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $location, ngDialog, $filter) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    vm.leads = []; 
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
    for (var i=0, length = vm.leads.length; i < length; i++) {
    	$scope.editingData[vm.leads[i].id] = false;
    }
    
    $scope.showRowDetails = function(leads) {  
    	$scope.editingData[leads.id] = true;  
    	var tr = $(this).closest('tr');  
    	var row = vm.dtInstance.row(tr); 
    };
    
    $scope.hideRowDetails = function(leads) {   
    	$scope.editingData[leads.id] = false;  
    };
    
    $scope.cancel = function(leads) {
    	$scope.editingData[leads.id] = false;  
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
	    		vm.xclickHandler(nRow, aData, vm.leads[nRow._DT_RowIndex]);
	    	});
	    });
	    return nRow;
    }
 
    activate();


    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.symbols.controllers.LeadsController
    */
    function activate() {   
	    if (Authentication.getAuthenticatedAccount()) 
	    	Leads.get(Authentication.getAuthenticatedAccount().username).then(LeadsSuccessFn, LeadsErrorFn);
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
    function LeadsSuccessFn(data, status, headers, config) { 
         vm.leads = data.data; 
      }
    
    function LeadsErrorFn(data, status, headers, config) {
        // $location.url('/');
        toastr.error('Leads could not be retrieved');
      }
    

  }
})();