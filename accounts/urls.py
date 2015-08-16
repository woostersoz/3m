from django.conf.urls import patterns, url

from accounts import views
 
urlpatterns = patterns('',
    url(r'^companies/$', views.getAccountsAndCounts, name='list_all_companies_and_counts'),
    url(r'^account-match/(?P<accountSearchName>[^/]+)/$', views.matchAccountName, name='match_account_by_name'),
    url(r'^company-match/(?P<companySearchName>[^/]+)/$', views.matchCompanyName, name='match_company_by_name'),
    url(r'^$', views.getAccounts, name='list_all_accounts'),
 )
