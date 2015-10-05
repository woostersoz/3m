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


# class UserOauth(Document):
# 
#     user_id = IntField()
#     updated_date = DateTimeField(default=datetime.datetime.utcnow())
#     sfdc_access_token = StringField(max_length=300)
#     mkto_access_token = StringField(max_length=300)
#     slck_access_token = StringField(max_length=300)
# 
#     meta = {'collection': 'userOauth', 'indexes': ['user_id'], 'ordering':['-updated_date']}
        