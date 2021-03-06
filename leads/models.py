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


class LeadBase(Document):

    company_id = IntField()
    mkto_id = StringField(sparse=True)
    sfdc_id = StringField(sparse=True)
    sfdc_contact_id = StringField(sparse=True)
    sfdc_account_id = StringField(sparse=True)
    sugr_id = StringField(sparse=True)
    sugr_account_id = StringField(sparse=True)
    sugr_contact_id = StringField(sparse=True)
    hspt_id = StringField(sparse=True)
    hspt_subscriber_date = DateTimeField(null=True, sparse=True)
    hspt_lead_date = DateTimeField(null=True, sparse=True)
    hspt_mql_date = DateTimeField(null=True, sparse=True)
    hspt_sql_date = DateTimeField(null=True, sparse=True)
    hspt_opp_date = DateTimeField(null=True, sparse=True)
    hspt_customer_date = DateTimeField(null=True, sparse=True)
    leads = DictField()
    contacts = DictField()
    activities = DictField()
    opportunities = DictField()
    lists = DictField()
    statuses = DictField()
    memberships = DictField()
    source_first_name = StringField()
    source_last_name = StringField()
    source_email = StringField()
    source_company = StringField()
    source_created_date = DateTimeField()
    source_status = StringField()
    source_stage = StringField()
    source_source = StringField()
    to_be_deleted = BooleanField(default=False)
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'lead', 'indexes': ['company_id', {'fields' : ('company_id', 'source_first_name', 'source_last_name'), 'unique': False, 'name': 'co_fname_lname'}, {'fields' : ('company_id', 'hspt_id', 'source_first_name', 'source_last_name'), 'unique': False, 'name': 'co_hspt_id_fname_lname'}, {'fields' : ('company_id', 'mkto_id', 'source_first_name', 'source_last_name'), 'unique': False, 'name': 'co_mkto_id_fname_lname'}, {'fields' : ('company_id', 'hspt_id'), 'unique': False}, {'fields' : ('company_id', 'leads.sfdc.Id'), 'unique': False}, {'fields' : ('company_id', 'sfdc_id'), 'unique': False}, {'fields' : ('company_id', 'sfdc_contact_id'), 'unique': False}, {'fields' : ('company_id', 'leads.sfdc.CreatedById'), 'unique': False}, {'fields' : ('company_id', 'leads.mkto.sfdcLeadId'), 'unique': False}, {'fields' : ('company_id', 'leads.mkto.sfdcContactId'), 'unique': False}, {'fields' : ('company_id', 'leads.sfdc.CreatedById'), 'unique': False}, {'fields' : ('company_id', 'leads.sfdc.convertedContactId'), 'unique': False}, {'fields' : ('company_id', 'sfdc_account_id','updated_date'), 'unique': False}, {'fields' : ('company_id', 'leads.mkto.sfdcAccountId'), 'unique': False}, {'fields' : ('company_id', 'leads.mkto.originalSourceType', 'mkto_id', 'source_created_date'), 'unique': False, 'name': 'mkto_source_type'}, {'fields' : ('company_id', 'leads.hspt.properties.salesforceleadid'), 'unique': False}, {'fields' : ('company_id', 'leads.hspt.properties.salesforcecontactid'), 'unique': False}, {'fields' : ('company_id', 'source_source'), 'unique': False}, {'fields' : ('company_id', 'source_source', 'source_created_date'), 'unique': False}, {'fields' : ('company_id', 'source_stage'), 'unique': False}, {'fields' : ('company_id', 'source_stage', 'source_created_date'), 'unique': False}, {'fields' : ('company_id', 'source_company'), 'unique': False},  
                                              {'fields' : ('company_id', 'source_source', 'leads.hspt.properties.hs_analytics_source_data_1', 'leads.hspt.properties.lifecyclestage', 'leads.hspt.versions.lifecyclestage', 'leads.hspt.properties.hs_analytics_first_visit_timestamp'), 'unique': False, 'name': 'new_visit_index'}, {'fields' : ('company_id', 'source_source', 'leads.hspt.properties.hs_analytics_source_data_1', 'leads.hspt.versions.hs_analytics_last_referrer.value', 'leads.hspt.properties.lifecyclestage', 'leads.hspt.properties.hs_analytics_first_visit_timestamp', 'leads.hspt.versions.hs_analytics_last_referrer.timestamp'), 'unique': False, 'name': 'repeat_visit_index'}, {'fields' : ('company_id', 'opportunities.hspt.properties.closedate.value'), 'unique': False, 'name': 'opp_index'}, {'fields' : ('company_id', 'updated_date'), 'unique': False, 'name': 'updated_date_index'}, 'updated_date', 'leads.hspt.properties.hs_analytics_source', 'leads.hspt.properties.hs_analytics_source_data_1', 'leads.hspt.properties.hs_analytics_source_data_2', 'leads.hspt.properties.hs_analytics_first_visit_timestamp', 'leads.hspt.versions.hs_analytics_last_referrer.value', 'leads.hspt.versions.hs_analytics_last_referrer.timestamp', 'leads.hspt.related_contact_vids', {'fields' : ('company_id', 'source_source'), 'unique': False, 'name': 'source_index'}, {'fields' : ('company_id', 'source_source', 'leads.hspt.properties.hs_analytics_source_data_1'), 'unique': False, 'name': 'source_sourcedata1_index'}, {'fields' : ('company_id', 'source_created_date'), 'unique': False, 'name': 'co_sourcecreateddate_index'}, {'fields' : ('company_id', 'mkto_id', 'opportunities.sfdc.CreatedDate', 'leads.sfdc.CreatedById', 'opportunities.sfdc.IsWon'), 'unique': False, 'name': 'mkto_sfdc_opp'}, 
                                              {'fields' : ('company_id', 'mkto_id'), 'unique': False, 'name': 'co_mkto_id'}, {'fields' : ('company_id', 'sfdc_id', 'sfdc_contact_id'), 'unique': False, 'name': 'co_sfdc_ids'}, {'fields' : ('company_id', 'sfdc_id', 'sfdc_contact_id', 'leads.sfdc.CreatedById', 'source_created_date'), 'unique': False, 'name': 'co_sfdc_ids_created'}, {'fields' : ('company_id', 'activities.mkto.activityTypeId'), 'unique': False, 'name': 'co_mkto_activity_type'}, {'fields' : ('company_id', 'hspt_subscriber_date'), 'unique': False}, {'fields' : ('company_id', 'hspt_lead_date'), 'unique': False}, {'fields' : ('company_id', 'hspt_mql_date'), 'unique': False}, {'fields' : ('company_id', 'hspt_sql_date'), 'unique': False}, {'fields' : ('company_id', 'hspt_opp_date'), 'unique': False}, {'fields' : ('company_id', 'hspt_customer_date'), 'unique': False}, {'fields' :  ( 'company_id', 'leads.sfdc.createdById', 'activities.sfdc.CreatedDate', 'activities.sfdc.NewValue', 'activities.sfdc.OldValue'), 'unique': False, 'name': 'sfdc_activity'}, {'fields' : ('company_id', 'sugr_id'), 'unique': False}, {'fields' : ('company_id', 'leads.hspt.properties.first_conversion_event_date'), 'unique': False, 'name': 'first_conversion_date_index'}, {'fields' : ('company_id', 'leads.hspt.properties.recent_conversion_event_date'), 'unique': False, 'name': 'recent_conversion_date_index'}, {'fields' : ('company_id', 'sfdc_id', 'sfdc_contact_id', 'leads.sfdc.CreatedById', 'activities.sfdc.NewValue', 'activities.sfdc.OldValue', 'activities.sfdc.CreatedDate'), 'unique': False, 'name': 'sfdc_activity'}, {'fields' : ('company_id', 'opportunities.sfdc.0', 'opportunities.sfdc.CreatedDate',  'mkto_id', 'leads.mkto.originalSourceType'), 'unique': False, 'name': 'sfdc_opp_0'}, {'fields' : ('company_id', 'mkto_id', 'source_created_date', 'leads.mkto.originalSourceType'), 'unique': False, 'name': 'mkto_created'}, {'fields' : ('company_id', 'mkto_id', 'memberships'), 'unique': False, 'name': 'mkto_memberships'}, ], 
                'ordering':['-updated_date'], 'abstract': True}

class Lead(LeadBase):
    pass

class LeadWithForm(LeadBase):
    form = StringField()