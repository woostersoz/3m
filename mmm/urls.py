from django.conf.urls import patterns, include, url
from django.contrib import admin
#from django.views.decorators.cache import never_cache
#from django.contrib.auth.decorators import login_required

from rest_framework_nested import routers
from authentication.views import UserViewSet, LoginView, LogoutView
from socketio import sdjango
sdjango.autodiscover()

from mmm import views
from leads.views import LeadsViewSet
from campaigns.views import CampaignsViewSet


# router = routers.SimpleRouter()
# router.register(r'accounts', UserViewSet)
# 
# 
# accounts_router = routers.NestedSimpleRouter(
#     router, r'accounts', lookup='account'
# )

#accounts_router.register(r'leads', LeadsViewSet, 'leads' )
#accounts_router.register(r'campaigns', CampaignsViewSet, 'campaigns' )
#accounts_router.register(r'authorize', AuthorizeViewSet, 'authorize' )
                
urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mysite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    #url(r'^api/v1/', include(router.urls)),
    #url(r'^api/v1/', include(accounts_router.urls)),
    url(r'^api/v1/auth/login/$', LoginView.as_view(), name='login'),
#    url(r'^login/$', LoginView.as_view(), name='login_direct'),
    url(r'^api/v1/auth/logout/$', LogoutView.as_view(), name='logout'),
    url(r'^api/v1/export/(?P<type>[a-z:\\.0-9]+)', views.ExportView.as_view(), name='exports'),
#    url('', include('django.contrib.auth.urls', namespace='auth')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v1/oauth/', include('integrations.urls', namespace="integrations")),
#    url(r'^api/v1/superadmin/', include('superadmin.urls', namespace="superadmin")),
    url(r'^api/v1/campaigns/', include('campaigns.urls', namespace="campaigns")),
    url(r'^api/v1/company/', include('company.urls', namespace="company")),
    url(r'^api/v1/collab/', include('collab.urls', namespace="collab")),
    url(r'^api/v1/name-match/$', views.matchingAlgo, name='name-matching'),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    url(r'^socket\.io', include(sdjango.urls)),
    url(r'^mongonaut/', include('mongonaut.urls')),
    url('^.*$', views.IndexView.as_view(), name='index'),
)
