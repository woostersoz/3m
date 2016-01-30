# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [app_label]'
# into your database.
from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json

from celery.worker.control import heartbeat
from mongoengine.fields import StringField


class SuperIntegration(Document):
    CRM = 'CRM'
    MA = 'MA'
    SYSTEM_TYPES = (
                  (CRM, 'CRM'),
                  (MA, 'Marketing Automation'),)

    code = StringField(max_length=10)
    name = StringField(max_length=300)
    vendor = StringField(max_length=300)
    description = StringField(max_length=1200)
    system_type = StringField(max_length=20, choices=SYSTEM_TYPES, )
    company_info = DictField()

    meta = {'collection': 'superIntegration', 'indexes': ['name']}
    
   
class SuperAnalytics(Document):
    src = StringField(max_length=200)
    url = StringField(max_length=200)
    title = StringField(max_length=1000)
    name = StringField(max_length=200)
    chart_type = StringField()
    system_type = StringField()
    object = StringField()
    category = StringField()
    status = StringField()
    descr = StringField()
    filters = ListField(StringField())
    
    meta = {'collection': 'superAnalytics', 'indexes': ['system_type', 'name', 'object']}
    
class SuperJobMonitor(Document):
    
    STATUS = ('Started', 'Completed', 'Failed')
    TYPE = ('initial', 'delta')
    
    company_id = IntField()
    started_date = DateTimeField()
    ended_date = DateTimeField()
    type = StringField(choices=TYPE)
    status = StringField(choices=STATUS, default='Started')
    tasks = ListField(DictField())
    comments = StringField()
    
    meta = {'collection': 'superJobMonitor', 'indexes': ['company_id', 'started_date', 'ended_date', 'status']}


class SuperUrlMapping(Document):
   
    mappings = ListField(StringField())
   
    meta = {'collection': 'superUrlMapping', 'indexes': ['mappings']}
    
class SuperCountry(Document):
   
    country = StringField()
    lat = StringField()
    long = StringField()
    continent = StringField()
    alternatives = ListField(StringField())
   
    meta = {'collection': 'superCountry', 'indexes': ['country', 'continent', 'alternatives']}
    
class SuperDashboards(Document):
    title = StringField(max_length=1000)
    name = StringField(max_length=200)
    dashboard_type = StringField()
    system_type = StringField()
    object = StringField()
    category = StringField()
    src = StringField(max_length=200)
    status = StringField()
    descr = StringField()
    template = StringField()
    filters = ListField(StringField())
    
    meta = {'collection': 'superDashboards', 'indexes': ['system_type', 'name', 'object']}
    
class SuperViews(Document):
    title = StringField(max_length=1000)
    name = StringField(max_length=200)
    system_type = StringField()
    object = StringField()
    category = StringField()
    sequence = IntField()
    src = StringField(max_length=200)
    status = StringField()
    descr = StringField()
    template = StringField()
    filters = ListField(StringField())
    
    meta = {'collection': 'superViews', 'indexes': ['system_type', 'name', 'object']}

class SuperFilters(Document):
    source_system = StringField()
    filters = DictField()
    
    meta = {'collection': 'superFilters', 'indexes': ['source_system', 'filters']}
