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


class Traffic(Document):
    company_id = IntField()
    data = DictField()
    source_created_date = StringField()
    source_id = StringField()
    source_source = StringField()
    source_account_id = StringField()
    source_account_name = StringField()
    source_profile_id = StringField()
    source_profile_name = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'traffic', 'indexes': ['company_id', 'source_source', 'updated_date', 'source_created_date', 'source_id'], 'ordering':['-updated_date']}
