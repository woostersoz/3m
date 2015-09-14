from django.conf.urls import patterns, url

from analytics import views
 
urlpatterns = patterns('',
    url(r'^filters/$', views.retrieveFilters, name='retrieve_chart_filter_values'),
    url(r'^retrieve/$', views.retrieveAnalytics, name='retrieve_analytics'),
    url(r'^calculate/$', views.calculateAnalytics, name='calculate_analytics'),
    url(r'^charts/$', views.getCharts, name='retrieve_charts'),
    url(r'^snapshot/save/$', views.saveSnapshot, name='save_snapshot'),
    url(r'^snapshot/(?P<id>[a-z:\\.0-9]+)', views.getSnapshot, name='get_snapshot'),
    url(r'^snapshots/$', views.getSnapshots, name='get_snapshots'),
    url(r'^binder-template/$', views.SingleBinderTemplate.as_view({'post': 'create'}), name='binder-template'), #'get': 'list', 'delete': 'delete', 'put': 'update',  
    url(r'^binder-templates/$', views.BinderTemplates.as_view({'get': 'list'}), name='binder-templates'), #'post': 'create', 'delete': 'delete', 'put': 'update',  
    url(r'^binders/(?P<binder_template_id>[a-z:\\.0-9]+)/$', views.Binders.as_view({'get': 'list'}), name='binders'), #'post': 'create', 'delete': 'delete', 'put': 'update',  
    url(r'^binder/(?P<binder_id>[a-z:\\.0-9]+)/$', views.SingleBinder.as_view({'get': 'list'}), name='binder'), #'post': 'create', 'delete': 'delete', 'put': 'update',  

#    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.ActivitiesViewSet.as_view(), name='list_activities_by_source'),
#    url(r'^$', views.ActivitiesViewSet.as_view(), name='list_all_activities'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
