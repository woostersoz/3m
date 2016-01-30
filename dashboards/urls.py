from django.conf.urls import patterns, url

from dashboards import views
 
urlpatterns = patterns('',
    url(r'^retrieve/$', views.retrieveDashboards, name='retrieve_dashboards'),
    url(r'^calculate/$', views.calculateDashboards, name='calculate_dashboards'),
    url(r'^drilldown/$', views.drilldownDashboards, name='drilldown_dashboards'),
    url(r'^dashboards/$', views.getDashboards, name='get_dashboards'),
    
 )
