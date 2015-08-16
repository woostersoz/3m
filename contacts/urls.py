from django.conf.urls import patterns, url

from contacts import views
 
urlpatterns = patterns('',
    url(r'^retrieve/daily/$', views.retrieveContactsDaily, name='retrieve_contacts_daily'), # for cron job
    url(r'^retrieve/$', views.retrieveContacts, name='retrieve_contacts'),
    url(r'^filter/$', views.filterLeads, name='filter_leads'),
    url(r'^filter/duration/$', views.filterLeadsByDuration, name='filter_leads_by_duration'),
    url(r'^filter/source/$', views.filterLeadsBySource, name='filter_leads_by_source'),
    url(r'^(?P<code>[a-z:\\.0-9]+)/$', views.LeadsViewSet.as_view(), name='list_leads_by_source'),
    #url(r'^$', views.LeadsViewSet.as_view(), name='list_all_leads'),
    url(r'^$', views.getAllLeads, name='list_all_leads'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
