from django.conf.urls import patterns, url

from campaigns import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveCampaignsDaily, name='retrieve_campaigns_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveCampaigns, name='retrieve_campaigns'),
    url(r'^filter/events/$', views.filterCampaignEmailEventsByType, name='filter_campaign_email_events_by_type'),
    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.CampaignsViewSet.as_view(), name='list_campaigns_by_source'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='list_all_campaigns'),
    url(r'^$', views.getAllCampaigns, name='list_all_campaigns'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
