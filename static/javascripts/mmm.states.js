(function() {
	'use strict';

	angular.module('mmm.states').config(config);

	config.$inject = [ '$urlRouterProvider', '$stateProvider' ];
	
	/**
	 * @name config
	 * @desc Define valid application routes
	 */
	function config($urlRouterProvider, $stateProvider) {
		$stateProvider
		        .state(
				'pdf',
				{
					url : '/pdf/:object/:id',
					controller : 'BindersController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/binder-pdf.html' /*function ($stateParams) {
						if ($stateParams.object == 'binder')
							return '/static/templates/analytics/binder-pdf.html';
					}*/
				})
				.state(
				'screenshot',
				{
					url : '/capture?url',
					controller : 'BindersController',
					controllerAs : 'vm'
					//templateUrl : '/static/templates/analytics/binder-pdf.html'
				})
				.state('dashboards-listing', {
					url : '/dashboards',
					controller : 'DashboardsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/dashboards/dashboards-listing.html',
					ncyBreadcrumb: {
				    	label: 'Dashboards'
				    }
				})	
				.state('showdashboard', {
					url : '/dashboards/:name',
					controller : 'DashboardsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/dashboards/dashboard.html',
					ncyBreadcrumb: {
				    	label: '{{ current_dashboard.title }}',
				    	parent: 'dashboards-listing'
				    }
				})
				/*.state('dashboards', {
					url : '/dashboards/:type',
					controller : 'DashboardsController',
					controllerAs : 'vm',
					templateUrl : function ($stateParams) {
						var constUrl = '/static/templates/dashboards/';
						if ($stateParams.type == 'funnel')
							return constUrl + 'dashboard-funnel.html';
						else if ($stateParams.type == 'social_roi')
							return constUrl + 'dashboard-social.html';
						else if ($stateParams.type == 'waterfall')
							return constUrl + 'dashboard-waterfall.html';
						else if ($stateParams.type == 'form_fills')
							return constUrl + 'dashboard-forms.html';
						else if ($stateParams.type == 'opp_funnel')
							return constUrl + 'dashboard-opp-funnel.html';
					},
				    ncyBreadcrumb: {
				    	label: '{{ current_dashboard.title }}',
				    	parent: 'dashboards-listing'
				    }
				})*/
				.state('analytics', { //deprecated
					url : '',
					redirectTo: 'charts',
				    ncyBreadcrumb: {
				    	label: 'Analytics',
				    }
				})
				.state('charts-listing', {
					url : '/charts',
					controller : 'AnalyticsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/analytics-listing.html',
				    ncyBreadcrumb: {
				    	label: 'Charts'
				    }
				})
				.state('showchart', {
					url : '/charts/:url',
					controller : 'AnalyticsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/analytics-chart.html',
					ncyBreadcrumb: {
				    	label: '{{ chartTitle }}',
				    	parent: 'charts-listing'
				    }
				})
				.state('views-listing', {
					url : '/views',
					controller : 'ViewsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/views/views-listing.html',
					ncyBreadcrumb: {
				    	label: 'Views'
				    }
				})	
				.state('showview', {
					url : '/views/:name',
					controller : 'ViewsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/views/view.html',
					ncyBreadcrumb: {
				    	label: '{{ viewTitle }}',
				    	parent: 'views-listing'
				    }
				})
				.state('utils', {  
					url : '',
				    ncyBreadcrumb: {
				    	label: 'Helpful Stuff',
				    }
				})
		        .state(
				'fbok-test',
				{
					url : '/fbok-test',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html'
				})
				.state(
				'goog-test',
				{
					url : '/goog-test',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html'
				})
				.state(
				'superadmin-jobs',
				{
					url : '/superadmin-jobs',
					controller : 'SuperadminController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/superadmin/superadmin-jobs.html'
				})
				.state(
				'superadmin-logs',
				{
					url : '/superadmin-logs',
					controller : 'SuperadminController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/superadmin/superadmin-logs.html'
				})
				.state(
				'mongonaut',
				{
					url : '/mongonaut',
					controller : 'SuperadminController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/superadmin/superadmin-mongonaut.html'
				})
				.state(
				'mongonaut-other',
				{
					url : '/mongonaut/*path',
					controller : 'SuperadminController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/superadmin/superadmin-mongonaut.html'
				})
				.state(
				'admin',
				{
					url : '/admin',
					//controller : 'RegisterController',
					//controllerAs : 'vm',
					templateUrl : '/templates/admin/index.html',
					ncyBreadcrumb: {
				    	label: 'Admin'
				    }
				})
				.state(
					'register',
					{
						url : '/register',
						controller : 'RegisterController',
						controllerAs : 'vm',
						templateUrl : '/static/templates/authentication/register.html'
					})
				.state('login', {
					url : '/login',
					controller : 'LoginController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/authentication/login.html'
				})
				.state('login:query', {
					url : '/login:query',
					controller : 'LoginController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/authentication/login.html'
				})
				.state('users/login', {
					url : '/users/login',
					controller : 'LoginController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/authentication/login.html'
				})
				.state('users', {
					url : '/users',
					controller : 'RegisterController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/authentication/users.html',
					ncyBreadcrumb: {
				    	label: 'Users',
				    	parent: 'admin'
				    }
				})
				.state('profile', {
					url : '/users/:id',
					//params: {id:null},
					controller : 'ProfileController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/profiles/profile.html',
					ncyBreadcrumb: {
				    	label: '{{ profile.username }}',
				    	parent: 'users'
				    }
				})
				.state('profile_settings', {
					url : '/users/:id/settings',
					controller : 'ProfileSettingsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/profiles/settings.html',
					ncyBreadcrumb: {
				    	label: 'Settings',
				    	parent: 'profile'
				    }
				})
				.state('contacts', {
					url : '/contacts',
					controller : 'LeadsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/leads/leads.html',
					ncyBreadcrumb: {
				    	label: 'Contacts'
				    }
				})
				.state('contacts-code', {
					url : '/contacts/:code',
					controller : 'LeadsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/index.html'
				})
				.state('name', {
					url : '/name',
					controller : 'AccountsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/accounts/accounts.html'
				})
				.state('accounts', {
					url : '/accounts',
					controller : 'AccountsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/accounts/accounts.html',
					ncyBreadcrumb: {
				    	label: 'Accounts'
				    }
				})
				.state('companies', {
					url : '/companies',
					controller : 'AccountsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/accounts/accounts-companies.html',
					ncyBreadcrumb: {
				    	label: 'Companies'
				    }
				})
				.state('campaigns', {
					url : '/campaigns',
					controller : 'CampaignsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/campaigns/campaigns.html',
					ncyBreadcrumb: {
				    	label: 'Campaigns'
				    }
				})
				.state('campaigns-code', {
					url : '/campaigns/:code',
					controller : 'CampaignsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/index.html'
				})
				.state(
						'integrations-new',
						{
							url : '/integrations/new/:code',
							controller : 'NewIntegrationController',
							controllerAs : 'vm',
							templateUrl : '/static/templates/integrations/new-integration-index.html',
							ncyBreadcrumb: {
						    	label: 'New',
						    	parent: 'integrations'
						    }
						})
				.state(
						'integrations-edit',
						{
							url : '/integrations/edit/:code',
							controller : 'NewIntegrationController',
							controllerAs : 'vm',
							templateUrl : '/static/templates/integrations/new-integration-index.html',
							ncyBreadcrumb: {
						    	label: 'Edit',
						    	parent: 'integrations'
						    }
						})
				.state('integrations/:tabname', {
					url : '/integrations/:tabname',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html',
					ncyBreadcrumb: {
				    	label: '{{breadcrumbName}}',
				    	parent: 'integrations'
				    }
				})
				.state('integrations/:tabname/:result', {
					url : '/integrations/:tabname/:result',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html',
					ncyBreadcrumb: {
				    	label: 'Integrations',
				    	parent: 'integrations'
				    }
				})
				.state('integrations', {
					url : '/integrations',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html',
					ncyBreadcrumb: {
				    	label: 'Integrations',
				    	parent: 'admin'
				    }
				})				
				.state('oauth/:source', {
					url : '/oauth/:source?code&state&access_token&expires_in&refresh_token&oauth_token&oauth_verifier',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/index.html'
				})
				.state('data', {
					url : '/data',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/data.html'
				})
				.state('dataRetrieval', {
					url : '/dataretrieval/:object/:retrievalsource',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/data.html'
				})
				.state('main-dashboard', {
					url : '/dashboard',
					controller : 'CompanyController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/company/dashboard.html'
				})
				.state('setup', {
					url : '/setup',
					controller : 'CompanyController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/company/setup-main.html',
					ncyBreadcrumb: {
				    	label: 'Setup',
				    	parent: 'admin'
				    }
				})
				.state('setup/:tabname', {
					url : '/setup/:tabname',
					controller : 'CompanyController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/company/setup-main.html',
					/*templateUrl : function ($stateParams) {
						var constUrl = '/static/templates/company/';
						if ($stateParams.tabname == 'setup')
							return constUrl + 'setup-main.html';
						else if ($stateParams.tabname == 'statuses')
							return constUrl + 'lead-statuses-index.html';
					},*/
					ncyBreadcrumb: {
				    	label: '{{breadcrumbName}}',
				    	parent: 'setup'
				    }
				})
				.state('tweets', {
					url : '/tweets',
					controller : 'SocialController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/social/twitter-list.html'
				})
				.state('twitter-master-list', {
					url : '/twitter-master-list',
					controller : 'SocialController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/social/twitter-master-list.html'
				})
				.state('twitter-admin', {
					url : '/twitter-admin',
					controller : 'SocialController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/social/twitter-admin.html'
				})
				.state('analytics-data', {
					url : '/analytics-data',
					controller : 'AnalyticsDataController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/analytics-data.html'
				})
				.state('binders', {
					url : '/binders',
					controller : 'BindersController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/binders.html',
					ncyBreadcrumb: {
				    	label: 'Binders',
				    	parent: 'utils'
				    }
				})
				.state('binders-list', {
					url : '/binders/list/:template',
					controller : 'BindersController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/binder-list.html',
					ncyBreadcrumb: {
				    	label: 'List',
				    	parent: 'binders'
				    }
				})
				.state('binder-new', {
					url : '/binders/new',
					controller : 'BindersController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/binder-template.html',
					ncyBreadcrumb: {
				    	label: 'New',
				    	parent: 'binders'
				    }
				})
				.state('binder-show', {
					url : '/binder/:binderId',
					params: {
						binder: null, 
						binderId:null
					},
					controller : 'BindersController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/binder-show.html',
					ncyBreadcrumb: {
				    	label: '{{breadcrumbName}}',
				    	parent: 'binders'
				    }
				})
				.state('snapshots', {
					url : '/snapshots',
					controller : 'SnapshotsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/snapshots.html',
					ncyBreadcrumb: {
				    	label: 'Snapshots',
				    	parent: 'utils'
				    }
				})
				.state('snapshots-detail', {
					url : '/snapshots/:id',
					controller : 'SnapshotsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/snapshots.html',
					ncyBreadcrumb: {
				    	label: '{{snapshot_id}}',
				    	parent: 'snapshots'
				    }
				})
				.state('snapshot', {
					url : '/snapshot:html',
					controller : 'SnapshotsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/snapshot.html',
					ncyBreadcrumb: {
				    	label: 'Snapshot',
				    	parent: 'snapshots'
				    }
				})
				.state('enterChannel', {
					url : '/channel/:enteredRoom',
					params: {roomName:null, roomDescription:null},
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/messages/room-messages.html'
				})
				.state('enterSlack', {
					url : '/slack/:type/:id',
					params: {name:null, purpose:null},
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/messages/slack-messages.html'
				})
				.state('notifications', {
					url : '/notifications',
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/notifications.html'
				})
				.state('exports', {
					url : '/exports',
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/exports.html',
					ncyBreadcrumb: {
				    	label: 'Exports'
				    }
				})
				.state('/oops', {
					url : '/oops',
					controller : 'IndexController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/404.html',
					ncyBreadcrumb: {
				    	label: 'Uh oh'
				    }
				})
				.state('/', {
					url : '/',
					redirectTo: 'dashboards-listing',
				    ncyBreadcrumb: {
				    	label: 'Dashboards',
				    }
				});

		$urlRouterProvider.otherwise('/oops');
	}
})();