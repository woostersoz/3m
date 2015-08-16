/**
 * DashboardsController
 * 
 * @namespace mmm.dashboards.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.dashboards.controllers', [ 'datatables' ]).controller(
			'DashboardsController', DashboardsController);

	DashboardsController.$inject = [ '$scope', 'Dashboards', 'Authentication',
	                                'Leads', 'Snapshots', '$location', 'DTOptionsBuilder',
	                                'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter',
	                                '$state', '$stateParams', '$document', '$window', 'Sticky',
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'Social', 'Websites'];

	/**
	 * @namespace DashboardsController
	 */
	function DashboardsController($scope, Dashboards, Authentication, Leads,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope,  Social, Websites, $interval) {

		var vm = this;
		vm.dashboards = [];
		vm.leads = [];
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.leadsPerPage = 10;
	    $scope.currentPage = 1;
	
		$scope.notes = [];
		//$scope.createNote = createNote;
		//$scope.deleteNote = deleteNote;
		//$scope.handleDeletedNote = Sticky.handleDeletedNote;
		$scope.showLeads = false;
		$scope.showLeadsDuration = false;
		$scope.showTweets = false;
		$scope.showWebsiteVisitors = false;
		$scope.showCarousel = true;
		$scope.showChart = false;
		$scope.notFirstChart = false; // this is set to false only when page is loaded else always true
		
		$scope.data = [];
		$scope.strict = false;
		$scope.chartName = '';
		$scope.chartType = '';
		$scope.startDate = '';
		$scope.endDate = '';
		/*$scope.snapshot = snapshot;
		$scope.staticUrl = staticUrl;
		$scope.drawChart = drawChart;
		$scope.postToChannel = postToChannel;*/
		$scope.barUrl = staticUrl('images/dashboards-bar.png');
		$scope.lineUrl = staticUrl('images/dashboards-line.png');
		$scope.rowUrl = staticUrl('images/dashboards-row.png');
		$scope.pieUrl = staticUrl('images/dashboards-pie.png');
		
		$scope.dashboard_name = '';
		$scope.system_type = '';
		$scope.start_date = '';
		$scope.end_date = '';
		$scope.stageNames = {};
		$scope.stageNames = {'marketingqualifiedlead' : 'MQL', 'salesqualifiedlead' : 'SQL', 'customer' : 'Customer', 'subscriber' : 'Subscriber', 'lead' : 'Lead', 'opportunity' : 'Opportunity'};
		$scope.sourceNames = {'DIRECT_TRAFFIC' : 'Direct', 'EMAIL_MARKETING': 'Email Campaign', 'OFFLINE': 'Offline', 'PAID': 'Paid'};
			
		var account = Authentication.getAuthenticatedAccount();
		if (!account) {
			toastr.error('You need to login first');
			$location.url = '/login';
		}
		
		if ($state.params.type == 'funnel') {
			$scope.dashboard_name = 'funnel';
			$scope.system_type = 'MA';
			$scope.start_date = moment().subtract(90, "days").startOf("day").unix();
			$scope.end_date = moment().endOf("day").unix();
			Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
		}
		
		function DashboardSuccessFxn(data, status, headers, config) {
			$scope.results = data.data;
			/*$scope.start_date = $scope.results['start_date'];
			$scope.end_date = $scope.results['end_date'];
			$scope.created_source = $scope.results['created_source'];
			$scope.created_stage = $scope.results['created_stage'];
			$scope.existed_source = $scope.results['existed_source'];
			$scope.existed_stage = $scope.results['existed_stage'];*/
			
		}
		
        function DashboardErrorFxn(data, status, headers, config) {
			toastr.error('Could not retrieve dashboard');
		}

	}
})();