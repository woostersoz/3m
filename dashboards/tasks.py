from __future__ import absolute_import, division
from datetime import timedelta, date, datetime
import pytz
import os, copy, requests, shutil, pwd, grp
import time, calendar
import urllib2
from dateutil import tz
import numpy, math

from collections import OrderedDict
from operator import itemgetter

from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from rest_framework.response import Response
from mongoengine.queryset.visitor import Q

from leads.models import Lead
from campaigns.models import Campaign, EmailEvent
from company.models import CompanyIntegration
from accounts.models import Account
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from social.models import PublishedTweet, FbAdInsight, FbPageInsight
from analytics.models import AnalyticsData, AnalyticsIds
from websites.models import Traffic
from superadmin.models import SuperUrlMapping, SuperIntegration, SuperCountry
from mmm.models import ImageFile
from mmm.views import _date_from_str, _str_from_date
from screamshot.utils import render_template

from django.utils.timezone import get_current_timezone
from geopy.geocoders import Nominatim, GoogleV3

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")

@app.task
def calculateMktoDashboards(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    print 'in Mkto dashboards'
    method_map = {"funnel": mkto_funnel, "waterfall_chart": mkto_waterfall }
    method_map[chart_name](user_id, company_id, chart_name, mode, _date_from_str(start_date, 'short')) # the conversion from string to date object is done here
    try:
        message = 'Data retrieved for ' + chart_title + ' - ' + mode + ' run'
        notification = Notification()
        #notification.company_id = company_id
        notification.owner = user_id
        notification.module = 'Dashboards'
        notification.type = 'Background task' 
        notification.method = os.path.basename(__file__)
        notification.message = message
        notification.success = True
        notification.read = False
        notification.save()
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    


@app.task
def calculateSfdcDashboards(user_id=None, company_id=None):
    pass

@app.task
def calculateHsptDashboards(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    method_map = {"social_roi" : hspt_social_roi, "funnel" : hspt_funnel, "waterfall_chart": None, "form_fills": hspt_form_fills,}
    method_map[chart_name](user_id, company_id, chart_name, mode, _date_from_str(start_date, 'short')) # the conversion from string to date object is done here
    try:
        message = 'Data retrieved for ' + chart_title + ' - ' + mode + ' run'
        notification = Notification()
        #notification.company_id = company_id
        notification.owner = user_id
        notification.module = 'Dashboards'
        notification.type = 'Background task' 
        notification.method = os.path.basename(__file__)
        notification.message = message
        notification.success = True
        notification.read = False
        notification.save()
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    

@app.task
def calculateBufrAnalytics(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    method_map = { "tw_performance" : bufr_tw_performance}
    method_map[chart_name](user_id, company_id, chart_name, mode, _date_from_str(start_date, 'short')) # the conversion from string to date object is done here
    try:
        message = 'Data retrieved for ' + chart_title + ' - ' + mode + ' run'
        notification = Notification()
        #notification.company_id = company_id
        notification.owner = user_id
        notification.module = 'Analytics'
        notification.type = 'Background task' 
        notification.method = os.path.basename(__file__)
        notification.message = message
        notification.success = True
        notification.read = False
        notification.save()
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    
        
@app.task
def calculateGoogAnalytics(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    method_map = { "google_analytics" : google_analytics}
    method_map[chart_name](user_id, company_id, chart_name, mode, _date_from_str(start_date, 'short')) # the conversion from string to date object is done here
    try:
        message = 'Data retrieved for ' + chart_title + ' - ' + mode + ' run'
        notification = Notification()
        #notification.company_id = company_id
        notification.owner = user_id
        notification.module = 'Analytics'
        notification.type = 'Background task' 
        notification.method = os.path.basename(__file__)
        notification.message = message
        notification.success = True
        notification.read = False
        notification.save()
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    


# begin MKTO dashboards

def mkto_funnel(user_id, company_id, chart_name, mode, start_date):
#MKTO Funnel dashboard aggregation
    print 'starting Mkto funnel'
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        utc_day_start = local_start_date.astimezone(pytz.timezone('UTC'))
        
        delta = timedelta(days=1)
        e = local_end_date
#         days_list = []
#         delta = local_end_date - local_start_date
#         for i in range(delta.days + 1):
#             days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
        
       
        #get all CRM systems
        crm_systems = SuperIntegration.objects(system_type='CRM').only('code')
        if crm_systems is None:
            return
        crm_systems_list = [d['code'] for d in crm_systems]
        crm_system_code = None
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        #check which CRM system for this company
        if existingIntegration is None or 'integrations' not in existingIntegration:
            raise ValueError('No integration data found'
                             )
        for key, value in existingIntegration['integrations'].items():
            if key in crm_systems_list:
                crm_system_code = key
                break
        if crm_system_code is None:
            return []
        
        #query variables
        source_created_date_qry = 'source_created_date'
        company_id_qry = 'company_id'
        source_metric_name_qry = 'source_metric_name'
        period_qry = 'data__period'
        end_time_qry = 'data__values__end_time'
        source_page_id_qry = 'source_page_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        created_date_end_qry = 'source_created_date__lte'
        created_date_start_qry = 'source_created_date__gte'
        mkto_id_qry = 'mkto_id__exists'
        
        #general variables
        chart_name = 'funnel' #this also covers the Waterfall, for Marketo
        sync_to_sfdc_activity_type_id = 19 #mkto activity type id
        change_value_activity_type_id = 13 #mkto activity type id
        convert_to_opp_activity_type_id = 21 #mkto activity type id
        add_to_opp_activity_type_id = 34 #mkto activity type id
        mkto_primary_attribute_value = 'Lead Status'
        collection = Lead._get_collection()
        data = {}
        ids = {}
        statuses = {}
        
        #get the status config
        if crm_system_code == 'sfdc':
            #existingIntegration = CompanyIntegration.objects(company_id = company_id).first()   
            if 'sfdc' in existingIntegration['integrations']:
                try:
                    statuses['sal'] = existingIntegration['mapping']['sal_statuses']
                    statuses['sql'] = existingIntegration['mapping']['sql_statuses']
                    statuses['recycle'] = existingIntegration['mapping']['recycle_statuses']
                    statuses['mql'] = existingIntegration['mapping']['mql_statuses'] 
                    mkto_sync_user = existingIntegration['mapping']['mkto_sync_user']
                except Exception as e:
                    print 'Stage details not completely defined for company'
                    raise ValueError('Stage details not completely defined for company')
            
        #the sequence of stages/statuses
        #status_subsequent = {'': ['Assigned', 'Working', 'Qualified'], 'Assigned': ['Working', 'Qualified'], 'Working': ['Qualified',]}
        #stage_status_mapping = {'Pre MQL': ['', 'Assigned', 'Working', 'Marketing Nurture', 'Unqualified'], 'MQL': ['Qualified']}
        #detour_statuses = {'Unqualified', 'Blitz', 'Marketing Nurture'}
        
        #root names of stages 
        stages_root = ['premql', 'mql', 'sal', 'sql', 'opps', 'closedwon', 'closedlost']
        functions = ['mktg', 'sales']
        
        #precollect all MQLs created by Marketing i.e. were synched to CRM and did not originate from CRM
        mkto_leads_mql_mktg = collection.find({'company_id' : int(company_id), 'activities.mkto.activityTypeId' : sync_to_sfdc_activity_type_id, 'leads.mkto.originalSourceType' : {'$ne': 'salesforce.com'}}) #, 'source_created_date': {'$gte' : utc_day_start}})
        mkto_leads_mql_mktg_list = list(mkto_leads_mql_mktg)
        mkto_leads_mql_mktg2 = collection.find({'company_id' : int(company_id), 'leads.mkto.originalSourceType' : {'$ne': 'salesforce.com'}, 'source_created_date': {'$gte' : utc_day_start}}) #, 'source_created_date': {'$gte' : utc_day_start}})
        mkto_leads_mql_mktg_list2 = list(mkto_leads_mql_mktg2)
        #print 'found  mql leads ' + str(len(mkto_leads_mql_mktg_list))
        
        #daily loop begins
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            #data = {'num_mktg_premql' : 0, 'num_sales_premql' : 0, 'num_mktg_mql': 0, 'num_sales_mql': 0, 'num_mktg_sal': 0, 'num_sales_sal': 0, 'num_mktg_sql': 0, 'num_sales_sql': 0, 'num_mktg_opps': 0, 'num_sales_opps': 0, 'num_mktg_closedwon' : 0, 'num_sales_closedwon' : 0, 'num_mktg_closedlost' : 0, 'num_sales_closedlost' : 0}
            #ids = {}
            results = {}
            
            inflow_leads_count = {'premql' : 0, 'mql' : 0, 'sal' : 0, 'sql' : 0, 'opps' : 0, 'closedwon' : 0, 'closedlost' : 0, 'mktg_premql' : 0, 'sales_premql' : 0, 'mktg_mql': 0, 'sales_mql': 0, 'mktg_sal': 0, 'sales_sal': 0, 'mktg_sql': 0, 'sales_sql': 0, 'mktg_opps': 0, 'sales_opps': 0, 'mktg_closedwon' : 0, 'sales_closedwon' : 0, 'mktg_closedlost' : 0, 'sales_closedlost' : 0}
            outflow_leads_count = {'premql' : 0, 'mql' : 0, 'sal' : 0, 'sql' : 0, 'opps' : 0, 'closedwon' : 0, 'closedlost' : 0, 'mktg_premql' : 0, 'sales_premql' : 0, 'mktg_mql': 0, 'sales_mql': 0, 'mktg_sal': 0, 'sales_sal': 0, 'mktg_sql': 0, 'sales_sql': 0, 'mktg_opps': 0, 'sales_opps': 0, 'mktg_closedwon' : 0, 'sales_closedwon' : 0, 'mktg_closedlost' : 0, 'sales_closedlost' : 0}
            inflow_leads_ids = {'mktg_premql' : set(), 'sales_premql' : set(), 'mktg_mql': set(), 'sales_mql': set(), 'mktg_sal': set(), 'sales_sal': set(), 'mktg_sql': set(), 'sales_sql': set(), 'mktg_opps': set(), 'sales_opps': set(), 'mktg_closedwon' : set(), 'sales_closedwon' : set(), 'mktg_closedlost' : set(), 'sales_closedlost' : set()}
            outflow_leads_ids = {'mktg_premql' : set(), 'sales_premql' : set(), 'mktg_mql': set(), 'sales_mql': set(), 'mktg_sal': set(), 'sales_sal': set(), 'mktg_sql': set(), 'sales_sql': set(), 'mktg_opps': set(), 'sales_opps': set(), 'mktg_closedwon' : set(), 'sales_closedwon' : set(), 'mktg_closedlost' : set(), 'sales_closedlost' : set()}
            duration = {'premql' : 0, 'mql' : 0, 'sal' : 0, 'sql' : 0, 'opps' : 0, 'closedwon' : 0, 'closedlost' : 0, 'mktg_premql' : 0, 'sales_premql' : 0, 'mktg_mql': 0, 'sales_mql': 0, 'mktg_sal': 0, 'sales_sal': 0, 'mktg_sql': 0, 'sales_sql': 0, 'mktg_opps': 0, 'sales_opps': 0, 'mktg_closedwon' : 0, 'sales_closedwon' : 0, 'mktg_closedlost' : 0, 'sales_closedlost' : 0}
            
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            
            #get all leads which were created before the start of today regardless of in MA or CRM
            print 'getting existed count'
            existed_count_mktg = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'leads.mkto.originalSourceType' : {'$ne': 'salesforce.com'}, 'source_created_date': {'$lt' : utc_day_start}}).count()
                
            #get all leads that were created in this time period by source and stage regardless of in MA or CRM
            print 'getting all leads created today'
            querydict = {company_id_qry: company_id, created_date_start_qry: utc_day_start, created_date_end_qry: utc_day_end} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            leads_created_source = Lead.objects(**querydict).item_frequencies('source_source')
            if None in leads_created_source: #replace None key with 'Unknown' else Mongo will throw error upon save
                leads_created_source['Unknown'] = leads_created_source[None]
                leads_created_source.pop(None, None)
            #print 'sources are ' + str(list(leads_created_source))
            leads_created_stage = Lead.objects(**querydict).item_frequencies('source_status')
            if None in leads_created_stage: #replace None key with 'Unknown' else Mongo will throw error upon save
                leads_created_stage['Unknown'] = leads_created_stage[None]
                leads_created_stage.pop(None, None)
            print 'stages are ' + str(list(leads_created_stage))
            created_count = Lead.objects(**querydict).count()
            #created_count = Lead.objects(**querydict).count()
            
            if crm_system_code == 'sfdc': #if Salesforce
                
                #mktg_premql - inflows - find all leads in MKTO that were created today and did not come from SFDC
                print 'getting mktg_premql'
                mkto_leads_raw = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'leads.mkto.originalSourceType' : {'$ne': 'salesforce.com'}, 'source_created_date': {'$gte' : utc_day_start, '$lte': utc_day_end}})
                mkto_leads_raw_list = list(mkto_leads_raw)
                #inflow_leads_count['mktg_premql'] = len(mkto_leads_raw_list) 
                inflow_leads_ids['mktg_premql'] = [d['mkto_id'] for d in mkto_leads_raw_list]
                print 'mktg premql list is ' + str(inflow_leads_ids['mktg_premql'])
                #mktg_premql - outflows - should this include other status changes apart from inflows to mktg_mql?
                #done while calculating mql inflows below
                
                #MA related metrics other than premql
                print 'getting mktg mql'
                utc_date_string_start = _str_from_date(utc_day_start)
                utc_date_string_end = _str_from_date(utc_day_end)
                #print 'utc start string for SFDC sync is ' + utc_date_string_start
                #print 'utc end string is ' + utc_date_string_end
                #deprecated - check synch was successful - which means Lead Status activity has to occur at the same time as the sync
                for lead in mkto_leads_mql_mktg_list2 : #list2 contains all leads created in MKTO on/after the start of the initial run
                    this_lead_done = False
                    newStatus = ''
                    oldStatus = ''
                    if 'mkto' in lead['activities']:
                        for d in lead['activities']['mkto']: 
                            #MQL inflows
                            if d['activityTypeId'] == sync_to_sfdc_activity_type_id and d['activityDate'] >= utc_date_string_start and d['activityDate'] <= utc_date_string_end:
                                #for c in lead['activities']['mkto']:
                                    #if c['activityTypeId'] == change_value_activity_type_id and c['activityDate'] == d['activityDate']:
                                inflow_leads_ids['mktg_mql'].add(lead['mkto_id'])
                                #inflow_leads_count['mktg_mql'] += 1
                                #mktg_premql - outflow
                                outflow_leads_ids['mktg_premql'].add(lead['mkto_id']) #NOTE - assumption is outflow for preMql == inflow for MQL
                                #outflow_leads_count['mktg_premql'] += 1 #NOTE - assumption is outflow for preMql == inflow for MQL
                                #duration['mktg_premql'] = ((duration['mktg_premql'] * (outflow_leads_count['mktg_premql'] - 1)) + (_date_from_str(d['activityDate'], 'utc') - lead['source_created_date']).days) / outflow_leads_count['mktg_premql']
                                duration['mktg_premql'] +=  max(0, (_date_from_str(d['activityDate'], 'utc') - lead['source_created_date']).days)
                                #this_lead_done = True
                                #break
    #                         elif (d['activityTypeId'] == convert_to_opp_activity_type_id or d['activityTypeId'] == add_to_opp_activity_type_id) and d['activityDate'] >= utc_date_string_start and d['activityDate'] <= utc_date_string_end:  
    #                             #Opp inflows - this is here because we are clubbing all 'activity' related checks here. 
    #                             inflow_leads_ids['mktg_opps'].append(lead['mkto_id'])
    #                             inflow_leads_count['mktg_opps'] += 1
                    #other inflows and outflows - 'status' related checks
                    if 'mkto' in lead['statuses']:
                        for index, d in enumerate(lead['statuses']['mkto']):
                            newStatus = d['newStatus']
                            oldStatus = d['oldStatus']
                            if d['activityTypeId'] == change_value_activity_type_id and d['primaryAttributeValue'] == mkto_primary_attribute_value and d['activityDate'] >= utc_date_string_start and d['activityDate'] <= utc_date_string_end:  
                                #first calculate the difference between this status date and the previous state date (or lead created date if no previous status change found)
                                if index + 1 >= len(lead['statuses']['mkto']): #this is the last status - nothing earlier than this so take created date
                                    durn =  max(0, (_date_from_str(d['activityDate'], 'utc') - lead['source_created_date']).days)
                                else:
                                    durn =  max(0, (_date_from_str(d['activityDate'], 'utc') - _date_from_str(lead['statuses']['mkto'][index+1]['activityDate'], 'utc')).days) # get the date from the immediate earlier status change activity
                                #print 'mkto durn is ' + str(durn)
                                #MQL outflows
                                if (newStatus in statuses['sal'] and oldStatus in statuses['mql']) or (newStatus in statuses['recycle'] and oldStatus in statuses['mql']):
                                    outflow_leads_ids['mktg_mql'].add(lead['mkto_id'])
                                    #outflow_leads_count['mktg_mql'] += 1
                                    #duration['mktg_mql'] = ((duration['mktg_mql'] * (outflow_leads_count['mktg_mql'] - 1)) + durn) / outflow_leads_count['mktg_mql']
                                    duration['mktg_mql'] += durn 
                                #SAL inflows
                                if newStatus in statuses['sal'] and oldStatus not in statuses['sal']:
                                    inflow_leads_ids['mktg_sal'].add(lead['mkto_id'])
                                    #inflow_leads_count['mktg_sal'] += 1
                                #SAL outflows
                                if oldStatus in statuses['sal'] and newStatus not in statuses['sal']:
                                    outflow_leads_ids['mktg_sal'].add(lead['mkto_id'])
                                    #outflow_leads_count['mktg_sal'] += 1
                                    #duration['mktg_sal'] = ((duration['mktg_sal'] * (outflow_leads_count['mktg_sal'] - 1)) + durn) / outflow_leads_count['mktg_sal']
                                    duration['mktg_sal'] += durn
                                #SQL inflows
                                if newStatus in statuses['sql'] and oldStatus not in statuses['sql']:
                                    inflow_leads_ids['mktg_sql'].add(lead['mkto_id'])
                                    #inflow_leads_count['mktg_sql'] += 1
                                #SQL outflows
                                if oldStatus in statuses['sql'] and newStatus not in statuses['sql']:
                                    outflow_leads_ids['mktg_sql'].add(lead['mkto_id'])
                                    #outflow_leads_count['mktg_sql'] += 1 
                                    #duration['mktg_sql'] = ((duration['mktg_sql'] * (outflow_leads_count['mktg_sql'] - 1)) + durn) / outflow_leads_count['mktg_sql']
                                    duration['mktg_sql'] += durn
                    
                                       
                #deal with all Opps related metrics in CRM below
                
                # all CRM related metrics start here
                print 'going to sales'
                #branch to sfdc module for the rest of the metrics  
                inflow_leads_ids, outflow_leads_ids, inflow_leads_count, outflow_leads_count, duration, closed_deal_value, lost_deal_value, max_deal_value, existed_count_sales = sfdc_waterfall_sub(user_id = user_id, company_id = company_id, utc_day_start = utc_day_start, utc_day_end = utc_day_end, date = date, caller = 'mkto', statuses = statuses, mkto_sync_user = mkto_sync_user, inflow_leads_ids = inflow_leads_ids, outflow_leads_ids=outflow_leads_ids, inflow_leads_count=inflow_leads_count, outflow_leads_count=outflow_leads_count, duration=duration)
                print 'back from sales'
                existed_count = existed_count_sales + existed_count_mktg
                #calculate counts and durations here to prevent double counting in the sales sub-module code
                for key, value in inflow_leads_count.items():
                    if key in inflow_leads_ids:
                        inflow_leads_count[key] = len(inflow_leads_ids[key])
                for key, value in outflow_leads_count.items():
                    if key in outflow_leads_ids:
                        outflow_leads_count[key] = len(outflow_leads_ids[key])
                        #if outflow_leads_count[key] > 0:
                        #    duration[key] = duration[key] / outflow_leads_count[key]
                
                #consolidate mktg and sales counts into summary counts
                for stage in stages_root:
                    durn = 0
                    for func in functions:
                        inflow_leads_count[stage] += inflow_leads_count[func + '_' + stage]
                        outflow_leads_count[stage] += outflow_leads_count[func + '_' + stage]
                        durn += duration[func + '_' + stage] #* outflow_leads_count[func + '_' + stage]
                        if outflow_leads_count[func + '_' + stage] > 0:
                            duration[func + '_' + stage] = math.ceil(duration[func + '_' + stage] / outflow_leads_count[func + '_' + stage]) # divide here since so far duration only has the totals
                    if outflow_leads_count[stage] > 0:
                        duration[stage] = math.ceil(durn / outflow_leads_count[stage])
                
                #print 'inflow counts are ' + str(inflow_leads_count)
                #print 'outflow counts are ' + str(outflow_leads_count)
                #print 'durations are ' + str(duration)
                #continue
             
                results['data'] = {'existed_count': existed_count, 'created_count': created_count, 'created_source' : leads_created_source, 'inflow_count': inflow_leads_count, 'outflow_count': outflow_leads_count, 'outflow_duration': duration, 'num_deals_closed' : inflow_leads_count['closedwon'], 'closed_deal_value' : closed_deal_value, 'lost_deal_value': lost_deal_value, 'max_deal_value': max_deal_value, 'created_stage' : leads_created_stage} #'created_stage' : leads_created_stage,  , 
                results['ids'] = {}
                results['ids']['inflow'] = inflow_leads_ids
                results['ids']['outflow'] = outflow_leads_ids
                #results['ids']['deals'] = deals_list
                #print 'results ' + str(results)
                
                #prepare analytics collections           
                queryDict = {company_id_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: date}
                analyticsData = AnalyticsData.objects(**queryDict).first()
                if analyticsData is None:
                    analyticsData = AnalyticsData()
                    analyticsData.system_type = 'MA'
                    analyticsData.company_id = company_id  
                    analyticsData.chart_name = chart_name
                    analyticsData.date = date
                    analyticsData.results = {}
                    analyticsData.save()
                      
                analyticsIds = AnalyticsIds.objects(**queryDict).first()
                if analyticsIds is None:
                    analyticsIds = AnalyticsIds()
                    analyticsIds.system_type = 'MA'
                    analyticsIds.company_id = company_id  
                    analyticsIds.chart_name = chart_name
                    analyticsIds.date = date
                    analyticsIds.results = {}
                    analyticsIds.save()
                     
                print 'results are ' + str(results)
                analyticsData.results = results['data']
                analyticsIds.results['inflow'] = results['ids']['inflow']
                analyticsIds.results['outflow'] = results['ids']['outflow']
                analyticsIds.results['deals'] = [] #results['ids']['deals']
                results = {}
                print 'saving' 
                try:
                    AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                    print 'saved AD'
                    AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
                except Exception as e:
                    print 'exception while saving analytics data: ' + str(e)
                    continue
                print 'saved'
                        
            
            else: # if not Salesforce
                return []
        
        
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    

