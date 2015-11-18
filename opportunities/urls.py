from django.conf.urls import patterns, url

from opportunities import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveOpportunitiesDaily, name='retrieve_opportunities_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveOpportunities, name='retrieve_opportunities'),
#    url(r'^(?P<code>[a-z:\\.0-9]+)/$', lenses.ActivitiesViewSet.as_view(), name='list_activities_by_source'),
#    url(r'^$', lenses.ActivitiesViewSet.as_view(), name='list_all_activities'),
    #url(r'^$', lenses.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
