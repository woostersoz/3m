from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json


# Create your models here.
class Campaign(Document):

    company_id = IntField()
    #derived_id = StringField()
    source_system = StringField()
    name = StringField()
    guid = StringField()
    channel = StringField()
    emails = ListField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'campaign', 'indexes': ['id', 'company_id', 'guid', 'name', {'fields' : ('company_id', 'guid'), 'unique': True, 'name': 'co_guid'}], 'ordering':['-updated_date']}

class EmailEvent(Document):

    company_id = IntField()
    #derived_id = StringField()
    source_system = StringField()
    campaign_guid = StringField()
    email_id = IntField()
    event_type = StringField()
    event_id = StringField()
    recipient = StringField()
    created = IntField()
    details = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'emailEvent', 'indexes': ['id', 'company_id', 'campaign_guid', {'fields' : ('company_id', 'campaign_guid'), 'unique': False, 'name': 'co_guid'}, {'fields' : ('company_id', 'campaign_guid', 'email_id', 'created'), 'unique': False, 'name': 'created'}, {'fields' : ('company_id', 'campaign_guid', 'email_id', 'event_id'), 'unique': True, 'name': 'all'}, {'fields' : ('company_id', 'event_type', 'created', 'details.url'), 'unique': False, 'name': 'drilldown'}], 'ordering':['-updated_date']}