# chart- Waterfall chart
def mkto_waterfall(user_id, company_id, chart_name, mode, start_date):
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        delta = timedelta(days=1)
        e = local_end_date
#         days_list = []
#         delta = local_end_date - local_start_date
#         for i in range(delta.days + 1):
#             days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
        
       
        #get all CRM systems
        crm_systems = SuperIntegration.objects(system_type='CRM').only('code')
        if crm_systems is None:
            return
        crm_systems_list = [d['code'] for d in crm_systems]
        crm_system_code = None
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        #check which CRM system for this company
        if existingIntegration is None or 'integrations' not in existingIntegration:
            raise ValueError('No integration data found'
                             )
        for key, value in existingIntegration['integrations'].items():
            if key in crm_systems_list:
                crm_system_code = key
                break
        if crm_system_code is None:
            return []
        
        #query variables
        source_created_date_qry = 'source_created_date'
        company_id_qry = 'company_id'
        source_metric_name_qry = 'source_metric_name'
        period_qry = 'data__period'
        end_time_qry = 'data__values__end_time'
        source_page_id_qry = 'source_page_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        created_date_end_qry = 'source_created_date__lte'
        created_date_start_qry = 'source_created_date__gte'
        
        #general variables
        chart_name = 'waterfall'
        sync_to_sfdc_activity_type_id = 19 #mkto activity type id
        change_value_activity_type_id = 13 #mkto activity type id
        collection = Lead._get_collection()
        data = {}
        ids = {}
        statuses = {}
        
        #get the status config
        if crm_system_code == 'sfdc':
            existingIntegration = CompanyIntegration.objects(company_id = company_id).first()   
            if 'sfdc' in existingIntegration['integrations']:
                try:
                    statuses['sal'] = existingIntegration['mapping']['sal_statuses']
                    statuses['sql'] = existingIntegration['mapping']['sql_statuses']
                    statuses['recycle'] = existingIntegration['mapping']['recycle_statuses']
                    statuses['mql'] = existingIntegration['mapping']['mql_statuses'] 
                    mkto_sync_user = existingIntegration['mapping']['mkto_sync_user']
                except Exception as e:
                    print 'Stage details not completely defined for company'
                    raise ValueError('Stage details not completely defined for company')
            
            mkto_leads_mql_all = collection.find({'company_id' : int(company_id), 'activities.mkto.activityTypeId' : sync_to_sfdc_activity_type_id})
            mkto_leads_mql_all_list = list(mkto_leads_mql_all)
            print 'found  mql leads ' + str(len(mkto_leads_mql_all_list))
        
        #daily loop begins
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            data = {'num_mktg_raw_leads' : 0, 'num_sales_raw_leads' : 0, 'num_mql': 0, 'num_mktg_sal': 0, 'num_sales_sal': 0, 'num_mktg_sql': 0, 'num_sales_sql': 0, 'num_mktg_opps': 0, 'num_sales_opps': 0, 'num_mktg_closed_deals' : 0, 'num_sales_closed_deals' : 0}
            ids = {}
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            
            if crm_system_code == 'sfdc': #if Salesforce
                #find all leads in MKTO that did not come from a SFDC Lead or Contact or were not synched into SFDC and were created today 
                mkto_leads_raw = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'leads.mkto.sfdcLeadId' : {'$exists': False}, 'leads.mkto.sfdcContactId' : {'$exists': False}, 'source_created_date': {'$gte' : utc_day_start, '$lte': utc_day_end}})
                mkto_leads_raw_list = list(mkto_leads_raw)
                data['num_mktg_raw_leads'] = len(mkto_leads_raw_list) 
                ids['mktg_raw_leads'] = [d['mkto_id'] for d in mkto_leads_raw_list]
                #find all leads that were synched to CRM today (successfully - which means Lead Status activity has to occur at the same time as the sync)
                utc_date_string_start = _str_from_date(utc_day_start)
                utc_date_string_end = _str_from_date(utc_day_end)
                print 'utc start string is ' + utc_date_string_start
                print 'utc end string is ' + utc_date_string_end
                # get all leads with sync to SFDC activities for today
                sync_activities_list = []
                for lead in mkto_leads_mql_all_list :
                    this_lead_done = False
                    for d in lead['activities']['mkto']:
                        if d['activityTypeId'] == sync_to_sfdc_activity_type_id and d['activityDate'] >= utc_date_string_start and d['activityDate'] <= utc_date_string_end:
                            for c in lead['activities']['mkto']:
                                if c['activityTypeId'] == change_value_activity_type_id and c['activityDate'] == d['activityDate']:
                                    sync_activities_list.append({'lead_id': lead['mkto_id'], 'activity': d})
                                    this_lead_done = True
                                    break
                        if this_lead_done:
                            break #stop processing this lead if one activity already found
                print 'sync activities are ' + str(sync_activities_list) 
                #now that all leads have been processed for MQL for today, count them
                data['num_mql'] =  len(sync_activities_list)    
                ids['mql'] = [d['lead_id'] for d in sync_activities_list]
                print 'going to sales'
                #branch to sfdc module for the rest of the metrics  
                sales_data, sales_ids = sfdc_waterfall_sub(user_id = user_id, company_id = company_id, utc_day_start = utc_day_start, utc_day_end = utc_day_end, date = date, caller = 'mkto', statuses = statuses, mkto_sync_user = mkto_sync_user)
                print 'back from sales'
                for key, value in sales_data.items():
                    data[key] = sales_data[key]
                    
                for key, value in sales_ids.items():
                    ids[key] = sales_ids[key]
                    
                print 'data for ' + date + ': ' + str(data)
             
                #prepare analytics collections           
                queryDict = {company_id_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: date}
                analyticsData = AnalyticsData.objects(**queryDict).first()
                if analyticsData is None:
                    analyticsData = AnalyticsData()
                    analyticsData.system_type = 'MA'
                    analyticsData.company_id = company_id  
                    analyticsData.chart_name = chart_name
                    analyticsData.date = date
                    analyticsData.results = {}
                    analyticsData.save()
                      
                analyticsIds = AnalyticsIds.objects(**queryDict).first()
                if analyticsIds is None:
                    analyticsIds = AnalyticsIds()
                    analyticsIds.system_type = 'MA'
                    analyticsIds.company_id = company_id  
                    analyticsIds.chart_name = chart_name
                    analyticsIds.date = date
                    analyticsIds.results = {}
                    analyticsIds.save()
                     
                #print 'results are ' + str(results)
                analyticsData.results = data
                analyticsIds.results = ids
                print 'saving' 
                try:
                    AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                    AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
                except Exception as e:
                    print 'exception while saving analytics data: ' + str(e)
                    continue
                print 'saved'       
          
