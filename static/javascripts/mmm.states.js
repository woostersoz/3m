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
				.state('dashboards', {
					url : '/dashboards/:type',
					controller : 'DashboardsController',
					controllerAs : 'vm',
					templateUrl : function ($stateParams) {
						var constUrl = '/static/templates/dashboards/';
						if ($stateParams.type == 'funnel')
							return constUrl + 'dashboard-funnel.html';
						else if ($stateParams.type == 'social')
							return constUrl + 'dashboard-social.html';
						else if ($stateParams.type == 'waterfall')
							return constUrl + 'dashboard-waterfall.html';
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
					templateUrl : '/templates/admin/index.html'
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
					templateUrl : '/static/templates/authentication/users.html'
				})
				.state('profile', {
					url : '/users/:id',
					//params: {id:null},
					controller : 'ProfileController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/profiles/profile.html'
				})
				.state('profile_settings', {
					url : '/users/:id/settings',
					controller : 'ProfileSettingsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/profiles/settings.html'
				})
				.state('leads', {
					url : '/leads',
					controller : 'LeadsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/leads/leads.html'
				})
				.state('leads-code', {
					url : '/leads/:code',
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
					templateUrl : '/static/templates/accounts/accounts.html'
				})
				.state('companies', {
					url : '/companies',
					controller : 'AccountsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/accounts/accounts-companies.html'
				})
				.state('campaigns', {
					url : '/campaigns',
					controller : 'CampaignsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/campaigns/campaigns.html'
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
							templateUrl : '/static/templates/integrations/new-integration-index.html'
						})
				.state(
						'integrations-edit',
						{
							url : '/integrations/edit/:code',
							controller : 'NewIntegrationController',
							controllerAs : 'vm',
							templateUrl : '/static/templates/integrations/new-integration-index.html'
						})
				.state('integrations/:tabname', {
					url : '/integrations/:tabname',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html'
				})
				.state('integrations/:tabname/:result', {
					url : '/integrations/:tabname/:result',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html'
				})
				.state('integrations', {
					url : '/integrations',
					controller : 'IntegrationsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/integrations/main.html'
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
				.state('dashboard', {
					url : '/dashboard',
					controller : 'CompanyController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/company/dashboard.html'
				})
				.state('analytics', {
					url : '/analytics',
					controller : 'AnalyticsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/analytics.html'
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
					templateUrl : '/static/templates/analytics/binders.html'
				})
				.state('snapshots', {
					url : '/snapshots',
					controller : 'SnapshotsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/snapshots.html'
				})
				.state('snapshot', {
					url : '/snapshot:html',
					controller : 'SnapshotsController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/analytics/snapshot.html'
				})
				.state('enterChannel', {
					url : '/channel/:enteredRoom&:roomName&:roomDescription',
					//params: {enteredRoom:null},
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/messages/room-messages.html'
				})
				.state('notifications', {
					url : '/notifications',
					controller : 'MessagesController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/notifications.html'
				})
				.state('/oops', {
					url : '/oops',
					controller : 'IndexController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/layout/404.html'
				})
				.state('/', {
					url : '/',
					controller : 'CompanyController',
					controllerAs : 'vm',
					templateUrl : '/static/templates/company/dashboard.html'
				});

		$urlRouterProvider.otherwise('/oops');
	}
})();