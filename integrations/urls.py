from django.conf.urls import patterns, url

from integrations import views
 
urlpatterns = patterns('',
    url(r'^sfdc/$', views.get_sfdc_token, name='sfdc'),
    url(r'^hspt/$', views.get_hspt_token, name='hspt'),
    url(r'^bufr/$', views.get_bufr_token, name='bufr'),
    url(r'^goog/$', views.get_goog_token, name='goog'),
    url(r'^fbok/$', views.get_fbok_token, name='fbok'),
    url(r'^twtr/$', views.get_twtr_token, name='twtr'),
    url(r'^goog-test/$', views.goog_test, name='goog-test'),
#    url(r'^fbok-test/$', views.get_campaign_stats, name='fbok-test'),
    url(r'^metadata/$', views.get_metadata, name='retrieve_metadata'),

)