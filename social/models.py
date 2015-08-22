from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json

from celery.worker.control import heartbeat
from authentication.models import Company

# Create your models here.
class CompanyTweetCategory(Document):
    company = ReferenceField(Company)
    category_name = StringField()
    description = StringField()
    weight = IntField()
    meta = {'collection': 'companyTweetCategory', 'indexes': ['id', 'category_name'], 'ordering':['-id']}


class Tweet(Document):
    company = ReferenceField(Company)
    text1 = StringField(max_length=140)
    text2 = StringField(max_length=140)
    text3 = StringField(max_length=140)
    category = ReferenceField(CompanyTweetCategory, reverse_delete_rule=DENY)
    #owner = ObjectIdField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'tweet', 'indexes': ['id', 'updated_date', 'company'], 'ordering':['-updated_date']}

            
class TweetMasterList(Document):
    company = ReferenceField(Company)
    tweets = ListField(DictField())
    tw_handle = StringField()
    buffer_profile_id = StringField()
    published = BooleanField(default=False)
    published_date = DateTimeField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)
    
    meta = {'collection': 'tweetMasterList', 'indexes': ['id', 'updated_date', 'published_date', 'tw_handle'], 'ordering':['-updated_date']}

class PublishedTweet(Document):
    company_id = IntField()
    interaction_id = StringField()
    published_timestamp = IntField()
    published_date = StringField()
    data = DictField()
    #owner = ObjectIdField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'publishedTweet', 'indexes': ['id', 'published_date', 'updated_date', 'company_id'], 'ordering':['-published_timestamp']}

class FbAdInsight(Document):
    company_id = IntField()
    data = DictField()
    source_created_date = StringField()
    source_account_id = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'facebookAdInsight', 'indexes': ['company_id', 'updated_date', 'source_created_date', 'source_account_id'], 'ordering':['-updated_date']}

class FbAdCampaignInsight(Document):
    company_id = IntField()
    data = DictField()
    source_created_date = StringField()
    source_campaign_id = StringField()
    source_campaign_name = StringField()
    source_account_id = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'facebookAdCampaignInsight', 'indexes': ['company_id', 'updated_date', 'source_created_date', 'source_account_id', 'source_campaign_id'], 'ordering':['-updated_date']}

class FbPageInsight(Document):
    company_id = IntField()
    data = DictField()
    source_metric_id = StringField()
    source_metric_name = StringField()
    source_page_id = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'facebookPageInsight', 'indexes': ['company_id', 'updated_date', 'source_metric_id', 'source_metric_name', 'source_page_id'], 'ordering':['-updated_date']}

class FbPostInsight(Document):
    company_id = IntField()
    data = DictField()
    source_metric_id = StringField()
    source_metric_name = StringField()
    source_page_id = StringField()
    source_post_id = StringField()
    source_created_date = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'facebookPostInsight', 'indexes': ['company_id', 'updated_date', 'source_created_date', 'source_metric_id', 'source_metric_name', 'source_page_id', 'source_post_id'], 'ordering':['-updated_date']}
