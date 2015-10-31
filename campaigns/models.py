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
    derived_id = StringField()
    campaigns = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'campaign', 'indexes': ['id', 'company_id'], 'ordering':['-updated_date']}
