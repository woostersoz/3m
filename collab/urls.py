from django.conf.urls import patterns, url

from collab import views
 
urlpatterns = patterns('',
    url(r'^(?P<type>[a-z:\\.0-9]+)/count', views.getCount, name='retrieve_count'),
    url(r'^(?P<type>[a-z:\\.0-9]+)/setunread', views.setUnread, name='retrieve_count'),
    url(r'rooms/user/membership/', views.getUserRooms, name="user_rooms"),
    url(r'rooms/user/notjoined/', views.getUserNotJoinedRooms, name="user_not_joined_rooms"),
    url(r'room/user/join/', views.user_join_room, name="user_join_room"),
    url(r'room/user/create/', views.user_create_room, name="user_create_room"),
    url(r'room/user/message/create/', views.user_create_message, name="user_create_message"),
    url(r'room/messages/', views.room_get_messages, name="room_get_messages"),
    url(r'rooms/', views.rooms, name="rooms"),
    url(r'^(?P<type>[a-z:\\.0-9]+)/room/create/$', "create", name="create"),
    url(r'^(?P<type>[a-z:\\.0-9]+)/room/(?P<slug>.*)$', "room", name="room"),
    url(r'^(?P<type>[a-z:\\.0-9]+)/(?P<subtype>[a-z:\\.0-9]+)/$', views.MessagesViewSet.as_view(), name='list_messages_by_type'),
    #url(r'^$', views.CampaignsViewSet.as_view(), name='campaigns_by_source'),
 )