#                 sync_activities_list = [lead for lead in mkto_leads_mql_list for d in lead['activities']['mkto'] if d['activityTypeId'] == sync_to_sfdc_activity_type_id and d['activityDate'] >= utc_date_string_start and d['activityDate'] <= utc_date_string_end 
#                                         for c in d['activities']['mkto'] if c['activityTypeId'] == change_value_activity_type_id and c['activityDate'] == d['activityDate']]
#                 print 'original sync activities are ' + str(sync_activities_list)
#                 # now check that there was a successful lead status change for the same time as the sync activity else the sync failed
#                 if sync_activities_list:
#                     sync_activities_list[:] = [d for d in sync_activities_list for c in d['activities']['mkto'] if c['activityTypeId'] == change_value_activity_type_id and c['activityDate'] == d['activityDate']]
#                     print 'lead id is ' + str(lead['mkto_id'])
#                     print 'revised sync activities are ' + str(sync_activities_list)
                        
            
            else: # if not Salesforce
                return []
        
        
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
def sfdc_waterfall_sub(user_id, company_id, utc_day_start, utc_day_end, date, caller,  statuses, mkto_sync_user, inflow_leads_ids, outflow_leads_ids, inflow_leads_count, outflow_leads_count, duration):
    try:
        data = {'num_sales_raw_leads' : 0, 'num_mktg_sal': 0, 'num_mktg_sql': 0, 'num_sales_sal': 0, 'num_sales_sql': 0, 'num_mktg_opps': 0, 'num_sales_opps': 0, 'num_mktg_closed_deals' : 0, 'num_sales_closed_deals' : 0}
        ids = {}
        
        #print 'sal status is ' + sfdc_sal_status    
        #find all raw leads created directly in SFDC today
        collection = Lead._get_collection()
        if caller == 'sfdc':
            sfdc_leads_raw = collection.find({'company_id' : int(company_id), 'source_created_date': {'$gte' : utc_day_start, '$lte': utc_day_end}})
            sfdc_leads_raw_list = list(sfdc_leads_raw)
            data['num_sales_raw_leads'] = len(sfdc_leads_raw_list) 
            ids['sales_raw_leads'] = [d['sfdc_id'] for d in sfdc_leads_raw_list]
        elif caller == 'mkto':
            print 'start date is ' + str(utc_day_start)
            print 'end date is ' + str(utc_day_end)
            sfdc_leads_existed = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'source_created_date': {'$lt' : utc_day_start}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            existed_count_sales = len(list(sfdc_leads_existed))
