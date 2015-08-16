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

    names = ListField(StringField)
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'superAccount', 'indexes': ['id', 'updated_date', 'names'], 'ordering':['-updated_date']}

class Account(Document):

    company_id = IntField()
    mkto_id = StringField(sparse=True)
    sfdc_id = StringField(sparse=True)
    hspt_id = StringField(sparse=True)
    accounts = DictField()
    leads = ListField(ReferenceField(Lead))
    source_name = StringField()
    source_source = StringField()
    source_industry = StringField()
    source_created_date = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'account', 'indexes': ['company_id', 'source_name', 'updated_date'], 'ordering':['-updated_date']}