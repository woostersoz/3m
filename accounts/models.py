from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json
from leads.models import Lead

from celery.worker.control import heartbeat

# Create your models here.

class SuperAccount(Document):

    names = ListField(StringField())
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'superAccount', 'indexes': ['id', 'updated_date', 'names'], 'ordering':['-updated_date']}

class Account(Document):

    company_id = IntField()
    mkto_id = StringField()
    sfdc_id = StringField()
    hspt_id = StringField()
    accounts = DictField()
    leads = ListField(required=False) #ListField(ReferenceField(Lead))) changed this on 1/20/15 to allow for SFDC Contact ID to be kept here rather than CX Lead ID
    opportunities = DictField()
    source_name = StringField()
    source_source = StringField()
    source_industry = StringField()
    source_created_date = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'account', 'indexes': ['company_id', 'source_name', 'updated_date'], 'ordering':['-updated_date']}