from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from leads.models import Lead

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json

from celery.worker.control import heartbeat

# Create your models here.

class TempDataOpportunity(Document): #middleware table to store source data
    company_id = IntField()
    source_system = StringField()
    source_record = DynamicField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'tempDataOpportunity', 'indexes': ['id', 'company_id', 'updated_date', 'source_system'], 'ordering':['-updated_date']}
