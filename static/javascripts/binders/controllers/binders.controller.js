/**
 * BindersController
 * 
 * @namespace mmm.binders.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.binders.controllers', [ 'datatables', 'mmm.analytics.services', 'mmm.dashboards.services' ]).controller(
			'BindersController', BindersController);

	BindersController.$inject = [ '$scope', 'Binders', 'Dashboards', 'Authentication', 'Analytics', 'BinderPage', 'Common', 'Fullscreen', 'Sticky', 'AnalyticsCharts', '$filter', '$state', '$stateParams', '$document', '$window', '$sce', '$location', 'DTOptionsBuilder', 'DTColumnDefBuilder',
			'DTColumnBuilder', 'DTInstances',  '$q', '$compile'];

	/**
	 * @namespace BindersController
	 */
	function BindersController($scope, Binders, Dashboards, Authentication, Analytics, BinderPage, Common, Fullscreen, Sticky, AnalyticsCharts, $filter, $state, $stateParams, $document, $window, $sce, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $q, $compile,  $interval) {
		
		var vm = this;
		
		// vm.isAuthenticated = Authentication.isAuthenticated();
		vm.binders = [];
		$scope.showBinder = showBinder;
		$scope.goBackToList = goBackToList;
		$scope.listMode = true;
		$scope.binderDate = '';
		$scope.orientations = ['Portrait', 'Landscape'];
		$scope.frequencies = ['One Time', 'Daily', 'Weekly', 'Monthly'];
		$scope.newBinder = {};
		$scope.pages = [];
		$scope.currentPage = {};
		$scope.createBinder = false;
		$scope.createBinderPage = createBinderPage;
		$scope.contentTitleHtml = {};
		$scope.charts = [];
		$scope.dashboards = [];
		$scope.getBinderTemplates = getBinderTemplates;
		$scope.saveBinderTemplate = saveBinderTemplate;
		$scope.getBinders = getBinders;
		$scope.showBinderFxn = showBinderFxn;
		$scope.binders = [];
    	$scope.showBinders = false;
    	$scope.showBinder = false;
    	$scope.notes = [];
    	$scope.createNote = createNote;
		$scope.deleteNote = deleteNote;
		$scope.goFullscreen = goFullscreen;
		$scope.toggleFullscreen = toggleFullscreen;
		$scope.goSlideBack = goSlideBack;
		$scope.goSlideForward = goSlideForward;
		$scope.isFullscreen = false;
		$scope.slidePosition = 0;
		$scope.noMoreForward = false;
		$scope.noMoreBack = false;
		$scope.hideTimeFilterOnTop = true;
		$scope.convertPagesToPdf = convertPagesToPdf;
		$scope.parentObj.preview = false;
		$scope.pdfRendered = false;
		$scope.escapeHit = function($event) {
			if ($event.keyCode == 27)
			{
			   $scope.isFullscreen = false;
			   console.log('Esc hit');
			}
		}
		$scope.groupDates = {};
		$scope.groupDates.date = {
				startDate : moment().subtract(6, "days").startOf("day"),
				endDate : moment().endOf("day")
		};
		
		$scope.stageNames = {'marketingqualifiedlead' : 'MQL', 'salesqualifiedlead' : 'SQL', 'customer' : 'Customer', 'subscriber' : 'Subscriber', 'lead' : 'Lead', 'opportunity' : 'Opportunity'};
		$scope.sourceNames = {'DIRECT_TRAFFIC' : 'Direct', 'EMAIL_MARKETING': 'Email', 'OFFLINE': 'Offline', 'ORGANIC_SEARCH': 'Organic', 'REFERRALS': 'Referrals', 'SOCIAL_MEDIA': 'Social', 'PAID_SEARCH': 'Paid', 'OTHER_CAMPAIGNS': 'Others', 'Unknown': 'Unknown'};

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
		
		$scope.$watch('currentPage.chartFilters.groupDates.date', function(newDate, oldDate) { 
			if (!newDate || !oldDate) return;
			if (newDate == oldDate) return;
			var startDate = 0;
			var endDate = 0;
			if ((newDate.startDate) && (newDate.endDate)
					&& (newDate != oldDate)) {
				startDate = moment(newDate.startDate).startOf('day');
				endDate = moment(newDate.endDate).endOf('day');
				$scope.currentPage.chartFilters.groupDates.date.startDate = startDate;
				$scope.currentPage.chartFilters.groupDates.date.endDate = endDate;
			}
		});
		
		$scope.opts = {
				ranges : {
					'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
					'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
					'This Month' : [ moment().startOf("month"),
					                 moment().endOf("day") ]
				}
		};
		
		
		$scope.createBinderFxn = function() {
			$scope.createBinder = true;
			createBinderPage('text');
			if ($scope.charts.length == 0)
				getCharts();
			if ($scope.dashboards.length == 0)
				getDashboards();
		}
		
		function createBinderPage(typeX) { 
			 var newPage = BinderPage.createBinderPage(typeX); 
			 newPage.position = $scope.pages.length + 1;
		     $scope.pages.push(newPage);
		     $scope.pages = BinderPage.handleSelectedBinderPage($scope.pages, newPage.id);
		     $scope.currentPage = newPage;
		     //changeContentHtml(newPage.contentTitle);
	    }
		
		$scope.deleteBinderPage = function(id) { 
			$scope.pages = BinderPage.handleDeletedBinderPage($scope.pages, id);
			$scope.currentPage = {};
			//changeContentHtml('');
		}
		
		$scope.showPageContent = function(page) { 
			$scope.pages = BinderPage.handleSelectedBinderPage($scope.pages, page.id);
			$scope.currentPage = page;
			if (page.type == 'dashboard')
			{
				$scope.results = page.dashboardData;
				$scope.pageUrl = staticUrl("templates/dashboards/") + page.dashboardType.template + ".html";
				
			}
			//changeContentHtml(page.contentTitle);
		}
		
		function goSlideForward() { console.log('pos is ' + $scope.slidePosition + ' and length is ' + $scope.pages.length);
			if ($scope.slidePosition < $scope.pages.length)
			{
				$scope.showPageContent($scope.pages[$scope.slidePosition]);
				$scope.slidePosition+=1;
			}
			checkSlideButtons();
		}
		
		function goSlideBack() { console.log('pos is ' + $scope.slidePosition + ' and length is ' + $scope.pages.length);
			if ($scope.slidePosition > 0)
			{
				if ($scope.slidePosition > 1)
				   $scope.slidePosition-=1;
				$scope.showPageContent($scope.pages[$scope.slidePosition - 1]);
			}
			checkSlideButtons();
		}
		
		$scope.cancelBinderTemplate = cancelBinderTemplate;
		
		function cancelBinderTemplate(form) {
			$scope.createBinder = false;
			$scope.showBinder = false;
			$scope.showBinders = false;
			$scope.newBinder = {};
			$scope.pages = [];
			$scope.currentPage = {};
			if (form)
			{
			  form.$setPristine();
			  form.$setUntouched();
			}
		}
		
		var current_url = $state.href($state.current.name);
		
		if (current_url.substring(0, 11) == '/pdf/binder') // if PDF preview dont show navbar and side menu
		   $scope.parentObj.preview = true;
		
		$scope.$watch('parentObj.preview', function(newVal, oldVal) { 
			if (current_url.substring(0, 11) != '/pdf/binder') return;
			if ($scope.pdfRendered) return;
	    	  var binder_id = current_url.substring(12, current_url.length);
	    	  var account = Authentication.getAuthenticatedAccount();
			  if (account) {
				$scope.pdfRendered = true;
			   	Binders.getSingleBinder(account.company, binder_id).then(GetSingleBinderSuccessFn, GetSingleBinderErrorFn);
		      }  
		});
		
		if ($state.href($state.current.name) == '/binders')
	    {
	    	getBinderTemplates();
	    }
		else if ($state.current.name == 'binder-new')
	    {
			$scope.createBinderFxn();
	    }
		else if ($state.current.name == 'binders-list')
		{
			if ($stateParams.template)
				$scope.templateId = $stateParams.template;
			getBinders($scope.templateId);
		}
		else if ($state.current.name == 'binder-show')
		{
			if (!$stateParams.binderId)
				toastr.error('Unable to get binder');
			if ($stateParams.binder != null)
			    showBinderFxn($stateParams.binder);
			else
				{
				var account = Authentication.getAuthenticatedAccount();
				Binders.getSingleBinder(account.company, $stateParams.binderId).then(GetSingleBinderSuccessFn, GetSingleBinderErrorFn);
				}
			$scope.breadcrumbName = $stateParams.binderId;
		}
		
		
		
		function GetSingleBinderSuccessFn(data, status, headers, config) {  
	    	if (data.data.results.length > 0) {
	    		var binder = data.data.results[0]; // has to be the first element of the results array
	    		showBinderFxn(binder);
	    	}
	    	else if (!data.data.results || data.data.results.length == 0) {
	    		toastr.error('Could not retrieve binder for preview');
	    	}
	    	
	    }
		
		function GetSingleBinderErrorFn(data, status, headers, config) {  
	    	if (!data.data.results || data.data.results.length == 0) {
	    		toastr.error('Could not retrieve binder for preview');
	    	}
	    }
	
	
		
		
		function goBackToList() {
			$scope.listMode = true;
		}
		
		function fillBinder(html) {
			angular.element(document.querySelector('#binder')).html(html);
			angular.element(document.querySelector('#binder')).find('input, textarea, button, select').attr('disabled', true);
			angular.element(document.querySelector('#binder')).find('button').hide();
		}
		
		function getBinderTemplates() {   
			var account = Authentication.getAuthenticatedAccount();
		    if (account) {
		    	Binders.getAllBinderTemplates(account.company).then(GetBindersSuccessFn, GetBindersErrorFn);
		    	cancelBinderTemplate(null);
		    }
	    }
	    
	    function GetBindersSuccessFn(data, status, headers, config) {  
	    	if (data.data.results)
		       $scope.binderTemplates = data.data.results;
	    	   $scope.templateCount = data.data.templateCount;
	    	   $scope.binderCount = data.data.binderCount;
	    	   $scope.templateLastCreated = data.data.templateLastCreated;
	    	   $scope.binderLastCreated = data.data.binderLastCreated;
		}
	    
        function GetBindersErrorFn(data, status, headers, config) { 
		    
		}
        
        function showBinder(binder_id) {
        	var account = Authentication.getAuthenticatedAccount();
		    if (account) {
        	    Binders.get(account.company, binder_id).then(GetBinderSuccessFn, GetBinderErrorFn);
		    }
		}
        
        function GetBinderSuccessFn(data, status, headers, config) {  
		    if (data.data.results) {
		    	$scope.binders = data.data.results;
		    	$scope.showBinders = true;
		    }
		}
	    
        function GetBinderErrorFn(data, status, headers, config) { 
        	toastr.error("Could not get binders");
		}
        
        function saveBinderTemplate(form) {
        	var account = Authentication.getAuthenticatedAccount();
		    if (account) {
		    	$scope.newBinder.pages = $scope.pages
		    	Binders.saveBinderTemplate(account.company, $scope.newBinder).then(binderTemplateSaveSuccessFxn, binderTemplateSaveErrorFxn);
		    	cancelBinderTemplate(form);
		    }
        }
        
        function binderTemplateSaveSuccessFxn(data, status, headers, config) { 
		    if (data.data.results)
		    {
		    	$scope.binderTemplates = data.data.results;
		    	toastr.success("Binder template saved");
		    	$location.path('/binders');
		    }
		   
		}
        
        function binderTemplateSaveErrorFxn(data, status, headers, config) { 
        	toastr.error("Binder template could not be saved");
		}
        
        function getBinders(templateId) {
        	var account = Authentication.getAuthenticatedAccount();
		    if (account) {
		    	Binders.getBinders(account.company, templateId).then(GetBinderSuccessFn, GetBinderErrorFn);
		    }
        }
        
        function showBinderFxn(binder) {
        	var account = Authentication.getAuthenticatedAccount();
        	cancelBinderTemplate(null);
        	$scope.newBinder = binder;
        	$scope.requests = [];
        	$scope.requests2 = [];
            
        	for (var i=0; i < binder.pages.length; i++) {
        		
        		var page = binder.pages[i];
        		
        		if (page.type == 'text')
        			$scope.pages.push(page); // that's all that's needed for Text pages
        		else if (page.type == 'chart') // the fun begins
        		{
        			try {
	        			if (page.chartType.name && page.chartFilters.groupDates)
	        			{
		        			var startDate = moment(page.chartFilters.groupDates.date.startDate).unix() * 1000;
		        			var endDate = moment(page.chartFilters.groupDates.date.endDate).unix() * 1000;
		        			$scope.requests.push({"name": page.chartType.name, "startDate": startDate, "endDate": endDate, "systemType": page.chartType.system_type});
	        			}
        			}
        			catch(e) {}
        			$scope.pages.push(page); 
        			
        		} // end of if page.type == chart
        		else if (page.type == 'dashboard')
        		{
        			try {
	        			if (page.dashboardType.name && page.chartFilters.groupDates)
	        			{
		        			var startDate = moment(page.chartFilters.groupDates.date.startDate).unix() * 1000;
		        			var endDate = moment(page.chartFilters.groupDates.date.endDate).unix() * 1000;
		        			$scope.requests2.push({"name": page.dashboardType.name, "startDate": startDate, "endDate": endDate, "systemType": page.dashboardType.system_type});
	        			}
        			}
        			catch(e) {}
        			$scope.pages.push(page); 
        			
        		} // end of if page.type == dashboard
        	} // end of pages loop
        	
        	$q.all($scope.requests.map(function(request) {
        		return Analytics.retrieveChart(account.company, request.name, request.startDate, request.endDate, request.systemType);
        	})).then(function(results){
        		var resultsPosition = 0;
        		var scope_options = AnalyticsCharts.getScopeOptions($scope);
        		$scope = scope_options['scope'];
        		for (var i=0; i < $scope.pages.length; i++)
        		{
        			$scope.pages[i].content = '';
        			var chartData = null;
        			try {
	        			if ($scope.pages[i].type == 'chart' && $scope.pages[i].chartType.name && $scope.pages[i].chartFilters.groupDates)
	        			{
	        				//if ($scope.pages[i].chartType.name == "sources_bar"  || $scope.pages[i].chartType.name == "website_traffic"  || $scope.pages[i].chartType.name == "tw_performance") {
	        				if ($scope.pages[i].chartType.chart_type == 'multibar') {	
	        				        chartData = results[resultsPosition].data.map(function(d) {
	        						d.values = d.values.sort(AnalyticsCharts.natcmp);
	        						return d;
	        					});
	        				}
	        				else if ($scope.pages[i].chartType.name == "pipeline_duration") {
	        					chartData = results[resultsPosition].data.results;
	        					$scope.statuses = results[resultsPosition].data.statuses;
	        				}
	        				else
	        					chartData = results[resultsPosition].data;
	        				
	        			    $scope.pages[i].chartData = chartData;	
	        			    resultsPosition++;
	        			    
	        			    $scope.pages[i].chartOptions = scope_options[$scope.pages[i].chartType.name];
	        			}
        			}
        			catch(e) {}
        		}
        		
        		if ($scope.pages.length > 0)
            	{
            	   $scope.currentPage = $scope.pages[0];
            	   BinderPage.handleSelectedBinderPage($scope.pages, $scope.pages[0].id);
            	}
            	
 
        	});
        	
        	$q.all($scope.requests2.map(function(request) {
        		return Dashboards.retrieveDashboard(account.company, request.name, request.startDate, request.endDate, request.systemType);
        	})).then(function(results){
        		var resultsPosition = 0;
        		for (var i=0; i < $scope.pages.length; i++)
        		{
        			$scope.pages[i].content = '';
        			var dashboardData = null;
        			try {
	        			if ($scope.pages[i].type == 'dashboard' && $scope.pages[i].dashboardType.name && $scope.pages[i].chartFilters.groupDates)
	        			{
	        				dashboardData = results[resultsPosition].data;
	        				var dashboardType = $scope.pages[i].dashboardType;
	        				dashboardType['pageUrl'] = staticUrl("templates/dashboards/") + $scope.pages[i].dashboardType.template + ".html";
	        				$scope.pages[i].dashboardType = dashboardType;
	        				$scope.pages[i].dashboardData = dashboardData;	
	        				if ($scope.pages[i].dashboardType.name == 'form_fills')
	        				// if showing a map, create markers and fill other scope variables
	        				{
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
	        					createMarkers($scope.pages[i].dashboardData.countries);
	        				}
	        			    resultsPosition++;
	        			    
	        			}
        			}
        			catch(e) {}
        		}
        		
        		if ($scope.pages.length > 0)
            	{
            	   $scope.currentPage = $scope.pages[0];
            	   BinderPage.handleSelectedBinderPage($scope.pages, $scope.pages[0].id);
            	}
            	
 
        	});
        	
        	$scope.showBinder = true;
        }
        
        function getCharts() {
	        var account = Authentication.getAuthenticatedAccount();
			if (account) {
			    Analytics.getChartsByCompany(account.company)
					.then(ChartsSuccessFn, ChartsErrorFn);
			}
			else {
				toastr.error("You need to login first");
			}
        }
        
		function ChartsSuccessFn(data, status, headers, config) {
			if (data.data.results.length > 0) 
			{  
				$scope.charts = data.data.results;
				for (var i=0; i < $scope.charts.length; i++)
					$scope.charts[i].src = staticUrl($scope.charts[i].src);
			}
			else {
				toastr.error("Could not find charts for company");
			}
		}
		
		function ChartsErrorFn(data, status, headers, config) {
			toastr.error("Could not find charts for company");
			return false;
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
			}
			else {
				toastr.error("Could not find dashboards for company");
			}
		}
		
		function DashboardsErrorFn(data, status, headers, config) {
			toastr.error("Could not find dashboards for company");
			return false;
		} 
        
        function changeContentHtml(title) {
        	/*html = '<a href="#" editable-text="page.contentTitle">' + title + '</a>';
        	angular.element("#content-body").html(html);*/
			//$compile(angular.element("#content-body"))($scope);
        }
        
        function createNote() {
        	if (!$scope.currentPage.notes)
        		$scope.currentPage.notes = [];
			$scope.currentPage.notes.push(Sticky.createNote());
		}

		function deleteNote(id) {
			$scope.currentPage.notes = Sticky.handleDeletedNote($scope.currentPage.notes, id);
		}
		
		function goFullscreen() {
			if (Fullscreen.isEnabled())
				Fullscreen.cancel();
			else
				Fullscreen.all();
		}
		
		function toggleFullscreen() {
			$scope.isFullscreen = false; 
			$scope.isFullscreen = true; //!$scope.isFullscreen;
			$scope.slidePosition = $scope.currentPage.position;
			checkSlideButtons();
			console.log('slide pos is ' + $scope.slidePosition);
		}
		
		function checkSlideButtons() {
			if ($scope.slidePosition == $scope.pages.length)
			    $scope.noMoreForward = true;
			else
				$scope.noMoreForward = false;
			if ($scope.slidePosition == 1)
			    $scope.noMoreBack = true;
			else
				$scope.noMoreBack = false;
		}
		
		function convertPagesToPdf() {
			/*var pagesHtml = [];
			for (var i=0; i < $scope.pages.length; i++)
			{
				//$scope.currentPage = $scope.pages[i];
				$scope.$apply(function() {
					$scope.showPageContent($scope.pages[i]);
				});
				
				var id = $scope.pages[i].id + '-content';
				console.log('id is ' + id);
				//$compile(document.body)($scope);
				var divElement = angular.element(document.body).find('#' + id);
				var html = divElement.html();
				pagesHtml.push(html);
				//console.log(html);
			
			}*/
			var account = Authentication.getAuthenticatedAccount();
			if (account) {
			   Common.exportToPdf(account.company, "binder", $scope.newBinder.id, encodeURIComponent($scope.newBinder.binder_template.name), 'binder').then(ExportToPdfSuccessFxn, ExportToPdfErrorFxn);
		    }
        }
        
        function ExportToPdfSuccessFxn(data, status, headers, config) { 
        	if (data.data.Error)
        		toastr.error(data.data.Error);
        	else
        	    toastr.info('Export is scheduled. Check My Exports for details');
        	/*var anchor = angular.element('<a>');
        	var file = new Blob([data.data], { type: 'application/pdf'});
        	var fileURL = URL.createObjectURL(file);
        	console.log(fileURL);
        	var trustedURL = $sce.trustAsResourceUrl(fileURL);
        	console.log(trustedURL);
        	
        	anchor.attr({
        		href: trustedURL,
        		download: 'binder.pdf'
        	})[0].click();
        	
			toastr.success('Exported to PDF');*/
		}
        
        function ExportToPdfErrorFxn(data, status, headers, config) { 
        	toastr.error('Export to PDF could not be scheduled');
		}
		
		function readHtmlLoop(i) {
			setTimeout(function() {
				  $scope.currentPage = $scope.pages[i];
				  var id = $scope.pages[i].id + '-content';
				  console.log('id is ' + id);
				  console.log('current page id is ' + $scope.currentPage.id);
				  var html = angular.element('#' + id).html();
				  i++;
				  console.log(html);
				  if (i < $scope.pages.length - 1)
					  readHtmlLoop(i);
				  }, 100);
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
        
        function createMarkers(countries) {
        	
        	//angular.extend($scope, {
        	$scope.markers = Dashboards.createMarkers(countries, $scope);
        	//$scope.layers = layers;
        	//});
        }
	    
	}
})();