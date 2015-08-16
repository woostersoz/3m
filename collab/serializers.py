from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer
from mongoengine_extras.fields import SlugField
from mongoengine_extras.utils import slugify
# from mongoengine_relational import RelationManagerMixin
# from mongoengine_relational import *
from collab.models import Notification, ChatRoom, ChatUser, ChatUserMessage

class NotificationSerializer(DocumentSerializer):  
    
    class Meta:
        model = Notification
        fields = ('id', 'company', 'recipient', 'owner', 'type', 'message', 'success', 'method', 'read', 'updated_date' )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Notification(**attrs)
   
class ChatroomSerializer(DocumentSerializer):       
    
    class Meta:
        model = ChatRoom
        fields = ('id', 'company', 'name', 'updated_date', 'description', 'owner', 'nickname' )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return ChatRoom(**attrs)
   
class ChatuserSerializer(DocumentSerializer):       
    
    class Meta:
        model = ChatUser
        fields = ('id', 'company', 'user', 'room', 'updated_date', 'nickname' )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                print 'k is ' + str(k)
                setattr(instance, k, v)
            return instance
        return ChatUser(**attrs)
    
class ChatusermessageSerializer(DocumentSerializer):       
    
    class Meta:
        model = ChatUserMessage
        fields = ('id', 'user', 'room', 'updated_date', 'nickname', 'message', 'snapshot')

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return ChatUserMessage(**attrs)
   