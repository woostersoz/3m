from __future__ import unicode_literals

from mongoengine import *
from mongoengine import signals
import datetime

from authentication.models import Company


# Create your models here.

class Snapshot(Document):

    company = ReferenceField(Company)
    owner = ObjectIdField()
    chart_name = StringField()
    snapshot_html = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'snapshot', 'indexes': ['id', 'company', 'owner'], 'ordering':['-updated_date']}

class AnalyticsData(Document): # stores data calculated for various charts

    company_id = IntField()
    chart_name = StringField()
    system_type = StringField()
    date = StringField()
    date_range = StringField()
    results = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'analyticsData', 'indexes': ['id', 'company_id', 'chart_name', 'date', {'fields' : ('company_id', 'chart_name', 'date', 'date_range'), 'unique': True}], 'ordering':['-updated_date']}
    
class AnalyticsIds(Document): # stores IDs of objects when needed for quick retrieval in charts

    company_id = IntField()
    chart_name = StringField()
    system_type = StringField()
    date = StringField()
    date_range = StringField()
    results = DictField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'analyticsIds', 'indexes': ['id', 'company_id', 'chart_name', 'date', {'fields' : ('company_id', 'chart_name', 'date'), 'unique': True, 'name': 'co_chart_date'}, {'fields' : ('company_id', 'chart_name', 'date', 'date_range'), 'unique': True}], 'ordering':['-updated_date']}

class PageTemplate(Document):
    TYPE = ('chart', 'text')
    
    type = StringField(choices=TYPE)
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    page_html = StringField() 

    meta = {'collection': 'pageTemplate', 'indexes': ['id', 'type'], 'ordering':['-updated_date']}

class BinderTemplate(Document):
    ORIENTATION = ('Portrait', 'Landscape')
    FREQUENCY = ('One Time', 'Daily', 'Weekly', 'Monthly')
    
    company = ReferenceField(Company)
    owner = ObjectIdField()
    name = StringField()
    pages = ListField(DictField()) #PageTemplate()
    orientation = StringField(choices=ORIENTATION)
    frequency = StringField(choices=FREQUENCY)
    frequency_day = StringField() #for info such as Montly(Frequency) on the 15th
    distribution_list = ListField(EmailField())
    binder_count = IntField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'binderTemplate', 'indexes': ['id', 'company'], 'ordering':['-updated_date']}
    
class Binder(Document):
    ORIENTATION = ('Portrait', 'Landscape')
    FREQUENCY = ('One Time', 'Daily', 'Weekly', 'Monthly')
    
    company = ReferenceField(Company)
    owner = ObjectIdField()
    name = StringField()
    pages = ListField(DictField())
    binder_template = ReferenceField(BinderTemplate)
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'binder', 'indexes': ['id', 'company', 'owner'], 'ordering':['-updated_date']}