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
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'Social', 'Websites', 'Common', '$compile'];

	/**
	 * @namespace DashboardsController
	 */
	function DashboardsController($scope, Dashboards, Authentication, Leads,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope,  Social, Websites, Common, $compile, $interval) {

		var vm = this;
		vm.dashboards = [];
		vm.leads = [];
		$scope.parseInt = parseInt;
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.leadsPerPage = 10;
	    $scope.currentPageNumber = 1;
	    
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
		$scope.sourceNames = {'DIRECT_TRAFFIC' : 'Direct', 'EMAIL_MARKETING': 'Email', 'OFFLINE': 'Offline', 'ORGANIC_SEARCH': 'Organic', 'REFERRALS': 'Referrals', 'SOCIAL_MEDIA': 'Social', 'PAID_SEARCH': 'Paid', 'OTHER_CAMPAIGNS': 'Others', 'Unknown': 'Unknown'};
		// for form fills map
		$scope.map = false;
		 var continentProperties= {
	                "009": {
	                        name: 'Oceania',
	                        colors: [ '#CC0066', '#993366', '#990066', '#CC3399', '#CC6699' ]
	                },
	                "019": {
	                        name: 'America',
	                        colors: [ '#006699', '#336666', '#003366', '#3399CC', '#6699CC' ]
	                },
	                "150": {
	                        name: 'Europe',
	                        colors: [ '#FF0000', '#CC3333', '#990000', '#FF3333', '#FF6666' ]
	                },
	                "002": {
	                        name: 'Africa',
	                        colors: [ '#00CC00', '#339933', '#009900', '#33FF33', '#66FF66' ]
	                },
	                "142": {
	                        name: 'Asia',
	                        colors: [ '#FFCC00', '#CC9933', '#999900', '#FFCC33', '#FFCC66' ]
	                },
	        };
	        
	     // Get a country paint color from the continents array of colors
	        function getColor(country) {
	            if (!country || !country["region-code"]) {
	                return "#FFF";
	            }

	            var colors = continentProperties[country["region-code"]].colors;
	            var index = country["alpha-3"].charCodeAt(0) % colors.length ;
	            return colors[index];
	        }

	        
	        function style(feature) {
	            return {
	                fillColor: getColor($scope.countries[feature.id]),
	                weight: 2,
	                opacity: 1,
	                color: 'white',
	                dashArray: '3',
	                fillOpacity: 0.7
	            };
	        }
		 // end of form fills map
		
		$scope.groupDates = {};
		$scope.groupDates.date = {
				startDate : moment().subtract(6, "days").startOf("day"),
				endDate : moment().endOf("day")
		};
	
		getDashboards(); // get all dashboards for this company
		
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
		
		if ($state.current.name == 'dashboards-listing') {
			getDashboards();
		}
		
		if ($state.params.type == 'funnel') {
			$scope.dashboard_name = 'funnel';
		}
		else if ($state.params.type == 'social_roi') {
			$scope.dashboard_name = 'social_roi';
		}
		else if ($state.params.type == 'waterfall') {
			$scope.dashboard_name = 'waterfall';
		}
		else if ($state.params.type == 'form_fills') {
			$scope.map = true;
			$scope.dashboard_name = 'form_fills';
			angular.extend($scope, {
				center: {
					lat: 40.8741,
					lng: 14.0625,
					zoom: 2
				},
				legend: {
                    colors: [ '#CC0066', '#006699', '#FF0000', '#00CC00', '#FFCC00' ],
                    labels: [ 'Oceania', 'America', 'Europe', 'Africa', 'Asia' ]
                },
                defaults: {
                	scrollWheelZoom: false
                }
			});
			
			Common.getCountriesData().then(CountriesDataSuccessFxn, CountriesDataErrorFxn);
		}
		
		
		function getDashboards() {
	        var account = Authentication.getAuthenticatedAccount();
			if (account) {
			    Dashboards.getDashboardsByCompany(account.company)
					.then(DashboardsSuccessFn, DashboardsErrorFn);
			}
			else {
				toastr.error("You need to login first");
			}
        }
        
		function DashboardsSuccessFn(data, status, headers, config) {
			if (data.data.results.length > 0) 
			{  
				$scope.dashboards = data.data.results;
				$scope.current_dashboard = Common.findByAttr($scope.dashboards, 'name', $scope.dashboard_name);
			}
			else {
				toastr.error("Could not find dashboards for company");
			}
		}
		
		function DashboardsErrorFn(data, status, headers, config) {
			toastr.error("Could not find dashboards for company");
			return false;
		} 
		
		$scope.breadcrumbName = Common.capitalizeFirstLetter($scope.dashboard_name);
		$scope.system_type = 'MA';
		$scope.start_date = moment().subtract(30, "days").startOf("day").unix();
		$scope.end_date = moment().endOf("day").unix();
		$scope.results = {};
			//$scope.results.created_source = {'DIRECT_TRAFFIC' : 2180, 'EMAIL_MARKETING': 143, 'OFFLINE': 3782, 'ORGANIC_SEARCH': 209876, 'REFERRALS': 152432, 'SOCIAL_MEDIA': 13334445, 'PAID_SEARCH': 28976, 'OTHER_CAMPAIGNS': 5};
			
			//Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
		
		function DashboardSuccessFxn(data, status, headers, config) {
			//$scope.results = data.data;
			$scope.currentPage = {};
			$scope.currentPage.dashboardData = data.data; // these 2 lines needed to enable dashboard data in binders
			$scope.now = moment();
			if ($scope.map) // if showing a map, create markers
				createMarkers();
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
        
        function createMarkers() {
        	
        	//angular.extend($scope, {
        	$scope.markers = Dashboards.createMarkers($scope.currentPage.dashboardData.countries, $scope);
        	//$scope.layers = layers;
        	//});
        }
        
        function CountriesDataSuccessFxn(data, status, headers, config) {
        	
			$scope.countries = {};
            for (var i=0; i< data.data.length; i++) {
                var country = data.data[i];
                $scope.countries[country['alpha-3']] = country;
            }
            
            Common.getCountriesGeoData().then(CountriesGeoSuccessFxn, CountriesDataErrorFxn);	
        }
        
        function CountriesGeoSuccessFxn(data, status, headers, config) {
        	angular.extend($scope, {
                geojson: {
                    data: data.data,
                    style: style,
                    resetStyleOnMouseout: true
                },
                selectedCountry: {}
            }); 	
        }

        function CountriesDataErrorFxn(data, status, headers, config) {
        	
        	
        }
        
       
        
        $scope.$watch('groupDates.date', function(newDate, oldDate) { 
    		if (!newDate || !oldDate) return;
    		if (newDate == oldDate) return;
    		var startDate = 0;
    		var endDate = 0;
    		if ((newDate.startDate) && (newDate.endDate)
    				&& (newDate != oldDate)) {
    			startDate = moment(newDate.startDate).startOf('day').unix();
    			endDate = moment(newDate.endDate).endOf('day').unix();
    			$scope.start_date = startDate * 1000;
    			$scope.end_date = endDate * 1000;
    			
    			Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
    			
    		    
    		}
    	    }, true);
        
        function drilldown(object, section, channel, chart_name) {
        	
        	$scope.object = object;
        	$scope.section = section;
        	$scope.channel = channel;
        	$scope.chart_name = chart_name;
        	$scope.system_type = 'MA';
        	
        	if (account)
        		{
        		   $scope.filterTitle = ' for ' + Common.capitalizeFirstLetter($scope.section) + ' ' + Common.capitalizeFirstLetter($scope.object) + ' from ' + Common.capitalizeFirstLetter($scope.channel) + ' between ' + moment.unix($scope.start_date / 1000 ).format("YYYY-MM-DD") + ' and ' + moment.unix($scope.end_date / 1000).format("YYYY-MM-DD");
        		   if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
        		     Dashboards.drilldownContacts(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
        		   else if ($scope.object == 'deals' )
        			   Dashboards.drilldownDeals(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
        		}
        }
        
        function DrilldownContactsSuccessFxn(data, status, headers, config) {
        	if (data.data.results)
        	{
	        	$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				$scope.startLeadCounter = ($scope.currentPageNumber - 1) * $scope.leadsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPageNumber * $scope.leadsPerPage;
				
				vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
				vm.leads.sort(Common.sortByProperty("id"));
				$scope.showLeads = true;
				$scope.showDeals = false;
				$scope.hideDetailColumn = true;
				if ($scope.chart_name == 'form_fills')
					$scope.showFormData = true;
				else
					$scope.showFormData = false;
				
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
				$scope.startDealCounter = ($scope.currentPageNumber - 1) * $scope.leadsPerPage + 1;
			    $scope.endDealCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startDealCounter + $scope.thisSetCount -1 : $scope.currentPageNumber * $scope.leadsPerPage;
				
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
			$scope.currentPageNumber = newPage;
			if (account)
    		{
    		   if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
    			   Dashboards.drilldownContacts(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
    		   else if ($scope.object == 'deals' )
    			   Dashboards.drilldownDeals(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
    		}
	    }

	}
})();