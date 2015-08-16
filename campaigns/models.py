from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json

from celery.worker.control import heartbeat

# Create your models here.

class MktoCampaign(Document):
    active = StringField()
    createdAt = DateTimeField()
    id = IntField()
    name = StringField()
    programName =  StringField()
    type =  StringField()
    updatedAt = DateTimeField()
    workspaceName = StringField()

class Campaign(Document):

    company_id = IntField()
    derived_id = StringField()
    campaigns = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'campaign', 'indexes': ['id', 'company_id'], 'ordering':['-updated_date']}

class TempDataCampaign(Document): #middleware table to store source data
    company_id = IntField()
    source_system = StringField()
    source_record = DynamicField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'tempDataCampaign', 'indexes': ['id', 'company_id', 'updated_date', 'source_system'], 'ordering':['-updated_date']}
