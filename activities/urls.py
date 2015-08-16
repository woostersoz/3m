from django.conf.urls import patterns, url

from activities import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveActivitiesDaily, name='retrieve_activities_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveActivities, name='retrieve_activities'),
    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.ActivitiesViewSet.as_view(), name='list_activities_by_source'),
    url(r'^$', views.ActivitiesViewSet.as_view(), name='list_all_activities'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