#             sfdc_leads_raw_list = list(sfdc_leads_raw)
#             inflow_leads_count['sales_mql'] += len(sfdc_leads_raw_list) 
#             print 'sfdc list is ' + str([d['sfdc_id'] for d in sfdc_leads_raw_list])
#             inflow_leads_ids['sales_mql'] = [d['sfdc_id'] for d in sfdc_leads_raw_list]
#             print 'passed sales mql'
        
        #convert dates to strings for SAL and SQL queries
        utc_day_start_string = datetime.strftime(utc_day_start, '%Y-%m-%dT%H-%M-%S.000+0000')
        utc_day_end_string = datetime.strftime(utc_day_end, '%Y-%m-%dT%H-%M-%S.000+0000')
        # find all leads that went into SAL status today 
        if caller == 'sfdc':
            data['num_mktg_sal'] = 0
            data['num_mktg_sql'] = 0
            sfdc_sales_sal = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'activities.sfdc': {'$elemMatch' : {'NewValue' :{'$in' : statuses['sal']}, 'OldValue' :{'$nin' : statuses['sal']}, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}})
            sfdc_sales_sal_list = list(sfdc_sales_sal)
            data['num_sales_sal'] = len(sfdc_sales_sal_list)
            ids['sales_sal'] = [d['sfdc_id'] for d in sfdc_sales_sal_list]
        
        elif caller == 'mkto':
            #sales_sal - inflow
            print 'getting into sales_sal'
            # get leads and contacts
            sfdc_sales_sal = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'activities.sfdc': {'$elemMatch' : {'NewValue' :{'$in' : statuses['sal']}, 'OldValue' :{'$nin' : statuses['sal']}, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})#.distinct('_id')
            sfdc_sales_sal_list = list(sfdc_sales_sal)
            for lead in sfdc_sales_sal_list :
                    if 'sfdc_contact_id' in lead:
                        inflow_leads_ids['sales_sal'].add(lead['sfdc_contact_id'])
                    elif 'sfdc_id' in lead:
                        inflow_leads_ids['sales_sal'].add(lead['sfdc_id'])
            #inflow_leads_count['sales_sal'] = len(inflow_leads_ids['sales_sal'])
            #sales_sal - outflow
            #get leads and contacts
            sfdc_sales_sal = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'activities.sfdc': {'$elemMatch' : {'$or': [{'NewValue' :{'$in' : statuses['sql']}}, {'NewValue' :{'$in' : statuses['recycle']}}] , 'OldValue' :{'$in' : statuses['sal']}, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})#.distinct('_id')
            sfdc_sales_sal_list = list(sfdc_sales_sal)
            for lead in sfdc_sales_sal_list :
                    if 'sfdc_contact_id' in lead:
                        outflow_leads_ids['sales_sal'].add(lead['sfdc_contact_id'])
                    elif 'sfdc_id' in lead:
                        outflow_leads_ids['sales_sal'].add(lead['sfdc_id'])
                    for a in lead['activities']['sfdc']:
                        if a['Field'] == 'Status' and (a['NewValue'] in statuses['sql'] or a['NewValue'] in statuses['recycle']) and a['OldValue'] in statuses['sal'] and a['CreatedDate'] >= utc_day_start_string and a['CreatedDate'] <= utc_day_end_string and lead['leads']['sfdc']['CreatedById'] != mkto_sync_user:
                            durn = (_date_from_str(a['CreatedDate']) - lead['source_created_date']).days
                            print 'durn is ' + str(durn)
                            duration['sales_sal'] += max(0, durn) #add all the durations together 
            #outflow_leads_count['sales_sal'] = len(outflow_leads_ids['sales_sal'])
            #calculate average duration
            #if outflow_leads_count['sales_sal'] > 0:
                #duration['sales_sal'] = duration['sales_sal'] / outflow_leads_count['sales_sal']
            print 'finished looping sales_sal_list'
            #sales_sql - inflow
            # get leads and contacts
            sfdc_sales_sql = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'activities.sfdc': {'$elemMatch' : {'NewValue' :{'$in' : statuses['sql']}, 'OldValue' :{'$nin' : statuses['sql']}, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})#.distinct('_id')
            sfdc_sales_sql_list = list(sfdc_sales_sql)
            for lead in sfdc_sales_sql_list :
                    if 'sfdc_contact_id' in lead:
                        inflow_leads_ids['sales_sql'].add(lead['sfdc_contact_id'])
                    elif 'sfdc_id' in lead:
                        inflow_leads_ids['sales_sql'].add(lead['sfdc_id'])
            #inflow_leads_count['sales_sql'] = len(inflow_leads_ids['sales_sql'])
            #sales_sql - outflow - need to consider the latest status (source_status) of the lead or status before it converted to an opp
            # get leads and contacts
            sfdc_sales_sql = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'activities.sfdc': {'$elemMatch' : {'NewValue' :{'$in' : statuses['recycle']}, 'OldValue' :{'$in' : statuses['sql']}, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})#.distinct('_id')
            sfdc_sales_sql_list = list(sfdc_sales_sql)
            for lead in sfdc_sales_sql_list :
                    if 'sfdc_contact_id' in lead:
                        outflow_leads_ids['sales_sql'].add(lead['sfdc_contact_id'])
                    elif 'sfdc_id' in lead:
                        outflow_leads_ids['sales_sql'].add(lead['sfdc_id'])
                    for a in lead['activities']['sfdc']:
                        if a['Field'] == 'Status' and a['NewValue'] in statuses['recycle'] and a['OldValue'] in statuses['sql'] and a['CreatedDate'] >= utc_day_start_string and a['CreatedDate'] <= utc_day_end_string and lead['leads']['sfdc']['CreatedById'] != mkto_sync_user:
                            durn = (_date_from_str(a['CreatedDate']) - lead['source_created_date']).days
                            duration['sales_sql'] +=  max(0, durn) #add all the durations together 
                            print 'durn is ' + str(durn)
            #outflow_leads_count['sales_sql'] = len(outflow_leads_ids['sales_sql'])
            #calculate average duration
            #if outflow_leads_count['sales_sql'] > 0:
                #duration['sales_sql'] = duration['sales_sql'] / outflow_leads_count['sales_sql']
            print 'finished looping sales_sql_list'            
            #mktg_opps
            sfdc_mktg_opps = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'opportunities.sfdc.0' : {'$exists': True},  'opportunities.sfdc.CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'leads.mkto.originalSourceType' : {'$ne': 'salesforce.com'} })
            sfdc_mktg_opps_list = list(sfdc_mktg_opps)
            for lead in sfdc_mktg_opps_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CreatedDate'] >= utc_day_start_string and opp['CreatedDate'] <= utc_day_end_string:
                        inflow_leads_ids['mktg_opps'].add(opp['Id'])
                        #inflow_leads_count['mktg_opps'] +=  1
            print 'finished looping mktg_opps_list in leads'
            #sales_opps - finds all opps created by sales and for which there's a lead or a contact
            sfdc_sales_opps = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'opportunities.sfdc.CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'leads.mkto.originalSourceType' : {'$eq': 'salesforce.com'}, 'opportunities.sfdc.Id' : {'$nin' : list(inflow_leads_ids['mktg_opps'])} })
            sfdc_sales_opps_list = list(sfdc_sales_opps)
            for lead in sfdc_sales_opps_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CreatedDate'] >= utc_day_start_string and opp['CreatedDate'] <= utc_day_end_string:
                        inflow_leads_ids['sales_opps'].add(opp['Id'])
                        #inflow_leads_count['sales_opps'] +=  1
            print 'finished looping sales_opps_list in leads'
            #sales_opps - get all the opportunities which don't have a contact - this is in the accounts collection
            sfdc_sales_accts_with_opps_no_contacts = Account._get_collection().find({'company_id' : int(company_id), 'opportunities.sfdc.CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'opportunities.sfdc.Id' : {'$nin' : list(inflow_leads_ids['sales_opps']), '$nin' : list(inflow_leads_ids['mktg_opps'])} })
            #print 'line 1'
            sfdc_sales_accts_with_opps_no_contacts_list = list(sfdc_sales_accts_with_opps_no_contacts)
            #print 'line 2'
            for account in sfdc_sales_accts_with_opps_no_contacts_list:
                for opp in account['opportunities']['sfdc']:
                    if opp['CreatedDate'] >= utc_day_start_string and opp['CreatedDate'] <= utc_day_end_string and opp['Id'] not in inflow_leads_ids['sales_opps']:
                        #print 'line 3'
                        inflow_leads_ids['sales_opps'].add(opp['Id'])
                        #print 'line 4'
                        #inflow_leads_count['sales_opps'] +=  1
                        #print 'line 5'
            print 'finished looping sales_opps_list in accounts'
            #mktg_closedwon
            closed_deal_value = 0
            lost_deal_value = 0
            max_deal_value = 0
            
            sfdc_mktg_closed_deals = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'opportunities.sfdc.CloseDate' : date, 'opportunities.sfdc.IsWon': True, 'leads.sfdc.CreatedById' : {'$eq': mkto_sync_user}})
            sfdc_mktg_closed_deals_list = list(sfdc_mktg_closed_deals)
            for lead in sfdc_mktg_closed_deals_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and opp['IsWon']:
                        inflow_leads_ids['mktg_closedwon'].add(opp['Id'])
                        #inflow_leads_count['mktg_closedwon'] +=  1
                        closed_deal_value += opp['Amount']
                        if closed_deal_value > max_deal_value: 
                            max_deal_value = closed_deal_value
                        outflow_leads_ids['mktg_opps'].add(opp['Id'])
                        #outflow_leads_count['mktg_opps'] += 1
                        duration['mktg_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping mktg_closedwon_list from leads'
            #sales_closedwon
            sfdc_sales_closed_deals = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'opportunities.sfdc.CloseDate' : date, 'opportunities.sfdc.IsWon': True, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            sfdc_sales_closed_deals_list = list(sfdc_sales_closed_deals)
            for lead in sfdc_sales_closed_deals_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and opp['IsWon']:
                        closed_deal_value += opp['Amount']
                        if closed_deal_value > max_deal_value: 
                            max_deal_value = closed_deal_value
                        inflow_leads_ids['sales_closedwon'].add(opp['Id'])
                        #inflow_leads_count['sales_closedwon'] +=  1
                        outflow_leads_ids['sales_opps'].add(opp['Id'])
                        #outflow_leads_count['sales_opps'] += 1
                        duration['sales_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping sales_closedwon_list from leads'
            #sales_closedwon - get all the opportunities which don't have a contact - this is in the accounts collection
            sfdc_sales_accts_with_opps_no_contacts = Account._get_collection().find({'company_id' : int(company_id),  'opportunities.sfdc.CloseDate' : date, 'opportunities.sfdc.IsWon': True, 'opportunities.sfdc.Id' : {'$nin' : list(inflow_leads_ids['sales_closedwon']), '$nin' : list(inflow_leads_ids['mktg_closedwon'])}})
            sfdc_sales_accts_with_opps_no_contacts_list = list(sfdc_sales_accts_with_opps_no_contacts)
            for account in sfdc_sales_accts_with_opps_no_contacts_list:
                for opp in account['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and opp['IsWon'] and opp['Id'] not in inflow_leads_ids['sales_closedwon'] and opp['Id'] not in inflow_leads_ids['mktg_closedwon']:
                        inflow_leads_ids['sales_closedwon'].add(opp['Id'])
                        #inflow_leads_count['sales_closedwon'] +=  1
                        closed_deal_value += opp['Amount']
                        if closed_deal_value > max_deal_value: 
                            max_deal_value = closed_deal_value
                        outflow_leads_ids['sales_opps'].add(opp['Id'])
                        #outflow_leads_count['sales_opps'] += 1
                        duration['sales_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping sales_closedwon_list from accounts'
            #mktg_closedlost
            sfdc_mktg_closed_deals = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'opportunities.sfdc.LastModifiedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'opportunities.sfdc.IsWon': False, 'opportunities.sfdc.IsClosed': True, 'leads.sfdc.CreatedById' : {'$eq': mkto_sync_user}}) #'opportunities.sfdc.CloseDate' : date,
            sfdc_mktg_closed_deals_list = list(sfdc_mktg_closed_deals)
            for lead in sfdc_mktg_closed_deals_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and not opp['IsWon'] and opp['IsClosed']:
                        inflow_leads_ids['mktg_closedlost'].add(opp['Id'])
                        #inflow_leads_count['mktg_closedlost'] +=  1
                        lost_deal_value += opp['Amount']
                        outflow_leads_ids['mktg_opps'].add(opp['Id'])
                        #outflow_leads_count['mktg_opps'] += 1
                        duration['mktg_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping mktg_closedlost'
            #sales_closedlost
            sfdc_sales_closed_deals = collection.find({'company_id' : int(company_id), '$or': [ { 'sfdc_id' : {'$exists': True} }, { 'sfdc_contact_id' : {'$exists': True} } ], 'opportunities.sfdc.LastModifiedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'opportunities.sfdc.IsWon': False, 'opportunities.sfdc.IsClosed': True, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}}) #'opportunities.sfdc.CloseDate' : date,
            sfdc_sales_closed_deals_list = list(sfdc_sales_closed_deals)
            for lead in sfdc_sales_closed_deals_list:
                for opp in lead['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and not opp['IsWon'] and opp['IsClosed']:
                        inflow_leads_ids['sales_closedlost'].add(opp['Id'])
                        #inflow_leads_count['sales_closedlost'] +=  1
                        lost_deal_value += opp['Amount']
                        outflow_leads_ids['sales_opps'].add(opp['Id'])
                        #outflow_leads_count['sales_opps'] += 1
                        duration['sales_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping sales_closedlost_list from leads'
            #sales_closedlost - get all the opportunities which don't have a contact - this is in the accounts collection
            sfdc_sales_accts_with_opps_no_contacts = Account._get_collection().find({'company_id' : int(company_id), 'opportunities.sfdc.LastModifiedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'opportunities.sfdc.IsWon': False, 'opportunities.sfdc.IsClosed': True, 'opportunities.sfdc.Id' : {'$nin' : list(inflow_leads_ids['sales_closedlost']), '$nin' : list(inflow_leads_ids['mktg_closedlost'])}}) # 'opportunities.sfdc.CloseDate' : date,
            sfdc_sales_accts_with_opps_no_contacts_list = list(sfdc_sales_accts_with_opps_no_contacts)
            for account in sfdc_sales_accts_with_opps_no_contacts_list:
                for opp in account['opportunities']['sfdc']:
                    if opp['CloseDate'] == date and not opp['IsWon'] and opp['IsClosed'] and opp['Id'] not in inflow_leads_ids['sales_closedlost']:
                        inflow_leads_ids['sales_closedlost'].add(opp['Id'])
                        #inflow_leads_count['sales_closedlost'] +=  1
                        lost_deal_value += opp['Amount']
                        outflow_leads_ids['sales_opps'].add(opp['Id'])
                        #outflow_leads_count['sales_opps'] += 1
                        duration['sales_opps'] +=  max(0, (_date_from_str(opp['CloseDate'], 'only_date') - _date_from_str(opp['CreatedDate'])).days)
            print 'finished looping sales_closedlost_list from accounts'
            
#             if outflow_leads_count['mktg_opps'] > 0: 
#                 duration['mktg_opps'] = duration['mktg_opps'] / outflow_leads_count['mktg_opps']
#             if outflow_leads_count['sales_opps'] > 0: 
#                 duration['sales_opps'] = duration['sales_opps'] / outflow_leads_count['sales_opps']
            print 'done with sales'
            #outflows for mktg_opps and sales_opps - combine values from mktg and sales closedwon and closedlost
            #outflow_leads_count['mktg_opps'] = inflow_leads_count['mktg_closedwon'] + inflow_leads_count['mktg_closedlost'] 
            #outflow_leads_count['sales_opps'] = inflow_leads_count['sales_closedwon'] + inflow_leads_count['sales_closedlost']
#             for id in inflow_leads_ids['mktg_closedwon']:
#                 outflow_leads_ids['mktg_opps'].append(id)
#             for id in inflow_leads_ids['mktg_closedlost']:
#                 outflow_leads_ids['mktg_opps'].append(id)
#             for id in inflow_leads_ids['sales_closedwon']:
#                 outflow_leads_ids['sales_opps'].append(id)
#             for id in inflow_leads_ids['sales_closedlost']:
#                 outflow_leads_ids['sales_opps'].append(id)
#             print 'finished looping outflows for sales and mktg opps'   
            
        return inflow_leads_ids, outflow_leads_ids, inflow_leads_count, outflow_leads_count, duration, closed_deal_value, lost_deal_value, max_deal_value, existed_count_sales
            
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
#begin HSPT dashboards
def hspt_social_roi(user_id, company_id, chart_name, mode, start_date):
    print 'starting social roi'
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        print 'local start is ' + str(local_start_date)
        print 'local end is ' + str(local_end_date)
        #time1 = str(time.time())
    
        delta = timedelta(days=1)
        e = local_end_date
        
        results = {}
       
        ids = {}
        
        #all query parameters
        source_created_date_qry = 'source_created_date'
        company_id_qry = 'company_id'
        source_metric_name_qry = 'source_metric_name'
        period_qry = 'data__period'
        end_time_qry = 'data__values__end_time'
        source_page_id_qry = 'source_page_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        source_system_qry= 'source_system'
        hspt_id_qry = 'hspt_id'
        related_contact_vid_qry = 'leads__hspt__related_contact_vids'
        
        #all other predefined data
        fb_paid_metrics = {'impressions', 'unique_impressions', 'reach', 'clicks', 'website_clicks', 'frequency', 'spend', 'cpc'} #actions array should also be included 
        fb_organic_metrics = {'page_impressions', 'page_impressions_unique', 'page_impressions_organic', 'page_impressions_organic_unique', 'page_consumptions_by_consumption_type', 'page_positive_feedback_by_type'}  
        source_system = 'hspt'
        
        #get all the distinct sources
        collection = Lead._get_collection()
        #sources = collection.find({'company_id':int(company_id)}).distinct('source_source').hint({'company_id': 1, 'source_source': 1})
        sources = ['OFFLINE', 'DIRECT_TRAFFIC', 'REFERRALS', 'ORGANIC_SEARCH', 'OTHER_CAMPAIGNS', 'SOCIAL_MEDIA', 'PAID_SEARCH', 'EMAIL_MARKETING', 'None']
    
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            print 'utc day start is ' + str(utc_day_start)
            print 'utc day end is ' + str(utc_day_end)
            utc_day_start_epoch = calendar.timegm(utc_day_start.timetuple()) * 1000
            utc_day_end_epoch = calendar.timegm(utc_day_end.timetuple()) * 1000
            print 'utc day starte is ' + str(utc_day_start_epoch)
            print 'utc day ende is ' + str(utc_day_end_epoch)
            results = {}
            
            results['Social'] = {}
            results['Social']['Facebook'] = {}
            #results['Social']['LinkedIn'] = {}
            #results['Social']['Twitter'] = {}
            results['Website'] = {}
            
            #get HS Sources data 
            results['Website']['Hubspot'] = {}
            results['Website']['Hubspot']['Revenue'] = 0
            querydict = {company_id_qry : company_id, source_system_qry: source_system, source_created_date_qry: date}
            trafficList = Traffic.objects(**querydict).first()
            if trafficList is not None and 'data' in trafficList:
                #results['Website']['Hubspot'].append(trafficList['data']) 
                for channelKey, channelData in trafficList['data'].items():
                    print 'channel is ' + channelKey
                    if channelKey not in results['Website']['Hubspot']:
                        results['Website']['Hubspot'][channelKey] = {}
                    results['Website']['Hubspot'][channelKey]['Revenue'] = 0
                    if channelKey == 'social':
                        for subchannel in channelData['breakdowns']:
                            if subchannel is None or subchannel['breakdown'] != 'Facebook':
                                continue
                            if subchannel['breakdown'] not in results['Website']['Hubspot'][channelKey]:
                                results['Website']['Hubspot'][channelKey][subchannel['breakdown']] = {}
                            if 'Paid' not in results['Website']['Hubspot'][channelKey][subchannel['breakdown']]:
                                results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid'] = {}
                            if 'Organic' not in results['Website']['Hubspot'][channelKey][subchannel['breakdown']]:
                                results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Total Visits'] = subchannel.get('visits', 0)
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Contacts'] = subchannel.get('contacts', 0)
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Leads'] = subchannel.get('leads', 0)
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Customers'] = subchannel.get('customers', 0)
                            campaigns = subchannel.get('campaigns', None)
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Total Visits'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Contacts'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Contacts']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Contacts']['People'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Leads'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Leads']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Leads']['People'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Customers'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Customers']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Customers']['People'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Total Visits'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Contacts'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Contacts']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Contacts']['People'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Leads'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Leads']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Leads']['People'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Customers'] = {}
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Customers']['Total'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Customers']['People'] = []
                            
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Revenue'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Revenue'] = 0
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Deals'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Deals'] = []
                            results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Revenue'] = 0
                            
                            
                            for campaign in campaigns:
                                contacts = campaign.get('contacts', None)
                                leads = campaign.get('leads', None)
                                customers = campaign.get('customers', None)
                                for person in customers['people']:
                                        hspt_id = str(person['vid'])
                                        print 'customer id is ' + str(hspt_id)
                                        querydict = {company_id_qry: company_id, hspt_id_qry: hspt_id}
                                        lead = Lead.objects(**querydict).first()
                                        if lead is None:
                                            print 'lead 1 not found'
                                            querydict = {company_id_qry: company_id, related_contact_vid_qry:person['vid']}
                                            lead = Lead.objects(**querydict).first()
                                        if lead is None:
                                            print 'no leads found for this id'
                                            continue
                                        else:
                                            opps = lead['opportunities'].get('hspt', [])
                                            for opp in opps:
                                                if opp['properties']['closedate']['timestamp'] >= int(utc_day_start_epoch) and opp['properties']['closedate']['timestamp'] <= int(utc_day_end_epoch):
                                                    print 'opp found'
                                                    deal_amount = float(opp['properties']['amount']['value'])
                                                    deal_name = opp['properties']['dealname']['value']
                                                    opp_object = {'lead_id' : lead['hspt_id'], 'deal_id': opp['dealId'], 'deal_amount': deal_amount, 'deal_close_date' : opp['properties']['closedate']['timestamp'], 'deal_name' : deal_name}
                                                    
                                                    if campaign['breakdown'] == 'c90e6907-e895-479c-8689-0d22fa660677': #hardcode? Check this
                                                        results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Revenue'] += deal_amount
                                                        results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Deals'].append(opp_object)
                                                    else:
                                                        results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Revenue'] += deal_amount
                                                        results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Deals'].append(opp_object)
                                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Revenue'] += deal_amount
                                                    results['Website']['Hubspot'][channelKey]['Revenue'] += deal_amount
                                                    results['Website']['Hubspot']['Revenue'] += deal_amount
                                if campaign['breakdown'] == 'c90e6907-e895-479c-8689-0d22fa660677': #hardcode? Check this  
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Total Visits'] += campaign.get('visits', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Contacts']['Total'] += contacts.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Contacts']['People'].extend(contacts.get('people', []))
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Leads']['Total'] +=  leads.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Leads']['People'].extend(leads.get('people', []))
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Customers']['Total'] +=  customers.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Organic']['Customers']['People'].extend(customers.get('people', []))
                                    
                                else:
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Total Visits'] += campaign.get('visits', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Contacts']['Total'] += contacts.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Contacts']['People'].extend(contacts.get('people', []))
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Leads']['Total'] +=  leads.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Leads']['People'].extend(leads.get('people', []))
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Customers']['Total'] +=  customers.get('total', 0)
                                    results['Website']['Hubspot'][channelKey][subchannel['breakdown']]['Paid']['Customers']['People'].extend(customers.get('people', []))
                                    
                
                
            #prepare analytics collections           
            queryDict = {company_id_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
                 
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.system_type = 'MA'
                analyticsIds.company_id = company_id  
                analyticsIds.chart_name = chart_name
                analyticsIds.date = date
                analyticsIds.results = {}
                analyticsIds.save()
                
            #print 'results are ' + str(results)
            analyticsData.results = results
            results = {}
            print 'saving' 
            try:
                AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                #AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            except Exception as e:
                print 'exception while saving analytics data: ' + str(e)
                continue
            print 'saved'
        #print 'start time was ' + time1 + ' and end time is ' + str(time.time())
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})

