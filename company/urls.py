from django.conf.urls import patterns, include, url

from company import views
from integrations.views import AuthorizeViewSet
from authentication.views import UserViewSet, SingleUserViewSet
from campaigns import views as campaignViews
 
urlpatterns = patterns('',
    url(r'^companies/$', views.CompaniesViewSet.as_view({'get': 'list', 'post': 'create'}), name='companies'),
    url(r'^(?P<companyid>[a-z:\\.0-9]+)/users/(?P<id>[a-z:\\.0-9]+)/$', SingleUserViewSet.as_view({'get': 'list', 'delete': 'delete', 'put': 'put'}), name='single_user'),
    url(r'^(?P<id>[a-z:\\.0-9]+)/users/$', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='users'),
#     url(r'^form/(?P<code>[A-Z:\\.0-9]+)/$', views.IntegrationFormView.as_view(), name='integration_form'),
    url(r'^form/(?P<code>[a-z:\\.0-9]+)/$', views.IntegrationFormView.as_view(), name='integration_form'),
    url(r'^(?P<id>[a-z:\\.0-9]+)/data/(?P<run_type>[a-z:\\.0-9]+)/$', views.CompanyDataViewSet.as_view({'get': 'list', 'post': 'create'}), name='company_data_mgt'),
    url(r'^(?P<id>[a-z:\\.0-9]+)/integration/authorize/$', AuthorizeViewSet.as_view({'get': 'list'}), name='integration_authorize'),
    url(r'^(?P<id>[a-z:\\.0-9]+)/integration/', views.CompanyIntegrationViewSet.as_view({'get': 'list'}), name='company_integration'),
    url(r'^integrations/(?P<status>[a-z:\\.0-9]+)/$', views.SystemsList.as_view(), name='integrations_list'),
    url(r'^integration/(?P<id>[a-z:\\.0-9]+)/(?P<code>[a-z:\\.0-9]+)/$', views.SingleIntegration.as_view(), name='integration_delete'),
    url(r'^(?P<id>[a-z:\\.0-9]+)/campaigns/', include('campaigns.urls', namespace="campaigns")),  
    url(r'^(?P<id>[a-z:\\.0-9]+)/leads/', include('leads.urls', namespace="leads")),
    url(r'^(?P<id>[a-z:\\.0-9]+)/accounts/', include('accounts.urls', namespace="accounts")),
    url(r'^(?P<id>[a-z:\\.0-9]+)/contacts/', include('contacts.urls', namespace="contacts")),
    url(r'^(?P<id>[a-z:\\.0-9]+)/activities/', include('activities.urls', namespace="activities")), 
    url(r'^(?P<id>[a-z:\\.0-9]+)/opportunities/', include('opportunities.urls', namespace="opportunities")), 
    url(r'^(?P<id>[a-z:\\.0-9]+)/websites/', include('websites.urls', namespace="websites")),
    url(r'^(?P<company_id>[a-z:\\.0-9]+)/analytics/', include('analytics.urls', namespace="analytics")), 
    url(r'^(?P<company_id>[a-z:\\.0-9]+)/dashboards/', include('dashboards.urls', namespace="dashboards")), 
    url(r'^(?P<id>[a-z:\\.0-9]+)/integrations/', include('integrations.urls', namespace="integrations")),   
    url(r'^(?P<id>[a-z:\\.0-9]+)/social/', include('social.urls', namespace="social")),   
    url(r'^(?P<id>[a-z:\\.0-9]+)/count/$', views.getCount, name='count_objects'),  
    url(r'^(?P<id>[a-z:\\.0-9]+)/collab/', include('collab.urls', namespace="collab")),
    url(r'^(?P<company_id>[a-z:\\.0-9]+)/superadmin/', include('superadmin.urls', namespace="superadmin")),
    url(r'^(?P<id>[a-z:\\.0-9]+)/timezones/$', views.getTimezones, name='get_timezones'),
)
