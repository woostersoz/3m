from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from leads.models import Lead

from mongoengine import *
from mongoengine import signals
from mongoengine_extras.fields import SlugField
from mongoengine_extras.utils import slugify
# from mongoengine_relational import RelationManagerMixin
# from mongoengine_relational import *

import datetime
from bson import json_util
import json

from collab.signals import send_notification
from analytics.models import Snapshot
from authentication.models import Company, CustomUser

# Create your models here.

class Notification(Document):

    company = ReferenceField(Company)
    recipient = ObjectIdField()
    owner = ObjectIdField()
    type = StringField()
    message = StringField()
    success = BooleanField()
    method = StringField() #name of method/class that was being run
    read = BooleanField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'message', 'indexes': ['id', 'company', 'owner'], 'ordering':['-updated_date']}
    @property
    def company_id(self):
        return self.company.company_id 

    @classmethod
    def post_save(cls, sender, document, **kwargs): #(self, *args, **kwargs): #
        try:
            
            send_notification(dict(
                 updated_date=json.dumps(document.updated_date, default=json_util.default),
                 message=document.message,
                 owner=json.dumps(document.owner, default=json_util.default),
                 id=json.dumps(document.id, default=json_util.default),
                 read = document.read,
                 success = document.success
                ))
        except Exception as e:
            send_notification(dict(
             type='error',
             message=str(e)
            ))
                    
        
signals.post_save.connect(Notification.post_save, sender=Notification)

class ChatRoom(Document):
    company = ReferenceField(Company)
    owner = ReferenceField(CustomUser)
    nickname = StringField(max_length=20) #redundant but needed
    name = StringField(max_length=200)
    description = StringField(max_length=256)
    slug = SlugField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'chatRoom', 'indexes': ['id', 'company', 'owner'], 'ordering':['name']}


    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ("room", (self.slug,))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(ChatRoom, self).save(*args, **kwargs)
    

class ChatUser(Document):
    company = ReferenceField(Company)
    user = ReferenceField(CustomUser)
    nickname = StringField(max_length=20)
    #session = StringField(max_length=20)
    room = ReferenceField(ChatRoom) #, related_name="users"
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'chatUser', 'indexes': [{'fields' : ('user', 'room'), 'unique': True}], 'ordering':['nickname']}


    def __unicode__(self):
        return self.nickname
    
    def getRoomName(self):
        return self.room.name
    
    def getRoom(self):
        return self.room

    
class ChatUserMessage(Document):
    company = ReferenceField(Company)
    user = ReferenceField(CustomUser)
    nickname = StringField(max_length=20)
    #session = StringField(max_length=20)
    room = ReferenceField(ChatRoom) #, related_name="users"
    message = StringField(max_length=5000)
    snapshot = ReferenceField(Snapshot, required=False)
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'chatUserMessage', 'indexes': ['id', 'company', 'user'], 'ordering':['updated_date']}

