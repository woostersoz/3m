from django.conf.urls import patterns, url

from leads import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveLeadsDaily, name='retrieve_leads_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveLeads, name='retrieve_leads'),
    url(r'^filter/$', views.filterLeads, name='filter_leads'),
    url(r'^filter/duration/$', views.filterLeadsByDuration, name='filter_leads_by_duration'),
    url(r'^filter/source/$', views.filterLeadsBySource, name='filter_leads_by_source'),
    url(r'^filter/revenue-source/$', views.filterLeadsByRevenueSource, name='filter_leads_by_source'),
    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.LeadsViewSet.as_view(), name='list_leads_by_source'),
    #url(r'^$', lenses.LeadsViewSet.as_view(), name='list_all_leads'),
    url(r'^$', views.getLeads, name='list_all_leads'),
    #url(r'^$', lenses.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
