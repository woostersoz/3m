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

class BaseCompanyIntegration(Document):
    code = StringField()
    host = StringField()
    client_id = StringField()
    client_secret = StringField()
    redirect_uri = StringField()
    access_token= StringField()
    system_type = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    #created_date = DateTimeField(auto_now_add=True)
    
    meta = {'allow_inheritance': True}
    
class MktoIntegration(BaseCompanyIntegration):
    pass
    
class SfdcIntegration(BaseCompanyIntegration): 
    pass 

class CompanyIntegration(Document):

    company_id = IntField(unique=True)
    integrations = DictField()
    mapping = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    initial_run_done = BooleanField(default=False)
    initial_run_in_process = BooleanField(default=False)
    initial_run_last_date = DateTimeField()
    delta_run_done = BooleanField(default=False)
    delta_run_in_process = BooleanField(default=False)
    delta_run_last_date = DateTimeField()
    
    #created_date = DateTimeField(auto_now_add=True)

    meta = {'collection': 'companyIntegration', 'indexes': ['company_id']}
    
class CompanyIntegrationDeleted(Document):

    company_id = IntField()
    integrations = DictField()
    deleted_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'companyIntegrationDeleted', 'indexes': ['company_id']}
    
class TempData(Document): #middleware table to store source data from initial runs
    company_id = IntField()
    job_id = ObjectIdField()
    record_type = StringField()
    source_system = StringField()
    source_record = DynamicField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'tempData', 'indexes': ['id', 'company_id', 'job_id', 'updated_date', 'source_system', 'record_type', {'fields' : ('company_id', 'job_id', 'source_system', 'record_type', 'updated_date'), 'unique': False, 'name': 'std_query'}, {'fields' : ('company_id', 'job_id', 'source_system', 'record_type', 'source_record.campaign_guid'), 'unique': False, 'name': 'campaign_guid'}], 'ordering':['-updated_date']}

class TempDataDelta(Document): #middleware table to store source data from delta runs
    company_id = IntField()
    job_id = ObjectIdField()
    record_type = StringField()
    source_system = StringField()
    source_record = DynamicField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'tempDataDelta', 'indexes': ['id', 'company_id', 'job_id', 'updated_date', 'source_system', 'record_type', {'fields' : ('company_id', 'job_id', 'source_system', 'record_type', 'updated_date'), 'unique': False, 'name': 'std_query'}], 'ordering':['-updated_date']}

 
class UserOauth(Document):

    user_id = ObjectIdField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow())
    sfdc_access_token = StringField(max_length=300)
    mkto_access_token = StringField(max_length=300)
    slck_access_token = StringField(max_length=300)

    meta = {'collection': 'userOauth', 'indexes': ['user_id'], 'ordering':['-updated_date']}       