from django.conf.urls import patterns, url

from lenses import views
 
urlpatterns = patterns('',
    url(r'^retrieve/$', views.retrieveViews, name='retrieve_views'),
    #url(r'^drilldown/$', lenses.drilldownDashboards, name='drilldown_views'),
    url(r'^superfilters/$', views.getSuperFilters, name='get_super_filters'),
    url(r'^views/$', views.getViews, name='get_views'),
    
 )