def hspt_funnel(user_id, company_id, chart_name, mode, start_date):
#HSPT Funnel dashboard aggregation
    print 'starting funnel'
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        print 'local start is ' + str(local_start_date)
        print 'local end is ' + str(local_end_date)
        #time1 = str(time.time())
    
        delta = timedelta(days=1)
        e = local_end_date
        
        
        #get all the distinct sources
        collection = Lead._get_collection()
        #sources = collection.find({'company_id':int(company_id)}).distinct('source_source').hint({'company_id': 1, 'source_source': 1})
        sources = ['OFFLINE', 'DIRECT_TRAFFIC', 'REFERRALS', 'ORGANIC_SEARCH', 'OTHER_CAMPAIGNS', 'SOCIAL_MEDIA', 'PAID_SEARCH', 'EMAIL_MARKETING', 'None']
    
        
        delta = timedelta(days=1)
        e = local_end_date
        #print 'local end date is ' + str(local_end_date)
        
        #all query parameters
        hspt_opp_close_date_start_qry = 'opportunities__hspt__properties__closedate__value__gte'
        hspt_opp_close_date_end_qry = 'opportunities__hspt__properties__closedate__value__lte'
        
        company_field_qry = 'company_id'
        created_date_end_qry = 'source_created_date__lte'
        created_date_start_qry = 'source_created_date__gte'
        source_created_date_qry = 'source_created_date'
        company_id_qry = 'company_id'
        source_metric_name_qry = 'source_metric_name'
        period_qry = 'data__period'
        end_time_qry = 'data__values__end_time'
        source_page_id_qry = 'source_page_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        
        #all other predefined data
        results = {}
        inflow_leads_count = {}
        outflow_leads_count = {}
        inflow_leads_ids = {}
        outflow_leads_ids = {}
        outflow_leads_duration = {}
        
        stage_dates = (('subscriber', 'hspt_subscriber_date'), ('lead', 'hspt_lead_date'), ('marketingqualifiedlead', 'hspt_mql_date'), ('salesqualifiedlead', 'hspt_sql_date'), ('opportunity', 'hspt_opp_date'), ('customer', 'hspt_customer_date'))
        stage_dates = OrderedDict(stage_dates)
        stage_subsequent = {'subscriber': ['lead', 'marketingqualifiedlead', 'salesqualifiedlead', 'opportunity', 'customer'], 'lead': ['marketingqualifiedlead', 'salesqualifiedlead', 'opportunity', 'customer'], 'marketingqualifiedlead': ['salesqualifiedlead', 'opportunity', 'customer'], 'salesqualifiedlead': ['opportunity', 'customer'], 'opportunity': ['customer'], 'customer': [] }
        collection = Lead._get_collection()
        
        ###loop through each day of the period 
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            #print 'utc day start is ' + str(utc_day_start)
            #print 'utc day end is ' + str(utc_day_end)
            utc_day_start_epoch = calendar.timegm(utc_day_start.timetuple()) * 1000
            utc_day_end_epoch = calendar.timegm(utc_day_end.timetuple()) * 1000
            #print 'utc day starte is ' + str(utc_day_start_epoch)
            #print 'utc day ende is ' + str(utc_day_end_epoch)
            
            inflow_leads_count = {}
            outflow_leads_count = {}
            inflow_leads_ids = {}
            outflow_leads_ids = {}
            outflow_leads_duration = {}
            
            #get all leads which were created before the start of today by source
            querydict = {company_field_qry: company_id, created_date_end_qry: utc_day_start} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            #leads_existed_source = Lead.objects(**querydict).item_frequencies('source_source')
            #leads_existed_stage = Lead.objects(**querydict).item_frequencies('source_stage')
            existed_count = Lead.objects(**querydict).count()
            #get all leads that were created in this time period by source
            querydict = {company_field_qry: company_id, created_date_start_qry: utc_day_start, created_date_end_qry: utc_day_end} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            leads_created_source = Lead.objects(**querydict).item_frequencies('source_source')
            leads_created_stage = Lead.objects(**querydict).item_frequencies('source_stage')
            created_count = Lead.objects(**querydict).count()
