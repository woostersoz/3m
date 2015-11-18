from django.conf.urls import patterns, url

from social import views
 
urlpatterns = patterns('',
    url(r'^twitter/categories/$', views.TwitterCategories.as_view({'get': 'list', 'post': 'create'}), name='twitter_categories'), 
    url(r'^twitter/category/size/$', views.get_tw_category_size, name='twitter_category_size'),
    url(r'^twitter/category/(?P<category_id>[a-z:\\.0-9]+)/$', views.TwitterCategory.as_view({'get': 'list', 'delete': 'delete', 'put': 'update', 'post': 'create'}), name='twitter_category'),
    url(r'^twitter/handles/$', views.get_tw_handles_buffer, name='twitter_handles'),
    url(r'^twitter/filter/$', views.filterTwInteractions, name='filter_twitter_interactions'),
    url(r'^tweets/$', views.Tweets.as_view({'get': 'list', 'post': 'create'}), name='tweets'), 
    url(r'^tweet/(?P<tweet_id>[a-z:\\.0-9]+)/$', views.SingleTweet.as_view({'get': 'list', 'delete': 'delete', 'put': 'update', 'post': 'create'}), name='tweet'),  
    url(r'^twitter/masterlists/$', views.TwitterMasterLists.as_view({'get': 'list', 'post': 'create'}), name='twitter_categories'), 
    url(r'^twitter/masterlist/(?P<masterlist_id>[a-z:\\.0-9]+)/publish/$', views.publishMl, name='twitter_publish_master_list'),
    url(r'^twitter/masterlist/(?P<masterlist_id>[a-z:\\.0-9]+)/$', views.SingleTweetMasterList.as_view({'post': 'create', 'get': 'list'}), name='twitter_master_list'), #'get': 'list', 'delete': 'delete', 'put': 'update', 
#     url(r'^retrieve/$', lenses.retrieveLeads, name='retrieve_leads'),
#     url(r'^filter/$', lenses.filterLeads, name='filter_leads'),
#     url(r'^filter/duration/$', lenses.filterLeadsByDuration, name='filter_leads_by_duration'),
#     url(r'^filter/source/$', lenses.filterLeadsBySource, name='filter_leads_by_source'),
#     url(r'^filter/revenue-source/$', lenses.filterLeadsByRevenueSource, name='filter_leads_by_source'),
#     url(r'^(?P<code>[a-z:\\.0-9]+)/$', lenses.LeadsViewSet.as_view(), name='list_leads_by_source'),
#    url(r'^$', lenses.getAccountsAndCounts, name='list_all_accounts_and_counts'),
 )
