from django.conf.urls import patterns, url

from superadmin import views
 
 
urlpatterns = patterns('',
   url(r'^jobs/$', views.JobViewSet.as_view({'get': 'list', 'post': 'create'}), name='job_monitor'),
)