#             if existed_count > 0:
#                 percentage_increase = float( created_count / existed_count ) * 100
#             else:
#                 percentage_increase = 0
            #loop through each stage
            for current_stage, current_stage_date_name in stage_dates.items():
                #get all leads that entered this stage in this time period
                date_start_qry = current_stage_date_name + '__gte'
                date_end_qry = current_stage_date_name + '__lte'
                querydict = {company_field_qry: company_id, date_start_qry: utc_day_start, date_end_qry: utc_day_end} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
                
                leads_became_stage = Lead.objects(**querydict)
                leads_became_stage_list  = list(leads_became_stage)
                inflow_leads_count[current_stage] = len(leads_became_stage_list)
                inflow_leads_ids[current_stage] = [x['hspt_id'] for x in leads_became_stage_list]
                
                #find all leads who were in this stage before the start of the period and moved into a subsequent stage in this period
                stage_subsequent_temp = stage_subsequent[current_stage] # we have all subsequent stages for this stage
                
                if current_stage != 'customer': #don't do this calculation for customers since there's no outflow 
                    querydict = {'company_id' : int(company_id), current_stage_date_name: { '$lt': utc_day_start} }
                    stage_qry_or_list = []
                    for subs_stage in stage_subsequent_temp:
                        stage_qry_or_list.append( { stage_dates[subs_stage] : {'$gte' : utc_day_start, '$lte' : utc_day_end} })
                    and_query = [{ '$or' : stage_qry_or_list }]
                    querydict['$and'] = and_query
                    
                    index_name = 'company_id_1_' + current_stage_date_name + '_1'
                    leads_exited_stage = collection.find(querydict).hint(index_name)
                    leads_exited_stage_list = list(leads_exited_stage)
                    outflow_leads_count[current_stage] = len(leads_exited_stage_list)
                    outflow_leads_ids[current_stage] = [x['hspt_id'] for x in leads_exited_stage_list]
                    
                    if outflow_leads_count[current_stage] > 0:
                        duration_list = [(utc_day_start - get_current_timezone().localize(x[current_stage_date_name], is_dst=None).astimezone(pytz.timezone('UTC'))).days for x in leads_exited_stage_list] #NOTE - calculatues upto the start of the current day to simplify calcs
                        outflow_leads_duration[current_stage] = sum(duration_list) / len(duration_list)
                        #print 'stage is ' + current_stage + ' on ' + date
                        #print 'were leads ' + str(outflow_leads_ids[current_stage])
                    else:
                        outflow_leads_duration[current_stage] = 'N/A'
        
                #treat customers differently for outflow, find deals instead
                else:
                    print 'in customer stage'
                    hspt_opp_close_date_start_qry = 'opportunities__hspt__properties__closedate__value__gte'
                    hspt_opp_close_date_end_qry = 'opportunities__hspt__properties__closedate__value__lte'
                    print 'utc is ' + str(utc_day_start_epoch) + ' - ' + str(utc_day_end_epoch)
                    querydict = {company_field_qry: company_id, hspt_opp_close_date_start_qry: str(utc_day_start_epoch), hspt_opp_close_date_end_qry: str(utc_day_end_epoch)} 
                    #deals_total_value = Lead.objects(**querydict).aggregate({'$unwind': '$opportunities.hspt'}, {'$group': {'_id' : '$_id', 'totalDealValue' : { '$max' : '$opportunities.hspt.properties.amount.value'}}})
                    deals_list = Lead.objects(**querydict).aggregate({'$unwind': '$opportunities.hspt'}, {'$match' : {'opportunities.hspt.properties.closedate.value': {'$gte': str(utc_day_start_epoch), '$lte': str(utc_day_end_epoch) }}}, {'$project': {'_id':0, 'id': '$opportunities.hspt.dealId', 'value': '$opportunities.hspt.properties.amount.value', 'close_date': '$opportunities.hspt.properties.closedate.value'}})
                    deals_list = list(deals_list)
