from django.conf.urls import patterns, url

from websites import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveLeadsDaily, name='retrieve_leads_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveLeads, name='retrieve_leads'),
    url(r'^filter/$', views.filterWebsites, name='filter_website_visitors'),
    url(r'^filter/duration/$', views.filterLeadsByDuration, name='filter_leads_by_duration'),
    url(r'^filter/source/$', views.filterLeadsBySource, name='filter_leads_by_source'),
    url(r'^filter/revenue-source/$', views.filterLeadsByRevenueSource, name='filter_leads_by_source'),
    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.LeadsViewSet.as_view(), name='list_leads_by_source'),
    #url(r'^$', views.LeadsViewSet.as_view(), name='list_all_leads'),
    url(r'^$', views.getAllLeads, name='list_all_leads'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
