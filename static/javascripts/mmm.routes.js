/*(function () {
  'use strict';

  angular
    .module('mmm.routes')
    .config(config);

  config.$inject = ['$routeProvider'];

  *//**
  * @name config
  * @desc Define valid application routes
  *//*
  function config($routeProvider) {
	  $routeProvider.when('/register', {
		  controller: 'RegisterController', 
		  controllerAs: 'vm',
		  templateUrl: '/static/templates/authentication/register.html'
		}).when('/login', {
		   controller: 'LoginController',
		   controllerAs: 'vm',
	       templateUrl: '/static/templates/authentication/login.html'
		}).when('/login:query', {
		  controller: 'LoginController',
		  controllerAs: 'vm',
		  templateUrl: '/static/templates/authentication/login.html'
		}).when('/accounts/login', {
		   controller: 'LoginController',
		   controllerAs: 'vm',
	 	  templateUrl: '/static/templates/authentication/login.html'
		}).when('/accounts/:username', {
		  controller: 'ProfileController',
		  controllerAs: 'vm',
		  templateUrl: '/static/templates/profiles/profile.html'
		}).when('/accounts/:username/settings', {
		  controller: 'ProfileSettingsController',
		  controllerAs: 'vm',
		  templateUrl: '/static/templates/profiles/settings.html'
		}).when('/leads', {
	      controller: 'LeadsController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/layout/index.html'
		}).when('/campaigns', {
	      controller: 'CampaignsController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/layout/index.html'
		}).when('/integrations/new/:code', {
	      controller: 'NewIntegrationController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/integrations/new-integration-index.html'
	    }).when('/integrations/:tabname', {
	      controller: 'IntegrationsController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/integrations/main.html'
		}).when('/integrations/:tabname/:result', {
		  controller: 'IntegrationsController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/integrations/main.html'
        }).when('/integrations', {
	      controller: 'IntegrationsController',
	      controllerAs: 'vm',
	      templateUrl: '/static/templates/integrations/main.html'
		}).when('/oauth/:source', {
		  controller: 'IntegrationsController',
		  controllerAs: 'vm',
		  templateUrl: '/static/templates/layout/index.html'
		}).when('/oops', {
		   controller: 'IndexController',
		   controllerAs: 'vm',
	       templateUrl: '/static/templates/layout/404.html'
		}).when('/', {
		   controller: 'IndexController',
		   controllerAs: 'vm',
		   templateUrl: '/static/templates/layout/index.html'
		}).otherwise({redirectTo: '/oops'})
  }
})();*/