#                     if (len(deals_list)) > 0:
#                         print 'deals ' + str(list(deals_list))
#                         return 
                    num_deals_closed = len(deals_list)
                    closed_deal_value = 0
                    max_deal_value = 0
                    for deal in deals_list:
                        #print 'total deal val is ' + deal['value']
                        if not deal['value']:
                            continue
                        closed_deal_value += float(deal['value'])
                        if float(deal['value']) > max_deal_value:
                            max_deal_value = float(deal['value'])
            
            for key, value in leads_created_source.items():
                if key is None:
                    leads_created_source['Unknown'] = leads_created_source.pop(key)  
                      
            for key, value in leads_created_stage.items():
                if key is None:
                    leads_created_stage['Unknown'] = leads_created_stage.pop(key) 
                      
            results['data'] = {'existed_count': existed_count, 'created_count': created_count, 'created_source' : leads_created_source, 'created_stage' : leads_created_stage, 'num_deals_closed' : num_deals_closed, 'closed_deal_value' : closed_deal_value, 'max_deal_value': max_deal_value, 'inflow_count': inflow_leads_count, 'outflow_count': outflow_leads_count, 'outflow_duration': outflow_leads_duration}
            results['ids'] = {}
            results['ids']['inflow'] = inflow_leads_ids
            results['ids']['outflow'] = outflow_leads_ids
            results['ids']['deals'] = deals_list
            #print 'results ' + str(results)
            
            #prepare analytics collections           
            queryDict = {company_id_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
                  
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.system_type = 'MA'
                analyticsIds.company_id = company_id  
                analyticsIds.chart_name = chart_name
                analyticsIds.date = date
                analyticsIds.results = {}
                analyticsIds.save()
                 
            #print 'results are ' + str(results)
            analyticsData.results = results['data']
            analyticsIds.results['inflow'] = results['ids']['inflow']
            analyticsIds.results['outflow'] = results['ids']['outflow']
            analyticsIds.results['deals'] = results['ids']['deals']
            results = {}
            print 'saving' 
            try:
                AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            except Exception as e:
                print 'exception while saving analytics data: ' + str(e)
                continue
            print 'saved'
        #return results
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 

def hspt_form_fills(user_id, company_id, chart_name, mode, start_date):
#HSPT Form Fills dashboard aggregation
    print 'starting form fills'
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        print 'local start is ' + str(local_start_date)
        print 'local end is ' + str(local_end_date)
        #time1 = str(time.time())
    
        delta = timedelta(days=1)
        e = local_end_date
        delta = timedelta(days=1)
        e = local_end_date
        #print 'local end date is ' + str(local_end_date)
        
        #all query parameters
        hspt_first_conversion_date_start_qry = 'leads__hspt__properties__first_conversion_date__gte'
        hspt_first_conversion_date_end_qry = 'leads__hspt__properties__first_conversion_date__lte'
        hspt_recent_conversion_date_start_qry = 'leads__hspt__properties__recent_conversion_date__gte'
        hspt_recent_conversion_date_end_qry = 'leads__hspt__properties__recent_conversion_date__lte'
        
        company_field_qry = 'company_id'
        created_date_end_qry = 'source_created_date__lte'
        created_date_start_qry = 'source_created_date__gte'
        source_created_date_qry = 'source_created_date'
        company_id_qry = 'company_id'
        source_metric_name_qry = 'source_metric_name'
        period_qry = 'data__period'
        end_time_qry = 'data__values__end_time'
        source_page_id_qry = 'source_page_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        
        #all other predefined data
        results = {}
        inflow_leads_count = {}
        outflow_leads_count = {}
        inflow_leads_ids = {}
        outflow_leads_ids = {}
        outflow_leads_duration = {}
        
        collection = Lead._get_collection()
        
        ###loop through each day of the period 
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            #print 'utc day start is ' + str(utc_day_start)
            #print 'utc day end is ' + str(utc_day_end)
            utc_day_start_epoch = calendar.timegm(utc_day_start.timetuple()) * 1000
            utc_day_end_epoch = calendar.timegm(utc_day_end.timetuple()) * 1000
            #print 'utc day starte is ' + str(utc_day_start_epoch)
            #print 'utc day ende is ' + str(utc_day_end_epoch)
            
            inflow_leads_count = {}
            outflow_leads_count = {}
            inflow_leads_ids = {}
            outflow_leads_ids = {}
            outflow_leads_duration = {}
            results_data = {}
            results_ids = {}
            
            #get all leads who have a first conversion date today
            querydict = {company_field_qry: company_id, hspt_first_conversion_date_start_qry: utc_day_start, hspt_first_conversion_date_end_qry: utc_day_end}
            firstConversionLeads =  Lead.objects(**querydict).aggregate(
                { "$group": {
                    "_id": {
                        "country": "$leads.hspt.properties.country",
                        "form" : "$leads.hspt.properties.first_conversion_event_name"
                    },
                    "ids": { "$push": {"id": "$hspt_id"} }, 
                    "leadCount": { "$sum": 1 }
                }},
                { "$sort": { "leadCount": -1 } },
                { "$group": {
                    "_id": "$_id.country",
                    "forms" : { "$push": {
                        "form" : "$_id.form",
                        "ids": "$ids",
                        "count" : "$leadCount"
                        },
                    },
                    "count": { "$sum": "$leadCount" },
            
                }},
            
                { "$sort": { "count": -1 } }
            )
            
#             for lead in list(firstConversionLeads):
#                 print 'first lead is ' + str(lead)
            result_data = {} #holds the final data for the day
            result_ids = {} # holds the final ids for the day
            
            firstList = list(firstConversionLeads)
            results_data, results_ids = _process_form_list(firstList)  
            result_data['first'] = results_data
            result_ids['first'] = results_ids
               
            #get all leads who have a recent conversion date today
            querydict = {company_field_qry: company_id, hspt_recent_conversion_date_start_qry: utc_day_start, hspt_recent_conversion_date_end_qry: utc_day_end}
            recentConversionLeads =  Lead.objects(**querydict).aggregate(
                { "$project": { #additional project and match stages for Recent dates to ensure non-duplication where Recent and First are the same
                   "leads.hspt.properties.recent_conversion_date": 1,
                   "leads.hspt.properties.first_conversion_date": 1,
                   "leads.hspt.properties.country": 1,
                   "leads.hspt.properties.recent_conversion_event_name": 1, 
                   "hspt_id": 1,
                   "isDifferent": {"$gt": ["$leads.hspt.properties.recent_conversion_date", "$leads.hspt.properties.first_conversion_date"]}
                               }
                },
                {  "$match": {
                    "isDifferent": True          
                              }  
                },
                { "$group": {
                    "_id": {
                        "country": "$leads.hspt.properties.country",
                        "form" : "$leads.hspt.properties.recent_conversion_event_name"
                    },
                    "ids": { "$push": {"id": "$hspt_id"} }, 
                    "leadCount": { "$sum": 1 }
                }},
                { "$sort": { "leadCount": -1 } },
                { "$group": {
                    "_id": "$_id.country",
                    "forms" : { "$push": {
                        "form" : "$_id.form",
                        "ids": "$ids",
                        "count" : "$leadCount"
                        },
                    },
                    "count": { "$sum": "$leadCount" },
            
                }},
            
                { "$sort": { "count": -1 } }
            )
            
            recentList = list(recentConversionLeads)
            print 'recent list ' + str(recentList)
            
            results_data, results_ids = _process_form_list(recentList)  
            result_data['recent'] = results_data
            result_ids['recent'] = results_ids
                            
            #prepare analytics collections           
            queryDict = {company_id_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
                
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.system_type = 'MA'
                analyticsIds.company_id = company_id  
                analyticsIds.chart_name = chart_name
                analyticsIds.date = date
                analyticsIds.results = {}
                analyticsIds.save()
  
            #print 'results are ' + str(results)
            analyticsData.results = result_data
            analyticsIds.results = result_ids
            
            print 'saving' 
            try:
                AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            except Exception as e:
                print 'exception while saving analytics data: ' + str(e)
                continue
            print 'saved'
            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 

