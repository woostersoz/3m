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
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'Social', 'Websites', 'Common'];

	/**
	 * @namespace DashboardsController
	 */
	function DashboardsController($scope, Dashboards, Authentication, Leads,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope,  Social, Websites, Common, $interval) {

		var vm = this;
		vm.dashboards = [];
		vm.leads = [];
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.leadsPerPage = 10;
	    $scope.currentPage = 1;
	    
	    vm.deals = [];
		$scope.deals = [];
	    $scope.totalDeals = 0;
	
		$scope.notes = [];
		//$scope.createNote = createNote;
		//$scope.deleteNote = deleteNote;
		//$scope.handleDeletedNote = Sticky.handleDeletedNote;
		$scope.showLeads = false;
		$scope.showDeals = false;
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
		
		$scope.dashboardFunnelUrl = staticUrl('images/dashboard-funnel.png');
		$scope.drilldown = drilldown;
		
		$scope.portal_id = '';
		$scope.source_system = ''; 
		
		$scope.object = '';
    	$scope.section = '';
    	$scope.channel = '';
		
		$scope.dashboard_name = '';
		$scope.system_type = '';
		$scope.start_date = '';
		$scope.end_date = '';
		$scope.stageNames = {};
		$scope.stageNames = {'marketingqualifiedlead' : 'MQL', 'salesqualifiedlead' : 'SQL', 'customer' : 'Customer', 'subscriber' : 'Subscriber', 'lead' : 'Lead', 'opportunity' : 'Opportunity'};
		$scope.sourceNames = {'DIRECT_TRAFFIC' : 'Direct', 'EMAIL_MARKETING': 'Email', 'OFFLINE': 'Offline', 'ORGANIC_SEARCH': 'Organic', 'REFERRALS': 'Referrals', 'SOCIAL_MEDIA': 'Social', 'PAID_SEARCH': 'Paid', 'OTHER_CAMPAIGNS': 'Others'};
		
		$scope.groupDates = {};
		$scope.groupDates.date = {
				startDate : moment().subtract(6, "days").startOf("day"),
				endDate : moment().endOf("day")
		};
	
		
		$scope.startDate = $scope.groupDates.date.startDate;
		$scope.endDate = $scope.groupDates.date.endDate;
		$scope.opts = {
				ranges : {
					'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
					'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
					'This Month' : [ moment().startOf("month"),
					                 moment().endOf("day") ]
				},
				opens: 'left'
		};

		var account = Authentication.getAuthenticatedAccount();
		if (!account) {
			toastr.error('You need to login first');
			$location.url = '/login';
		}
		
		if ($state.params.type == 'funnel') {
			$scope.dashboard_name = 'funnel';
			$scope.system_type = 'MA';
			$scope.start_date = moment().subtract(30, "days").startOf("day").unix();
			$scope.end_date = moment().endOf("day").unix();
			$scope.results = {};
			$scope.results.created_source = {'DIRECT_TRAFFIC' : 2180, 'EMAIL_MARKETING': 143, 'OFFLINE': 3782, 'ORGANIC_SEARCH': 209876, 'REFERRALS': 152432, 'SOCIAL_MEDIA': 13334445, 'PAID_SEARCH': 28976, 'OTHER_CAMPAIGNS': 5};
			
			//Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
		}
		
		if ($state.params.type == 'social') {
			$scope.dashboard_name = 'social';
			$scope.system_type = 'MA';
			$scope.start_date = moment().subtract(90, "days").startOf("day").unix();
			$scope.end_date = moment().endOf("day").unix();
			Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
		}
		
		function DashboardSuccessFxn(data, status, headers, config) {
			$scope.results = data.data;
			$scope.now = moment();
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
        
        $scope.$watch('groupDates.date', function(newDate, oldDate) { 
    		if (!newDate || !oldDate) return;
    		var startDate = 0;
    		var endDate = 0;
    		if ((newDate.startDate) && (newDate.endDate)
    				&& (newDate != oldDate)) {
    			startDate = moment(newDate.startDate).startOf('day').unix();
    			endDate = moment(newDate.endDate).endOf('day').unix();
    			$scope.start_date = startDate;
    			$scope.end_date = endDate;
    			
    			Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
    			
    		    
    		}
    	    }, true);
        
        function drilldown(object, section, channel) {
        	
        	$scope.object = object;
        	$scope.section = section;
        	$scope.channel = channel;
        	$scope.system_type = 'MA';
        	
        	if (account)
        		{
        		   $scope.filterTitle = ' for ' + Common.capitalizeFirstLetter($scope.section) + ' ' + Common.capitalizeFirstLetter($scope.object) + ' from ' + Common.capitalizeFirstLetter($scope.channel) + ' between ' + moment.unix($scope.start_date).format("YYYY-MM-DD") + ' and ' + moment.unix($scope.end_date).format("YYYY-MM-DD");
        		   if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
        		     Dashboards.drilldownContacts(account.company, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPage, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
        		   else if ($scope.object == 'deals' )
        			   Dashboards.drilldownDeals(account.company, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPage, $scope.leadsPerPage).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
        		}
        }
        
        function DrilldownContactsSuccessFxn(data, status, headers, config) {
        	if (data.data.results)
        	{
	        	$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
				
				vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
				$scope.showLeads = true;
				$scope.showDeals = false;
				$scope.hideDetailColumn = true;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
					
				}
				
				$timeout(function() {
					$location.hash('leaddrilldown');
					$anchorScroll();
				}, 0);
        	}
        	else {
        		toastr.error('Could not retrieve drilldown');
        	}
		}
        
        function DrilldownDealsSuccessFxn(data, status, headers, config) {
        	if (data.data.results)
        	{
        		$scope.totalDeals = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				$scope.startDealCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endDealCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startDealCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
				
				//vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
			    vm.deals = data.data.results;
				$scope.showDeals = true;
				$scope.showLeads = false;
				$scope.hideDetailColumn = true;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
					
				}
				
				$timeout(function() {
					$location.hash('dealdrilldown');
					$anchorScroll();
				}, 0);
        	}
        	else {
        		toastr.error('Could not retrieve drilldown');
        	}
        }
        
        function DrilldownErrorFxn(data, status, headers, config) {
			toastr.error('Could not retrieve drilldown');
		}
        
        $scope.pageChanged = function(newPage) {
			$scope.currentPage = newPage;
			if (account)
    		{
    		   if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
    			   Dashboards.drilldownContacts(account.company, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPage, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
    		   else if ($scope.object == 'deals' )
    			   Dashboards.drilldownDeals(account.company, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPage, $scope.leadsPerPage).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
    		}
	    }

	}
})();