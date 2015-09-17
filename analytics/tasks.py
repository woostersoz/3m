from __future__ import absolute_import
from datetime import timedelta, date, datetime
import pytz
import os, copy
import time, calendar
import urllib2
from dateutil import tz

from collections import OrderedDict
from operator import itemgetter

from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from mongoengine.queryset.visitor import Q

from leads.models import Lead
from company.models import CompanyIntegration
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from social.models import PublishedTweet, FbAdInsight, FbPageInsight
from analytics.models import AnalyticsData, AnalyticsIds
from websites.models import Traffic
from superadmin.models import SuperUrlMapping, SuperIntegration, SuperCountry

from django.utils.timezone import get_current_timezone
from dashboards.tasks import _str_from_date
from geopy.geocoders import Nominatim, GoogleV3

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")


def _date_from_str(dateString, format=None): # returns a datetime object from a timezone like string 
    
    if format == 'short': # short format of date string found in Mkto created date
        return datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
    else:
        if dateString.find('+0000') != -1: #account for weird formats
            return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:%S.000+0000') 
        else:
            return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:%SZ') # found in status record

def _str_from_date(dateTime, format=None): # returns a datetime object from a timezone like string 
    
    if format == 'short': # short format of date string found in Mkto created date
        return datetime.strftime(dateTime, '%Y-%m-%d')
    else:
        return datetime.strftime(dateTime, '%Y-%m-%dT%H:%M:%SZ') # found in status record

@app.task
def calculateMktoAnalytics(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    method_map = { "sources_bar" : mkto_sources_bar_chart, "contacts_distr" : mkto_contacts_distr_chart, "source_pie" : mkto_contacts_sources_pie, "pipeline_duration" : mkto_contacts_pipeline_duration, "revenue_source_pie" : mkto_contacts_revenue_sources_pie, "funnel": hspt_funnel, "waterfall_chart": mkto_waterfall}
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
def calculateSfdcAnalytics(user_id=None, company_id=None):
    pass

@app.task
def calculateHsptAnalytics(user_id=None, company_id=None, chart_name=None, chart_title=None, mode='delta', start_date=None):
    method_map = { "sources_bar" : hspt_sources_bar_chart, "contacts_distr" : hspt_contacts_distr_chart, "pipeline_duration" : hspt_contacts_pipeline_duration, "source_pie" : hspt_contacts_sources_pie, "revenue_source_pie" : hspt_contacts_revenue_sources_pie, "multichannel_leads" : hspt_multichannel_leads, "social_roi" : hspt_social_roi, "funnel" : hspt_funnel, "waterfall_chart": None, "form_fills": hspt_form_fills}
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


# begin MKTO analytics
# first chart - 'Timeline"
def mkto_sources_bar_chart(user_id, company_id, chart_name, mode, start_date): 
    company_field_qry = 'company_id'
    system_field_qry = 'leads__mkto__exists' #check if mkto lead exists; not checking for sfdc here coz scoring rules may be in action even though statuses are pulled from sfdc
    querydict = {system_field_qry: True, company_field_qry: company_id}
         
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            #print 'sources start date is ' + start_date
            #print 'original date was ' + str(datetime.utcnow() + timedelta(-1))
            start_date = start_date
#             system_type_query = 'system_type'
#             company_query = 'company_id'
#             chart_name_query = 'chart_name'
#             queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name}
#             analyticsData = AnalyticsData.objects(**queryDict).first()
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            firstDate = Lead.objects(**querydict).only('source_created_date').order_by('source_created_date').first()
            #start_date = _date_from_str(firstDate['source_created_date'])
            start_date = firstDate['source_created_date']
            
        
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        #print 'diff is ' + str((local_end_date - local_start_date).days)
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        
        #assumes that Marketo is integrated to SFDC and the statuses are picked up from the latter
#         if existingIntegration is not None and 'sfdc' in existingIntegration.integrations:
#             if 'metadata' in existingIntegration.integrations['sfdc'] and 'lead' in existingIntegration.integrations['sfdc']['metadata'] and 'statuses' in existingIntegration.integrations['sfdc']['metadata']['lead']:
#                 leadStatus = existingIntegration.integrations['sfdc']['metadata']['lead']['statuses']
#                 sortedLeadStatus = sorted(leadStatus, key=itemgetter('SortOrder'), reverse=False)
#             else:
#                 print 'value error - no metadata'
#                 raise ValueError('No metadata found for Lead Status from Salesforce')
                
        
        all_dates = []
        all_values = {}
        all_ids = {}
        
#         for status in sortedLeadStatus: #create container to hold the values by status, date
#             all_values[status['MasterLabel']] = {}
#             all_ids[status['MasterLabel']] = {}
        all_values['Unassigned'] = {}
        all_ids['Unassigned'] = {}
        
        created_date_qry = 'source_created_date__gte'
        if mode == 'delta':
            querydict = {system_field_qry: True, company_field_qry: company_id, created_date_qry: local_start_date} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        else:
            querydict = {system_field_qry: True, company_field_qry: company_id}
        #print ' qdict' + str(querydict)    
        existingLeads = Lead.objects(**querydict).only('mkto_id', 'statuses', 'source_status', 'source_created_date').all().timeout(False) 
        if existingLeads is None:
            print ' no leads found'
            return 
        #print ' found leads' + str(len(existingLeads))
        delta = timedelta(days=1)
        e = local_end_date
        #date_field_map = { "subscriber" : 'hs_lifecyclestage_subscriber_date', "lead" : 'hs_lifecyclestage_lead_date', "marketingqualifiedlead" : 'hs_lifecyclestage_marketingqualifiedlead_date', "salesqualifiedlead" : 'hs_lifecyclestage_salesqualifiedlead_date', "opportunity" : 'hs_lifecyclestage_opportunity_date', "customer" : 'hs_lifecyclestage_customer_date' } 
        #this_lead_done_for_day = False
        
        
        for lead in existingLeads:
            s = local_start_date - timedelta(days=1)
            #if 'mkto' not in lead.statuses: # if no statuses found for this lead, move to next lead
                #continue
            if 'mkto' in lead.statuses:
                statuses = lead.statuses['mkto']
            else:
                statuses = None
#             if len(statuses) == 0: # move to next lead if there's no current status for the lead
#                 continue
        
            #print 'statuses are ' + str(statuses)
            current_stage = lead.source_status if lead.source_status is not None else 'Unassigned'
            #find the current status' position in the status list array
#             currentStatusPosition = None
#             if statuses is not None and len(statuses) > 0: # if there are statuses for this lead, find all of them else assume 'Unassigned'
#                 for counter in range(len(sortedLeadStatus)):
#                     if current_stage == sortedLeadStatus[counter]['MasterLabel']:
#                         currentStatusPosition = counter
            
#             if currentStatusPosition is not None:   # either there are no statuses or some invalid value of source_status     
#                 statusesForThisLead = sortedLeadStatus[currentStatusPosition::-1] #slice from first possible status to the current status
#                 #store all of this lead's statuses and related dates in one dict - to avoid calculations in each date loop
#                 for current_stage in statusesForThisLead:
#                     #print 'enter date loop with start ' + str(s) + ' and end ' + str(e)
#                     current_stage_date_naive = None
#                     # find the date on which lead entered the current status in the loop
#                     for i in range(len(statuses)):
#                         #print 'about to bomb w ' + str(status)
#                         if statuses[i]['status'] == current_stage['MasterLabel']:
#                             current_stage_date_naive = _date_from_str(statuses[i]['date'])
#                             print 'date is ' + str(current_stage_date_naive)
#                     
#                     if current_stage_date_naive is None: # date not found for current status so move to next day
#                         current_stage_date_naive = _date_from_str(lead.source_created_date, "short")
#                          
#                     current_stage_date = pytz.utc.localize(current_stage_date_naive, is_dst=None)
#                     current_stage_date = current_stage_date.astimezone(get_current_timezone())
#                     
#                     current_stage['date'] = current_stage_date # store date for status
#             
#             else:
            #print 'lead created on ' +str(lead.source_created_date)
            statusesForThisLead = []
            if statuses is not None: # if there are statuses in the lead record, find the date for the current status
                for i in range(len(statuses)):
                    current_stage =  statuses[i]['status']
                    #print 'lead stat d us ' +str(statuses[i]['date'])
                    current_stage_date_naive = _date_from_str(statuses[i]['date'])
                    current_stage_date = pytz.utc.localize(current_stage_date_naive, is_dst=None)
                    current_stage_date = current_stage_date.astimezone(get_current_timezone())
                    #current_stage['date'] = current_stage_date # store date for status
                    statusesForThisLead.append({'MasterLabel' : current_stage, 'SortOrder': -1, 'date': current_stage_date})
                    if current_stage not in all_values: 
                        all_values[current_stage] = {}
                        all_ids[current_stage] = {}
                    # add one more entry with Unassigned at Lead Created date - else leads that were null after creation for more than a day will only show up for subsequent statuses
                    current_stage = 'Unassigned'
                    current_stage_date_naive = lead.source_created_date #_date_from_str(lead.source_created_date)             
                    current_stage_date = pytz.utc.localize(current_stage_date_naive, is_dst=None)
                    current_stage_date = current_stage_date.astimezone(get_current_timezone())
                    #print 'csd is ' + str(current_stage_date)
                    statusesForThisLead.append({'MasterLabel' : current_stage, 'SortOrder': -1, 'date': current_stage_date})
                    if current_stage not in all_values: 
                        all_values[current_stage] = {}
                        all_ids[current_stage] = {}
            else: # if there are no statuses, assume that the current status was valid from the lead created date
                current_stage_date_naive = lead.source_created_date #_date_from_str(lead.source_created_date)             
                current_stage_date = pytz.utc.localize(current_stage_date_naive, is_dst=None)
                current_stage_date = current_stage_date.astimezone(get_current_timezone())
                statusesForThisLead.append({'MasterLabel' : current_stage, 'SortOrder': -1, 'date': current_stage_date})
                if current_stage not in all_values: 
                    all_values[current_stage] = {}
                    all_ids[current_stage] = {}


            while s < (e - delta):
                s += delta #increment the day counter
                array_key = s.strftime('%Y-%m-%d')
                #print 'lead is ' + lead.mkto_id + ' and day is ' + str(array_key)
                if array_key not in all_dates:
                    all_dates.append(array_key)
                    
                for current_stage in statusesForThisLead:
                    current_stage_date = current_stage['date']
                    #print 'current stage date is ' + str(current_stage_date)
                    if current_stage_date <= s: # if the date for this stage is less than loop date, add it to the array
                        if array_key in all_values[current_stage['MasterLabel']]:
                            all_values[current_stage['MasterLabel']][array_key] += 1
                            #print '1 hap'
                        else:
                            all_values[current_stage['MasterLabel']][array_key] = 1
                            #print '2 hap'
                        if array_key not in all_ids[current_stage['MasterLabel']]:
                            all_ids[current_stage['MasterLabel']][array_key] = []                        
                        all_ids[current_stage['MasterLabel']][array_key].append(lead.mkto_id)
                        break # move onto the next day
                    
        #print 'final array is ' + str(all_values)
        #print 'final ids is ' + str(all_ids)
#         
#         #print 'found record for ' + str(subscriber_values_temp_array)
#         #save the records in the DB
    
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_query = 'date'
            #queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name}
            #analyticsData = AnalyticsData.objects(**queryDict).first()
            #analyticsIds = AnalyticsIds.objects(**queryDict).first()  
        
        for date in all_dates:
             
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_query: date}
            
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: #though not Initial, this date's record not found
                analyticsData = AnalyticsData()
            analyticsData.system_type = 'MA'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = date
            analyticsData.results = {}
            analyticsData.save()
            
            analyticsData.date = date
            
            analyticsIds = AnalyticsIds.objects(**queryDict).first() 
            if analyticsIds is None: #though not Initial, this date's record not found
                analyticsIds = AnalyticsIds()
            analyticsIds.system_type = 'MA'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = date
            analyticsIds.results = {}
            analyticsIds.save()
            
            analyticsIds.date = date
            
            for status in all_values.keys():
                
                analyticsData.results[status] = {}
                analyticsIds.results[status] = {}
                
                if date in all_values[status]:
                    analyticsData.results[status] = all_values[status][date]
                    analyticsIds.results[status] = all_ids[status][date]
                else:
                    analyticsData.results[status] = 0
                    analyticsIds.results[status] = []
                    
            #done with day so save the records
            #analyticsData.save()
            #analyticsIds.save()
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    

                
                    
        #print 'record is ' + str(analyticsData)

    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 
    
# chart - "Contacts  Distribution"   
def mkto_contacts_distr_chart(user_id, company_id, chart_name, mode, start_date): 
    #print 'orig start' + str(start_date)
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
        local_end_date_str = _str_from_date(local_end_date, 'short')
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        start_date_created_field_qry = 'source_created_date__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__mkto__exists'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
            
        
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        while s < (f - delta): # outer loop on the start date
            s += delta #increment the outer loop
            start_key = _str_from_date(s, 'short')
            #array_key = s.strftime('%m-%d-%Y')
            
            # look for leads that were created before or on this date and no later than the last date of the range we are looking for
            querydict = {company_field_qry: company_id, system_field_qry: True, end_date_created_field_qry: start_key} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            statuses = Lead.objects(**querydict).item_frequencies('source_status')
            if None in statuses:
                statuses['Unassigned'] = statuses.pop(None)
            print 'statuses for ' + start_key + ' are ' + str(statuses)  
            
            #use map reduce to group lead ids by status - not used
            map_f = """
                function() {
                   emit(this.source_status, {id: this.mkto_id});
                   }
                   """
            reduce_f = """
                function(keyStatus, mktoIdArray ) {
                   var ret = {ids: []};
                   var ids = {};
                    for (var i =0 ; i < mktoIdArray.length; i++)
                    {   
                        ret.ids.push(mktoIdArray[i].id);
                    }
                   return ret;
                   }
                   """

            mktoIds =  Lead.objects(**querydict).aggregate( { '$group': { '_id': '$source_status', 'mkto_id': { '$push': '$mkto_id' } } } ) #.map_reduce(map_f, reduce_f, 'test')
            #mktoIds = list(mktoIds)
         
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: 
                analyticsData = AnalyticsData()
            analyticsData.system_type = 'MA'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = start_key
            analyticsData.results = {}
            #print 'save 1'
            analyticsData.save()
            
            #update the totals for each status for this day
            for status in statuses:
                analyticsData.results[status] = {}
                analyticsData.results[status]['total'] = statuses[status]
                analyticsData.results[status]['inflows'] = 0
                analyticsData.results[status]['outflows'] = 0
            
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
            analyticsIds.system_type = 'MA'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = start_key
            analyticsIds.results = {}
            analyticsIds.save()
            
            #update the IDs for each status for this day
            for entry in list(mktoIds):
                #print 'mktoIds key is ' + str(entry['_id']) + ' of length ' + str(len(entry['mkto_id']))# + ' and val is ' + str(mktoId.value)
                if entry['_id'] is None: 
                    entry['_id'] = 'Unassigned'
                analyticsIds.results[entry['_id']] = {}
                analyticsIds.results[entry['_id']]['total'] = entry['mkto_id']
                analyticsIds.results[entry['_id']]['inflows'] = []
                analyticsIds.results[entry['_id']]['outflows'] = []
            
            # done with the lead statuses, now move on to Inflows and Outflows
            activity_date_qry = 'activities__mkto__activityDate__startswith'
            activity_name_qry = 'activities__mkto__activityTypeName__exact'
            activity_name = 'Change Data Value'
            activity_attribute_qry = 'activities__mkto__primaryAttributeValue__exact'
            activity_attribute = 'Lead Status'
            #print ' getting into q'
            querydict = {activity_date_qry: start_key, activity_attribute_qry: activity_attribute,  activity_name_qry: activity_name , company_field_qry: company_id, system_field_qry: True, end_date_created_field_qry: start_key}
            leads_with_activities = Lead.objects(**querydict).timeout(False) 
            #print 'found leads' + str(len(leads_with_activities))
            #&  Q(company_id= company_id, leads__mkto__exists= True, source_created_date__lte= start_key)
             
            for lead in leads_with_activities:
                #nelow line needed to extract the relevant Status Change activites and ignore the rest
                activities = [a for a in lead['activities']['mkto'] if a['activityTypeName'] == activity_name and a['primaryAttributeValue'] == activity_attribute and a['activityDate'].startswith(start_key)]
                #activities = lead['activities']['mkto']
                #print 'act is ' + str(activities)
                for activity in activities:
                    attributes = [b for b in activity['attributes'] if b['name'] == 'New Value' or b['name'] == 'Old Value']
                    for attribute in attributes:
                        #inflows
                        if attribute['name'] == 'New Value': # this is a positive for the lead
                            if attribute['value'] is None:
                                attribute['value'] = 'Unassigned'
                            if attribute['value'] in statuses: #if this status is already in statuses list
                                print 'status fond is ' + attribute['value']
                                analyticsData.results[attribute['value']]['inflows'] += 1 # increment the number of inflows
                            else: # for some reason, this status does not yet exist in  the statuses list
                                analyticsData.results[attribute['value']] = {}
                                analyticsData.results[attribute['value']]['total'] = 0
                                analyticsData.results[attribute['value']]['inflows'] = 1
                                analyticsData.results[attribute['value']]['outflows'] = 0
                            if attribute['value'] not in analyticsIds.results:
                                analyticsIds.results[attribute['value']] = {}
                                analyticsIds.results[attribute['value']]['inflows'] = []
                                analyticsIds.results[attribute['value']]['outflows'] = []
                            analyticsIds.results[attribute['value']]['inflows'].append(lead['mkto_id'])
                        #outflows
                        if attribute['name'] == 'Old Value': # this is a positive for the lead
                            if attribute['value'] is None:
                                attribute['value'] = 'Unassigned'
                            if attribute['value'] in statuses: #if this status is already in statuses list
                                analyticsData.results[attribute['value']]['outflows'] -= 1 # decrement the number of outflows
                            else: # for some reason, this status does not yet exist in  the statuses list
                                analyticsData.results[attribute['value']] = {}
                                analyticsData.results[attribute['value']]['total'] = 0
                                analyticsData.results[attribute['value']]['inflows'] = 0
                                analyticsData.results[attribute['value']]['outflows'] = -1
                            if attribute['value'] not in analyticsIds.results:
                                analyticsIds.results[attribute['value']] = {}
                                analyticsIds.results[attribute['value']]['inflows'] = []
                                analyticsIds.results[attribute['value']]['outflows'] = []
                            analyticsIds.results[attribute['value']]['outflows'].append(lead['mkto_id'])           
                        
            
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    

            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 


# chart - "Pipeline Duration"   
def mkto_contacts_pipeline_duration(user_id, company_id, chart_name, mode, start_date): 
    print 'orig start'
    try:
        if mode == 'delta':
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-1)
        else:
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-60)
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        local_end_date_str = _str_from_date(local_end_date, 'short')
        local_start_date_str_long = _str_from_date(local_start_date)
        local_end_date_str_long = _str_from_date(local_end_date)
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        start_date_created_field_qry = 'source_created_date__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__mkto__exists'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        status_start_date_qry = 'statuses__mkto__date__gte'
        status_end_date_qry = 'statuses__mkto__date__lte'
        status_date_qry = 'statuses__mkto__date__startswith'
        
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        
        date_status_changes = {} # holds the changes in statuses on a daily basis
        date_status_durations = {} # holds the durations between status changes on a daily basis
        date_status_ids = {} # holds the IDs for status changes on a daily basis
            
        print 'getting into days'
        while s < (f - delta): # outer loop on the start date
            print 'date is ' + str(s)
            s += delta #increment the outer loop
            start_key = _str_from_date(s, 'short')
            #array_key = s.strftime('%m-%d-%Y')
            
            # get all leads who have a status change on this day
            querydict = {company_field_qry: company_id, system_field_qry: True, status_date_qry: start_key}   
            
            count = Lead.objects(**querydict).count()
            if count == 0:
                print 'leaving with no leads'
                continue # if no leads with status changes for this day, move to next day
            
            leads_with_statuses = Lead.objects(**querydict).only('mkto_id').only('statuses').only('source_created_date')
            
            unassigned_status = {}
            for lead in leads_with_statuses:
                print 'in lead loop'
                if len(lead['statuses']['mkto']) == 1: #if there's only one entry in status array, add the start date and status
                    unassigned_status['status'] = 'Unassigned'
                    created_date = get_current_timezone().localize(_date_from_str(lead['source_created_date']), is_dst=None)
                    unassigned_status['date'] = _str_from_date(created_date)
                    unassigned_status['id'] = lead['mkto_id']
                    lead['statuses']['mkto'].extend([unassigned_status])
                #sort the lead status array by date
                sorted_lead_statuses = sorted(lead['statuses']['mkto'], key=itemgetter('date'), reverse=True)
                sorted_lead_tuples = zip(sorted_lead_statuses[1:], sorted_lead_statuses) # we now have a tuple with each status and its previous status
                for i in range(len(sorted_lead_tuples)): # loop through the status tuples and find out which statuses changed today
                    if sorted_lead_tuples[i][1]['date'].startswith(start_key): # if the date of the second entry in the tuple matches today's date, this is a relevant status
                        #array_key holds the string key values of status changes e.g. "MQL - SQL"
                        array_key = sorted_lead_tuples[i][0]['status'] + '-' + sorted_lead_tuples[i][1]['status']
                        # duration is days between the status changes
                        duration = (_date_from_str(sorted_lead_tuples[i][1]['date']) - _date_from_str(sorted_lead_tuples[i][0]['date'])).days
                        if start_key not in date_status_changes: #if this day not yet in array
                            date_status_changes[start_key] = {}
                            date_status_changes[start_key][array_key] = 1
                            date_status_durations[start_key] = {}
                            date_status_durations[start_key][array_key] = duration
                            date_status_ids[start_key] = {}
                            date_status_ids[start_key][array_key] = []
                            date_status_ids[start_key][array_key].append(lead['mkto_id'])
                        else:
                            if array_key not in date_status_changes[start_key]: #if this particular status change not in today's array
                                date_status_changes[start_key][array_key] = 1
                                date_status_durations[start_key][array_key] = duration
                                date_status_ids[start_key][array_key] = []
                                date_status_ids[start_key][array_key].append(lead['mkto_id'])
                            else:
                                date_status_changes[start_key][array_key] += 1 # this status change already exists for today
                                date_status_durations[start_key][array_key] += duration #this currently holds the total of the durations; remember to divide by number of leads at the end of day
                                date_status_ids[start_key][array_key].append(lead['mkto_id'])
                    else: #this status did not take place today so move to next tuple
                        continue
                 
                #we are done with this lead
            # we are done with this day so divide the durations by the total number of status changes for each status pair for this day
            for key in date_status_changes[start_key].keys():
                date_status_durations[start_key][key] = date_status_durations[start_key][key] / date_status_changes[start_key][key]
        # we are done with all days            
        
#         print 'changes are ' + str(date_status_changes)  
#         print 'durations are ' + str(date_status_durations)    
#         print 'ids are ' + str(date_status_ids)       
#         return
            #check if there's already a analytics record for this day of the loop
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: 
                analyticsData = AnalyticsData()
            analyticsData.system_type = 'MA'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = start_key
            analyticsData.results = {}
            #print 'save 1'
            analyticsData.save()
            
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
            analyticsIds.system_type = 'MA'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = start_key
            analyticsIds.results = {}
            analyticsIds.save()
             
            for key in date_status_changes[start_key].keys(): # for each entry for this day, update the results in DB
                analyticsData.results[key] = {}
                analyticsData.results[key]['changes'] = date_status_changes[start_key][key]
                analyticsData.results[key]['durations'] = date_status_durations[start_key][key]
                analyticsIds.results[key] = date_status_ids[start_key][key]
           
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    
            
        print 'done'    
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 


# chart- Source Distribution Pie
def mkto_contacts_sources_pie(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-1)
        else:
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-60)
            
        print 'in there'
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        #local_start_date_str = _str_from_date(local_end_date, 'short')
        #local_end_date_str = _str_from_date(local_end_date, 'short')
        
        delta = timedelta(days=1)
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
            
        delta = timedelta(days=1)
        e = local_end_date
        
        
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            f = s + timedelta(days=1)
            f_date = f.strftime('%Y-%m-%d')
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
            
            #below code to be uncommented if IDs to be stored in AnalyticsIds
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
#             if analyticsIds is None:
#                 analyticsIds = AnalyticsIds()
#             analyticsIds.system_type = 'MA'
#             analyticsIds.company_id = company_id  
#             analyticsIds.chart_name = chart_name
#             analyticsIds.date = date
#             analyticsIds.results = {}
#             analyticsIds.save()
            
            querydict = {company_query: company_id, start_date_field_qry : date, end_date_field_qry: f_date}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            sources = Lead.objects(**querydict).item_frequencies('leads.mkto.originalSourceType')
            #print 'time 2 is ' + str(time.time())
            #print 'date is ' + date + ' found leads' + str(sources)
            #source_field_qry = 'leads__hspt__properties__hs_analytics_source'
            source_distr = {}
            for source in sources.keys():
                #querydict = {source_field_qry: source, company_query: company_id, start_date_field_qry : s, end_date_field_qry: f}
                encoded_source = encodeKey(source)
                source_distr[encoded_source] = sources[source]
                #below code to be uncommented if IDs to be stored in AnalyticsIds
#                 if source not in analyticsIds.results:
#                     analyticsIds.results[source] = []
#                     leads = Lead.objects(**querydict).only('hspt_id').all()
#                     for lead in leads:
#                         analyticsIds.results[source].append(lead['hspt_id'])
             
            #print 'time 3 is ' + str(time.time())
            for key in source_distr.keys():
                analyticsData.results[key] = source_distr[key]
                
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            #AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# chart- Revenue Source Distribution Pie
def mkto_contacts_revenue_sources_pie(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        print 'in there'
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        #local_start_date_str = _str_from_date(local_end_date, 'short')
        #local_end_date_str = _str_from_date(local_end_date, 'short')
        
        delta = timedelta(days=1)
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
        sfdc_account_field_qry = 'leads__mkto__sfdcAccountId__ne'
        opp_created_date_qry = 'opportunities__sfdc__CreatedDate__lte'
            
        delta = timedelta(days=1)
        e = local_end_date
        
        opps = {}
        ids = {}
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            f = s + timedelta(days=1)
            f_date = f.strftime('%Y-%m-%d')
            start_date_string = _str_from_date(s)
#             print 'date is ' + str(date)
#             print 's is ' + str(s)
            print 'start date string is ' + start_date_string
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
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
            
            querydict = {company_query: company_id, sfdc_account_field_qry: None}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            leads = Lead.objects(**querydict).only('leads.mkto.originalSourceType').only('opportunities.sfdc').only('mkto_id')
            # we have the leads with the opportunity data
            if len(leads) == 0:
                print 'no leads found'
                continue # got to next date if no valid leads for this date

            opps[date] = {}
            ids[date] = {}
            
            for lead in leads:
                print 'lead id is ' + lead['mkto_id']
                source = lead['leads']['mkto']['originalSourceType']
                if not 'sfdc' in lead['opportunities']:
                    continue
                lead_opps = lead['opportunities']['sfdc']
                for opp in lead_opps:
                    print 'starting opp ' + opp['Id'] 
#                     if opp['CreatedDate'][:10] > date: # if this opp is created after today's date, go to next opp
#                         continue
                    if opp['Amount'] is None: # don't consider opportunities with a null value
                        opp['Amount'] = 0
                    print 'beyond c with opp ' + opp['Id'] 
                    if opp['IsClosed'] == False or (opp['IsClosed'] == True and date < opp['CloseDate']): #open  opportunity created on or before this date OR closed opportunity but still open on this date
                        if date not in opps: # no other opp yet for this date
                            print 'in 1/1 with ' + opp['Id']
                            opps[date] = {}
                            opps[date][source] = {}
                            opps[date][source]['open'] = opp['Amount']
                            opps[date][source]['closed'] = 0
                            
                            ids[date] = {}
                            ids[date][source] = {}
                            ids[date][source]['open'] = []
                            ids[date][source]['closed'] = []
                            ids[date][source]['open'].append(lead['mkto_id'])
                        else: #atleast one more opp for this date already exists
                            print 'in 2/1 with ' + opp['Id']
                            if source not in opps[date]:
                                opps[date][source] = {}
                                opps[date][source]['open'] = opp['Amount']
                                opps[date][source]['closed'] = 0
                        
                                ids[date][source] = {}
                                ids[date][source]['open'] = []
                                ids[date][source]['closed'] = []
                                ids[date][source]['open'].append(lead['mkto_id'])
                            else: #source already exists
                                opps[date][source]['open'] += opp['Amount']
                                ids[date][source]['open'].append(lead['mkto_id'])
                            
                    elif opp['IsClosed'] and date == opp['CloseDate']: # opp is closed on this date
                        if date not in opps: # no other opp yet for this date
                            print 'in 1/2 with ' + opp['Id']
                            opps[date] = {}
                            opps[date][source] = {}
                            opps[date][source]['open'] = 0
                            opps[date][source]['closed'] = opp['Amount']
                            
                            ids[date] = {}
                            ids[date][source] = {}
                            ids[date][source]['closed'] = []
                            ids[date][source]['open'] = []
                            ids[date][source]['closed'].append(lead['mkto_id'])
                        else: #atleast one more opp for this date already exists
                            print 'in 2/2 with ' + opp['Id']
                            if source not in opps[date]:
                                opps[date][source] = {}
                                opps[date][source]['open'] = 0
                                opps[date][source]['closed'] = opp['Amount']
                                
                                ids[date][source] = {}
                                ids[date][source]['closed'] = []
                                ids[date][source]['open'] = []
                                ids[date][source]['closed'].append(lead['mkto_id'])
                            else: #source already exists
                                opps[date][source]['closed'] += opp['Amount']
                                ids[date][source]['closed'].append(lead['mkto_id'])
                                
            # we are done for this day so do calculations and save the record in DB
            analyticsData.results = {}
            analyticsIds.results = {}
            for entry in opps[date]: 
                encoded_key = encodeKey(entry)
                analyticsData.results[encoded_key] = {}
                analyticsData.results[encoded_key]['open'] = opps[date][entry]['open']
                analyticsData.results[encoded_key]['closed'] = opps[date][entry]['closed']
                
                analyticsIds.results[encoded_key] = {}
                analyticsIds.results[encoded_key]['open'] = ids[date][entry]['open']
                analyticsIds.results[encoded_key]['closed'] = ids[date][entry]['closed']
            print 'saving' 
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            print 'saved'
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
        
        #general variables
        chart_name = 'waterfall'
        sync_to_sfdc_activity_type_id = 19 #mkto activity type id
        change_value_activity_type_id = 13 #mkto activity type id
        collection = Lead._get_collection()
        data = {}
        ids = {}
        
        #get all the leads that were transferred to Salesforce for this company
        if crm_system_code == 'sfdc':
            existingIntegration = CompanyIntegration.objects(company_id = company_id).first()   
            if 'sfdc' in existingIntegration['integrations']:
                try:
                    sfdc_sal_status = existingIntegration['integrations']['sfdc']['mapping']['sal_status']
                    sfdc_sql_status = existingIntegration['integrations']['sfdc']['mapping']['sql_status']
                    mkto_sync_user = existingIntegration['integrations']['sfdc']['mapping']['mkto_sync_user']
                except Exception as e:
                    print 'Details not completely defined in SFDC integration'
                    raise ValueError('Details not completely defined in SFDC integration')
            
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
                #find all leads in MKTO that did not come from SFDC or were not synched into SFDC and were created today 
                mkto_leads_raw = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'leads.mkto.sfdcLeadId' : {'$exists': False}, 'source_created_date': {'$gte' : utc_day_start, '$lte': utc_day_end}})
                mkto_leads_raw_list = list(mkto_leads_raw)
                data['num_mktg_raw_leads'] = len(mkto_leads_raw_list) 
                ids['mktg_raw_leads'] = [d['mkto_id'] for d in mkto_leads_raw_list]
                #find all leads that were synched to CRM today (successfully - which means Lead Status activity has to occur at the same time as the sync
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
                                if this_lead_done:
                                    break #stop processing this lead if one activity already found
                print 'sync activities are ' + str(sync_activities_list) 
                #now that all leads have been processed for MQL for today, count them
                data['num_mql'] =  len(sync_activities_list)    
                ids['mql'] = [d['lead_id'] for d in sync_activities_list]
                print 'going to sales'
                #branch to sfdc module for the rest of the metrics  
                sales_data, sales_ids = sfdc_waterfall_sub(user_id = user_id, company_id = company_id, utc_day_start = utc_day_start, utc_day_end = utc_day_end, date = date, caller = 'mkto', sfdc_sal_status = sfdc_sal_status, sfdc_sql_status = sfdc_sql_status, mkto_sync_user = mkto_sync_user)
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
    
def sfdc_waterfall_sub(user_id, company_id, utc_day_start, utc_day_end, date, caller,  sfdc_sal_status, sfdc_sql_status, mkto_sync_user):
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
            sfdc_leads_raw = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'source_created_date': {'$gte' : utc_day_start, '$lte': utc_day_end}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            sfdc_leads_raw_list = list(sfdc_leads_raw)
            data['num_sales_raw_leads'] = len(sfdc_leads_raw_list) 
            print 'sfdc list is ' + str([d['_id'] for d in sfdc_leads_raw_list])
            ids['sales_raw_leads'] = [d['sfdc_id'] for d in sfdc_leads_raw_list]
            print 'passed'
        
        #convert dates to strings for SAL and SQL queries
        utc_day_start_string = datetime.strftime(utc_day_start, '%Y-%m-%dT%H-%M-%S.000+0000')
        utc_day_end_string = datetime.strftime(utc_day_end, '%Y-%m-%dT%H-%M-%S.000+0000')
        # find all leads that went into SAL status today 
        if caller == 'sfdc':
            data['num_mktg_sal'] = 0
            data['num_mktg_sql'] = 0
            sfdc_sales_sal = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'activities.sfdc': {'$elemMatch' : {'NewValue' :sfdc_sal_status, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}})
            sfdc_sales_sal_list = list(sfdc_sales_sal)
            data['num_sales_sal'] = len(sfdc_sales_sal_list)
            ids['sales_sal'] = [d['sfdc_id'] for d in sfdc_sales_sal_list]
        elif caller == 'mkto':
            sfdc_sales_sal = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'activities.sfdc': {'$elemMatch' : {'NewValue' :sfdc_sal_status, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            sfdc_sales_sal_list = list(sfdc_sales_sal)
            data['num_sales_sal'] = len(sfdc_sales_sal_list)
            ids['sales_sal'] = [d['sfdc_id'] for d in sfdc_sales_sal_list]
            sfdc_mktg_sal = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'activities.sfdc': {'$elemMatch' : {'NewValue' :sfdc_sal_status, 'CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}}},  'leads.sfdc.CreatedById' : {'$eq': mkto_sync_user}})
            sfdc_mktg_sal_list = list(sfdc_mktg_sal)
            data['num_mktg_sal'] = len(sfdc_mktg_sal_list)
            ids['mktg_sal'] = [d['mkto_id'] for d in sfdc_mktg_sal_list]
            sfdc_sales_opps = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'opportunities.sfdc.CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            sfdc_sales_opps_list = list(sfdc_sales_opps)
            data['num_sales_opps'] = len(sfdc_sales_opps_list)
            ids['sales_opps'] = [d['sfdc_id'] for d in sfdc_sales_opps_list]
            sfdc_mktg_opps = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'opportunities.sfdc.CreatedDate' : {'$gte' : utc_day_start_string, '$lte': utc_day_end_string}, 'leads.sfdc.CreatedById' : {'$eq': mkto_sync_user}})
            sfdc_mktg_opps_list = list(sfdc_mktg_opps)
            data['num_mktg_opps'] = len(sfdc_mktg_opps_list)
            ids['mktg_opps'] = [d['mkto_id'] for d in sfdc_mktg_opps_list]
            sfdc_sales_closed_deals = collection.find({'company_id' : int(company_id), 'sfdc_id' : {'$exists': True}, 'opportunities.sfdc.CloseDate' : date, 'opportunities.sfdc.IsWon': True, 'leads.sfdc.CreatedById' : {'$ne': mkto_sync_user}})
            sfdc_sales_closed_deals_list = list(sfdc_sales_closed_deals)
            data['num_sales_closed_deals'] = len(sfdc_sales_closed_deals_list)
            ids['sales_closed_deals'] = [d['sfdc_id'] for d in sfdc_sales_closed_deals_list]
            sfdc_mktg_closed_deals = collection.find({'company_id' : int(company_id), 'mkto_id' : {'$exists': True}, 'opportunities.sfdc.CloseDate' : date, 'opportunities.sfdc.IsWon': True, 'leads.sfdc.CreatedById' : {'$eq': mkto_sync_user}})
            sfdc_mktg_closed_deals_list = list(sfdc_mktg_closed_deals)
            data['num_mktg_closed_deals'] = len(sfdc_mktg_closed_deals_list)
            ids['mktg_closed_deals'] = [d['mkto_id'] for d in sfdc_mktg_closed_deals_list]
            
            
        return data, ids   
            
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# begin HSPT analytics
# first chart - 'Timeline"
def hspt_sources_bar_chart(user_id, company_id, chart_name, mode, start_date): 
    company_field_qry = 'company_id'
    system_field_qry = 'leads__hspt__exists'
    querydict = {system_field_qry: True, company_field_qry: company_id}
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
#             system_type_query = 'system_type'
#             company_query = 'company_id'
#             chart_name_query = 'chart_name'
#             queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name}
#             analyticsData = AnalyticsData.objects(**queryDict).first()
        else:
            #start_date = datetime.utcnow() + timedelta(-30)
            start_date = start_date
            #firstDate = Lead.objects(**querydict).only('source_created_date').order_by('source_created_date').first()
            print 'date string is ' + str(start_date)
            #start_date = firstDate['source_created_date']
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        print 'diff is ' + str((local_end_date - local_start_date).days)
        subscriber_values_temp_array = {}
        lead_values_temp_array = {}
        mql_values_temp_array = {}
        sql_values_temp_array = {}
        opp_values_temp_array = {}
        customer_values_temp_array = {}
        
        subscriber_ids_temp_array = {}
        lead_ids_temp_array = {}
        mql_ids_temp_array = {}
        sql_ids_temp_array = {}
        opp_ids_temp_array = {}
        customer_ids_temp_array = {}
        
        all_dates = []
        
        company_field_qry = 'company_id'
        #print 'co is ' + str(company_id)
        #start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        start_date_created_field_qry = 'source_created_date__gte'
        system_field_qry = 'leads__hspt__exists'
        
        #querydict = {system_field_qry: True, company_field_qry: company_id, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        #existingLeads = Lead.objects(**querydict)
        
        collection = Lead._get_collection()
        existingLeads = collection.find({'company_id': int(company_id), 'source_created_date': {'$lte': local_end_date}}, batch_size=1000) #'$gte': local_start_date, 
        
        print ' count of leads ' + str(existingLeads.count())
        if existingLeads is None:
            return 
        delta = timedelta(days=1)
        e = local_end_date
        #date_field_map = { "subscriber" : 'hs_lifecyclestage_subscriber_date', "lead" : 'hs_lifecyclestage_lead_date', "marketingqualifiedlead" : 'hs_lifecyclestage_marketingqualifiedlead_date', "salesqualifiedlead" : 'hs_lifecyclestage_salesqualifiedlead_date', "opportunity" : 'hs_lifecyclestage_opportunity_date', "customer" : 'hs_lifecyclestage_customer_date' } 
        date_field_map = { "subscriber" : 'hspt_subscriber_date', "lead" : 'hspt_lead_date', "marketingqualifiedlead" : 'hspt_mql_date', "salesqualifiedlead" : 'hspt_sql_date', "opportunity" : 'hspt_opp_date', "customer" : 'hspt_customer_date' } 
        this_lead_done_for_day = False
        
        lead_counter = 0
        for lead in existingLeads:
            print 'lead id is ' + str(lead['hspt_id'])
            lead_counter += 1
            print 'leadcount is ' + str(lead_counter)
            s = local_start_date - timedelta(days=1)
            #properties = lead.leads['hspt']['properties']
            current_stage = lead['source_stage']
            if current_stage not in date_field_map or current_stage is None: #if the stage is not defined in our map, skip the lead
                continue
            if date_field_map[current_stage] not in lead: #weird case where there's no date for current stage
                continue
            if lead[date_field_map[current_stage]] is None:
                continue
            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
            current_stage_date = current_stage_date.astimezone(get_current_timezone())
            print 'current stage date is ' + str(current_stage_date) + ' and stage is ' + current_stage
            while s < (e - delta):
                #print 's is ' + str(s) + ' and e is ' + str(e)
                s += delta #increment the day counter
                this_lead_done_for_day = False
                current_stage = lead['source_stage'] # needs to be repeated here since current_stage is changed in the steps below
                #current_stage = properties['lifecyclestage']
                
                #print 'enter date loop with start ' + str(s) + ' and end ' + str(e)
                #current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                
                array_key = s.strftime('%Y-%m-%d')
                if array_key not in all_dates:
                    all_dates.append(array_key)
                            
                if current_stage == 'customer':
                    #print 'current stage date is ' + str(current_stage_date) + ' and s is ' + str(s)
                    if current_stage_date <= s: #and current_stage_date <= local_end_date:
                        if array_key in customer_values_temp_array:
                            customer_values_temp_array[array_key] += 1
                        else:
                            customer_values_temp_array[array_key] = 1
                        if not array_key in customer_ids_temp_array:
                            customer_ids_temp_array[array_key] = []
                        customer_ids_temp_array[array_key].append(lead['hspt_id'])
                        this_lead_done_for_day = True
                        continue  
                    if this_lead_done_for_day == False:
                        current_stage = 'opportunity'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in opp_values_temp_array:
                                    opp_values_temp_array[array_key] += 1
                                else:
                                    opp_values_temp_array[array_key] = 1
                                if not array_key in opp_ids_temp_array:
                                    opp_ids_temp_array[array_key] = []
                                opp_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                if not array_key in sql_ids_temp_array:
                                    sql_ids_temp_array[array_key] = []
                                sql_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'opportunity':
                    #current_stage = 'opportunity'
                    if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in opp_values_temp_array:
                                opp_values_temp_array[array_key] += 1
                            else:
                                opp_values_temp_array[array_key] = 1
                            if not array_key in opp_ids_temp_array:
                                opp_ids_temp_array[array_key] = []
                            opp_ids_temp_array[array_key].append(lead['hspt_id'])
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                if not array_key in sql_ids_temp_array:
                                    sql_ids_temp_array[array_key] = []
                                sql_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'salesqualifiedlead':
                    #current_stage = 'salesqualifiedlead'
                    if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in sql_values_temp_array:
                                sql_values_temp_array[array_key] += 1
                            else:
                                sql_values_temp_array[array_key] = 1
                            if not array_key in sql_ids_temp_array:
                                sql_ids_temp_array[array_key] = []
                            sql_ids_temp_array[array_key].append(lead['hspt_id'])
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'marketingqualifiedlead':
                    if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in mql_values_temp_array:
                                mql_values_temp_array[array_key] += 1
                            else:
                                mql_values_temp_array[array_key] = 1
                            if not array_key in mql_ids_temp_array:
                                mql_ids_temp_array[array_key] = []
                            mql_ids_temp_array[array_key].append(lead['hspt_id'])
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'lead':
                    if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in lead_values_temp_array:
                                lead_values_temp_array[array_key] += 1
                            else:
                                lead_values_temp_array[array_key] = 1
                            if not array_key in lead_ids_temp_array:
                                lead_ids_temp_array[array_key] = []
                            lead_ids_temp_array[array_key].append(lead['hspt_id'])
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                                this_lead_done_for_day = True 
                                continue
                                    
                elif current_stage == 'subscriber':
                    if date_field_map[current_stage] in lead and lead[date_field_map[current_stage]] is not None:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in subscriber_values_temp_array:
                                subscriber_values_temp_array[array_key] += 1
                            else:
                                subscriber_values_temp_array[array_key] = 1
                            if not array_key in subscriber_ids_temp_array:
                                subscriber_ids_temp_array[array_key] = []
                            subscriber_ids_temp_array[array_key].append(lead['hspt_id'])
                            this_lead_done_for_day = True 
                            continue
        
        #print 'found record for ' + str(subscriber_values_temp_array)
        #save the records in the DB
        
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_query = 'date'
        
        for date in all_dates:
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_query: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.results["Subscribers"] = {}
                analyticsData.results["Leads"] = {}
                analyticsData.results["MQLs"] = {}
                analyticsData.results["SQLs"] = {}
                analyticsData.results["Opportunities"] = {}
                analyticsData.results["Customers"] = {}
            
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.system_type = 'MA'
                analyticsIds.company_id = company_id  
                analyticsIds.chart_name = chart_name
                analyticsIds.date = date
                analyticsIds.results = {}
                analyticsIds.results["Subscribers"] = {}
                analyticsIds.results["Leads"] = {}
                analyticsIds.results["MQLs"] = {}
                analyticsIds.results["SQLs"] = {}
                analyticsIds.results["Opportunities"] = {}
                analyticsIds.results["Customers"] = {}
             
            analyticsData.date = date 
            analyticsIds.date = date 
             
            if date in subscriber_values_temp_array.keys():
                analyticsData.results["Subscribers"] = subscriber_values_temp_array[date]
                analyticsIds.results["Subscribers"] = subscriber_ids_temp_array[date]
            else:
                analyticsData.results["Subscribers"] = 0  
                analyticsIds.results["Subscribers"] = []  
            
            
            if date in lead_values_temp_array.keys():
                analyticsData.results["Leads"] = lead_values_temp_array[date]
                analyticsIds.results["Leads"] = lead_ids_temp_array[date]
            else:
                analyticsData.results["Leads"] = 0 
                analyticsIds.results["Leads"] = []
                
            
            if date in mql_values_temp_array.keys():
                analyticsData.results["MQLs"] = mql_values_temp_array[date]
                analyticsIds.results["MQLs"] = mql_ids_temp_array[date]
            else:
                analyticsData.results["MQLs"] = 0 
                analyticsIds.results["MQLs"] = []
            
            if date in sql_values_temp_array.keys():
                analyticsData.results["SQLs"] = sql_values_temp_array[date]
                analyticsIds.results["SQLs"] = sql_ids_temp_array[date]
            else:
                analyticsData.results["SQLs"] = 0 
                analyticsIds.results["SQLs"] = [] 
  
            
            if date in opp_values_temp_array.keys():
                analyticsData.results["Opportunities"] = opp_values_temp_array[date]
                analyticsIds.results["Opportunities"] = opp_ids_temp_array[date]
            else:
                analyticsData.results["Opportunities"] = 0
                analyticsIds.results["Opportunities"] = []
                
            
            if date in customer_values_temp_array.keys():
                analyticsData.results["Customers"] = customer_values_temp_array[date]
                analyticsIds.results["Customers"] = customer_ids_temp_array[date]
            else:
                analyticsData.results["Customers"] = 0
                analyticsIds.results["Customers"] = []
            
            analyticsData.save()
            analyticsIds.save()
        
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 


# chart - "Contacts  Distribution"   
def hspt_contacts_distr_chart(user_id, company_id, chart_name, mode, start_date): 
    #print 'orig start' + str(start_date)
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
        local_end_date_str = _str_from_date(local_end_date, 'short')
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        start_date_created_field_qry = 'source_created_date__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__hspt__exists'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
            
        
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        while s < (f - delta): # outer loop on the start date
            s += delta #increment the outer loop
            start_key = _str_from_date(s, 'short')
            #array_key = s.strftime('%m-%d-%Y')
            
            # look for leads that were created before or on this date and no later than the last date of the range we are looking for
            querydict = {company_field_qry: company_id, system_field_qry: True, end_date_created_field_qry: start_key} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            statuses = Lead.objects(**querydict).item_frequencies('source_stage')
            if None in statuses:
                statuses['Unassigned'] = statuses.pop(None)
            print 'statuses for ' + start_key + ' are ' + str(statuses)  
            
            #use map reduce to group lead ids by status - not used
            map_f = """
                function() {
                   emit(this.source_status, {id: this.mkto_id});
                   }
                   """
            reduce_f = """
                function(keyStatus, mktoIdArray ) {
                   var ret = {ids: []};
                   var ids = {};
                    for (var i =0 ; i < mktoIdArray.length; i++)
                    {   
                        ret.ids.push(mktoIdArray[i].id);
                    }
                   return ret;
                   }
                   """

            hsptIds =  Lead.objects(**querydict).aggregate( { '$group': { '_id': '$source_status', 'hspt_id': { '$push': '$hspt_id' } } } ) #.map_reduce(map_f, reduce_f, 'test')
            #mktoIds = list(mktoIds)
         
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: 
                analyticsData = AnalyticsData()
            analyticsData.system_type = 'MA'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = start_key
            analyticsData.results = {}
            #print 'save 1'
            analyticsData.save()
            
            #update the totals for each status for this day
            for status in statuses:
                analyticsData.results[status] = {}
                analyticsData.results[status]['total'] = statuses[status]
                analyticsData.results[status]['inflows'] = 0
                analyticsData.results[status]['outflows'] = 0
            
            queryDict = {company_field_qry : company_id, system_type_qry: 'MA', chart_name_qry: chart_name, date_qry: start_key}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
            analyticsIds.system_type = 'MA'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = start_key
            analyticsIds.results = {}
            analyticsIds.save()
            
            #update the IDs for each status for this day
            for entry in list(hsptIds):
                #print 'mktoIds key is ' + str(entry['_id']) + ' of length ' + str(len(entry['mkto_id']))# + ' and val is ' + str(mktoId.value)
                if entry['_id'] is None: 
                    entry['_id'] = 'Unassigned'
                analyticsIds.results[entry['_id']] = {}
                analyticsIds.results[entry['_id']]['total'] = entry['hspt_id']
                analyticsIds.results[entry['_id']]['inflows'] = []
                analyticsIds.results[entry['_id']]['outflows'] = []
            
            # done with the lead statuses, now move on to Inflows and Outflows
#             activity_date_qry = 'activities__mkto__activityDate__startswith'
#             activity_name_qry = 'activities__mkto__activityTypeName__exact'
#             activity_name = 'Change Data Value'
#             activity_attribute_qry = 'activities__mkto__primaryAttributeValue__exact'
#             activity_attribute = 'Lead Status'
#             #print ' getting into q'
#             querydict = {activity_date_qry: start_key, activity_attribute_qry: activity_attribute,  activity_name_qry: activity_name , company_field_qry: company_id, system_field_qry: True, end_date_created_field_qry: start_key}
#             leads_with_activities = Lead.objects(**querydict).timeout(False) 
#             #print 'found leads' + str(len(leads_with_activities))
#             #&  Q(company_id= company_id, leads__mkto__exists= True, source_created_date__lte= start_key)
#              
#             for lead in leads_with_activities:
#                 #nelow line needed to extract the relevant Status Change activites and ignore the rest
#                 activities = [a for a in lead['activities']['mkto'] if a['activityTypeName'] == activity_name and a['primaryAttributeValue'] == activity_attribute and a['activityDate'].startswith(start_key)]
#                 #activities = lead['activities']['mkto']
#                 #print 'act is ' + str(activities)
#                 for activity in activities:
#                     attributes = [b for b in activity['attributes'] if b['name'] == 'New Value' or b['name'] == 'Old Value']
#                     for attribute in attributes:
#                         #inflows
#                         if attribute['name'] == 'New Value': # this is a positive for the lead
#                             if attribute['value'] is None:
#                                 attribute['value'] = 'Unassigned'
#                             if attribute['value'] in statuses: #if this status is already in statuses list
#                                 print 'status fond is ' + attribute['value']
#                                 analyticsData.results[attribute['value']]['inflows'] += 1 # increment the number of inflows
#                             else: # for some reason, this status does not yet exist in  the statuses list
#                                 analyticsData.results[attribute['value']] = {}
#                                 analyticsData.results[attribute['value']]['total'] = 0
#                                 analyticsData.results[attribute['value']]['inflows'] = 1
#                                 analyticsData.results[attribute['value']]['outflows'] = 0
#                             if attribute['value'] not in analyticsIds.results:
#                                 analyticsIds.results[attribute['value']] = {}
#                                 analyticsIds.results[attribute['value']]['inflows'] = []
#                                 analyticsIds.results[attribute['value']]['outflows'] = []
#                             analyticsIds.results[attribute['value']]['inflows'].append(lead['mkto_id'])
#                         #outflows
#                         if attribute['name'] == 'Old Value': # this is a positive for the lead
#                             if attribute['value'] is None:
#                                 attribute['value'] = 'Unassigned'
#                             if attribute['value'] in statuses: #if this status is already in statuses list
#                                 analyticsData.results[attribute['value']]['outflows'] -= 1 # decrement the number of outflows
#                             else: # for some reason, this status does not yet exist in  the statuses list
#                                 analyticsData.results[attribute['value']] = {}
#                                 analyticsData.results[attribute['value']]['total'] = 0
#                                 analyticsData.results[attribute['value']]['inflows'] = 0
#                                 analyticsData.results[attribute['value']]['outflows'] = -1
#                             if attribute['value'] not in analyticsIds.results:
#                                 analyticsIds.results[attribute['value']] = {}
#                                 analyticsIds.results[attribute['value']]['inflows'] = []
#                                 analyticsIds.results[attribute['value']]['outflows'] = []
#                             analyticsIds.results[attribute['value']]['outflows'].append(lead['mkto_id'])           
#                         
#             
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    

            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 
    
# chart - "Contacts  Distribution"   
def hspt_contacts_distr_chart_deprecated(user_id, company_id, chart_name, mode, start_date): 
    #print 'orig start' + str(start_date)
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-30)
            start_date = start_date
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        #start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__hspt__exists'
            
        querydict = {company_field_qry: company_id, system_field_qry: True, end_date_created_field_qry: local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            
        
        existingLeads = Lead.objects(**querydict).timeout(False)
        for lead in existingLeads: # for every lead
            properties = lead.leads['hspt']['properties']
            s = local_start_date - timedelta(days=1)
            f = local_end_date #absolute last date of range
            while s < (f - delta): # outer loop on the start date
                s += delta #increment the outer loop
                start_key = s.strftime('%m-%d-%Y')
                print 'working on ' + start_key
                this_lead_done_for_range = False
                e = s  # start inner loop
                while e < f: # inner loop till the end date is hit
                    e += delta #increment inner loop
                    end_key = e.strftime('%m-%d-%Y')
                    range = start_key + ' - ' + end_key
                    print 'and end date ' + end_key
                    if not range in date_array:
                        date_array[range] = {}
                    if not range in ids_array:
                        ids_array[range] = {}
                    this_lead_done_for_range = False
                    if 'hs_lifecyclestage_customer_date' in properties:
                        local_customer_date = pytz.utc.localize(properties['hs_lifecyclestage_customer_date'], is_dst=None)
                        local_customer_date = local_customer_date.astimezone(get_current_timezone())
                        if local_customer_date >= s and local_customer_date <= e:
                            if 'Customers' in date_array[range]:
                                date_array[range]['Customers'] += 1
                            else:
                                date_array[range]['Customers'] = 1
                            if 'Customers' not in ids_array[range]:
                                ids_array[range]['Customers'] = []
                            ids_array[range]['Customers'].append(lead['hspt_id'])  
                            this_lead_done_for_range = True              
                            
                    if not this_lead_done_for_range and 'hs_lifecyclestage_opportunity_date' in properties:
                        local_opp_date = pytz.utc.localize(properties['hs_lifecyclestage_opportunity_date'], is_dst=None)
                        local_opp_date = local_opp_date.astimezone(get_current_timezone())
                        if local_opp_date >= s and local_opp_date <= e:
                            if 'Opportunities' in date_array[range]:
                                date_array[range]['Opportunities'] += 1
                            else:
                                date_array[range]['Opportunities'] = 1
                            if 'Opportunities' not in ids_array[range]:
                                ids_array[range]['Opportunities'] = []
                            ids_array[range]['Opportunities'].append(lead['hspt_id'])  
                            this_lead_done_for_range = True      
                            
                    if not this_lead_done_for_range and 'hs_lifecyclestage_salesqualifiedlead_date' in properties:
                        local_sql_date = pytz.utc.localize(properties['hs_lifecyclestage_salesqualifiedlead_date'], is_dst=None)
                        local_sql_date = local_sql_date.astimezone(get_current_timezone())
                        if local_sql_date >= s and local_sql_date <= e:
                            if 'SQLs' in date_array[range]:
                                date_array[range]['SQLs'] += 1
                            else:
                                date_array[range]['SQLs'] = 1
                            if 'SQLs' not in ids_array[range]:
                                ids_array[range]['SQLs'] = []
                            ids_array[range]['SQLs'].append(lead['hspt_id']) 
                            this_lead_done_for_range = True
        
                    if not this_lead_done_for_range and 'hs_lifecyclestage_marketingqualifiedlead_date' in properties:
                        local_mql_date = pytz.utc.localize(properties['hs_lifecyclestage_marketingqualifiedlead_date'], is_dst=None)
                        local_mql_date = local_mql_date.astimezone(get_current_timezone())
                        if local_mql_date >= s and local_mql_date <= e:
                            if 'MQLs' in date_array[range]:
                                date_array[range]['MQLs'] += 1
                            else:
                                date_array[range]['MQLs'] = 1
                            if 'MQLs' not in ids_array[range]:
                                ids_array[range]['MQLs'] = []
                            ids_array[range]['MQLs'].append(lead['hspt_id']) 
                            this_lead_done_for_range = True
                            
                    if not this_lead_done_for_range and 'hs_lifecyclestage_lead_date' in properties:
                        local_lead_date = pytz.utc.localize(properties['hs_lifecyclestage_lead_date'], is_dst=None)
                        local_lead_date = local_lead_date.astimezone(get_current_timezone())
                        if local_lead_date >= s and local_lead_date <= e:
                            if 'Leads' in date_array[range]:
                                date_array[range]['Leads'] += 1
                            else:
                                date_array[range]['Leads'] = 1
                            if 'Leads' not in ids_array[range]:
                                ids_array[range]['Leads'] = []
                            ids_array[range]['Leads'].append(lead['hspt_id']) 
                            this_lead_done_for_range = True
                     
                    if not this_lead_done_for_range and 'hs_lifecyclestage_subscriber_date' in properties:
                        local_subscriber_date = pytz.utc.localize(properties['hs_lifecyclestage_subscriber_date'], is_dst=None)
                        local_subscriber_date = local_subscriber_date.astimezone(get_current_timezone())
                        if local_subscriber_date >= s and local_subscriber_date <= e:
                            if 'Subscribers' in date_array[range]:
                                date_array[range]['Subscribers'] += 1
                            else:
                                date_array[range]['Subscribers'] = 1
                            if 'Subscribers' not in ids_array[range]:
                                ids_array[range]['Subscribers'] = []
                            ids_array[range]['Subscribers'].append(lead['hspt_id']) 
                            this_lead_done_for_range = True
                    
                    if not 'Customers' in date_array[range]:
                        date_array[range]['Customers'] = 0
                    if not 'Opportunities' in date_array[range]:
                        date_array[range]['Opportunities'] = 0
                    if not 'SQLs' in date_array[range]:
                        date_array[range]['SQLs'] = 0
                    if not 'MQLs' in date_array[range]:
                        date_array[range]['MQLs'] = 0
                    if not 'Leads' in date_array[range]:
                        date_array[range]['Leads'] = 0
                    if not 'Subscribers' in date_array[range]:
                        date_array[range]['Subscribers'] = 0
                        
                    if not 'Customers' in ids_array[range]:
                        ids_array[range]['Customers'] = []
                    if not 'Opportunities' in ids_array[range]:
                        ids_array[range]['Opportunities'] = []
                    if not 'SQLs' in ids_array[range]:
                        ids_array[range]['SQLs'] = []
                    if not 'MQLs' in ids_array[range]:
                        ids_array[range]['MQLs'] = []
                    if not 'Leads' in ids_array[range]:
                        ids_array[range]['Leads'] = []
                    if not 'Subscribers' in ids_array[range]:
                        ids_array[range]['Subscribers'] = []
        
            
            
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_range_query = 'date_range'
            
        for date_range in date_array.keys():
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_range_query: date_range}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
            analyticsData.system_type = 'MA'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date_range = date_range
            analyticsData.results = {}
            analyticsData.results = date_array[date_range]
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_range_query: date_range}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
            analyticsIds.system_type = 'MA'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date_range = date_range
            analyticsIds.results = {}
            analyticsIds.results = ids_array[date_range]
            
            analyticsData.save()
            analyticsIds.save()
        
        
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})       
  

def hspt_contacts_pipeline_duration(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-30)
            start_date = start_date
            
            
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        utc_current_date = datetime.utcnow()
        delta = timedelta(days=1)
        date_array = {}
 
        date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' } 
        
        stage_field_map = OrderedDict() #{"Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer'})
        stage_field_map["Subscribers"] = 'subscriber'
        stage_field_map["Leads"] = 'lead'
        stage_field_map["MQLs"] = 'marketingqualifiedlead'
        stage_field_map["SQLs"] = 'salesqualifiedlead'
        stage_field_map["Opportunities"] = 'opportunity'
        stage_field_map["Customers"] = 'customer' 
        
        average_days_in_this_stage_list = OrderedDict() #{ "Subscribers" : 0, "Leads" : 0, "MQLs" : 0, "SQLs" : 0, "Opportunities" : 0, "Customers" : 0}
        average_days_in_this_stage_list["Subscribers"] = 0
        average_days_in_this_stage_list["Leads"] = 0
        average_days_in_this_stage_list["MQLs"] = 0
        average_days_in_this_stage_list["SQLs"] = 0
        average_days_in_this_stage_list["Opportunities"] = 0
        average_days_in_this_stage_list["Customers"] = 0
        
        transition_field_map = {"S->L":0, "L->M":0, "M->S":0, "S->O":0, "O->C":0 }
        transitions_days = OrderedDict() #{ "Subscribers" : 0, "Leads" : 0, "MQLs" : 0, "SQLs" : 0, "Opportunities" : 0, "Customers" : 0}
        transitions_ids = OrderedDict()
        transitions_leads = OrderedDict()
        for stage in stage_field_map:
            transitions_days[stage] = OrderedDict()
            transitions_days["all"] = OrderedDict()
            transitions_ids[stage] = OrderedDict()
            transitions_ids["all"] = OrderedDict()
            transitions_leads[stage] = OrderedDict()
            transitions_leads["all"] = OrderedDict()
            if stage != "Subscribers":
                transitions_days[stage]["S->L"] = 0 #, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
                transitions_days["all"]["S->L"] = 0 
                transitions_ids[stage]["S->L"] = [] #, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
                transitions_ids["all"]["S->L"] = [] 
                transitions_leads[stage]["S->L"] = 0 #, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
                transitions_leads["all"]["S->L"] = 0
                if stage != "Leads":
                    transitions_days[stage]["L->M"] = 0
                    transitions_days["all"]["L->M"] = 0
                    transitions_ids[stage]["L->M"] = []
                    transitions_ids["all"]["L->M"] = []
                    transitions_leads[stage]["L->M"] = 0
                    transitions_leads["all"]["L->M"] = 0
                    if stage != "MQLs":
                        transitions_days[stage]["M->S"] = 0
                        transitions_days["all"]["M->S"] = 0
                        transitions_ids[stage]["M->S"] = []
                        transitions_ids["all"]["M->S"] = []
                        transitions_leads[stage]["M->S"] = 0
                        transitions_leads["all"]["M->S"] = 0
                        if stage != "SQLs":
                            transitions_days[stage]["S->O"] = 0
                            transitions_days["all"]["S->O"] = 0
                            transitions_ids[stage]["S->O"] = []
                            transitions_ids["all"]["S->O"] = []
                            transitions_leads[stage]["S->O"] = 0
                            transitions_leads["all"]["S->O"] = 0
                            if stage != "Opportunities":
                                transitions_days[stage]["O->C"] = 0  
                                transitions_days["all"]["O->C"] = 0 
                                transitions_ids[stage]["O->C"] = [] 
                                transitions_ids["all"]["O->C"] = []
                                transitions_leads[stage]["O->C"] = 0  
                                transitions_leads["all"]["O->C"] = 0   
        
        average_days = []
        transition_label_map = {"S->L":1, "L->M":2, "M->S":3, "S->O":4, "O->C":5 } #{"S->L":"Leads", "L->M":"MQLs", "M->S":"SQLs", "S->O":"Opportunities", "O->C":"Customers" }
        stage_label_map = {"Subscribers":0, "Leads":1, "MQLs":2, "SQLs":3, "Opportunities":4, "Customers":5 }
        
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_range_query = 'date_range'
                
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        
        
        while s < (f - delta): # outer loop on the start date
            s += delta #increment the outer loop
            start_key = s.strftime('%m-%d-%Y')
            print 'working on ' + start_key
            this_lead_done_for_range = False
            e = s  # start inner loop
            while e < f: # inner loop till the end date is hit
                e += delta #increment inner loop
                end_key = e.strftime('%m-%d-%Y')
                date_range = start_key + ' - ' + end_key
                print 'and end date ' + end_key
                if not date_range in date_array:
                    date_array[date_range] = {}
                this_lead_done_for_range = False
        
                for stage in stage_field_map:
                    start_date_field_qry = 'leads__hspt__properties__' + date_field_map[stage] + '__gte'
                    end_date_field_qry = 'leads__hspt__properties__' + date_field_map[stage] + '__lte'
                    #start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
                    #end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
                    stage_field_qry = 'leads__hspt__properties__lifecyclestage'
                    company_field_qry = 'company_id'
                    system_field_qry = 'leads__hspt__exists'
 
                    querydict = {system_field_qry: True, company_field_qry: company_id,start_date_field_qry : s, end_date_field_qry : e, stage_field_qry : stage_field_map[stage]} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date, 
                    #print 'query dict is ' + str(querydict)
                    leads = Lead.objects(**querydict) # now we have all leads in the given stage
                    #print ' found leads: ' + str(len(leads))
                    for lead in leads: # iterate over each lead
                        lead_props = lead['leads']['hspt']['properties']
                        #handle average days in current stage 
                        if date_field_map[stage] not in lead['leads']['hspt']['properties']:
                            raise ValueError("This is not possible")
                        started_this_stage_date = lead_props[date_field_map[stage]]
                        days_in_this_stage = (utc_current_date - started_this_stage_date).total_seconds() #remove conversion to seconds if you want dates; use .days then - no ()
                        average_days_in_this_stage_list[stage] += days_in_this_stage
                        
                        #handle transition days
                        if stage == "Customers":
                            stage_date1 = lead_props.get('hs_lifecyclestage_opportunity_date')
                            if stage_date1 is not None and started_this_stage_date is not None:
                                transitions_days["Customers"]["O->C"] += (started_this_stage_date - stage_date1).total_seconds() # change for number of days
                                transitions_days["all"]["O->C"] += (started_this_stage_date - stage_date1).total_seconds()
                                transitions_leads["Customers"]["O->C"] += 1
                                transitions_leads["all"]["O->C"] += 1
                                
                                if "O->C" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["O->C"] = []
                                transitions_ids["Customers"]["O->C"].append(lead['hspt_id'])
                                if "O->C" not in transitions_ids["all"]:
                                    transitions_ids["all"]["O->C"] = []
                                transitions_ids["all"]["O->C"].append(lead['hspt_id'])
                            
                            stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                            if stage_date2 is not None and stage_date1 is not None:
                                transitions_days["Customers"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                                transitions_days["all"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                                transitions_leads["Customers"]["S->O"] +=1
                                transitions_leads["all"]["S->O"] +=1
                                
                                if "S->O" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["S->O"] = []
                                transitions_ids["Customers"]["S->O"].append(lead['hspt_id'])
                                if "S->O" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->O"] = []
                                transitions_ids["all"]["S->O"].append(lead['hspt_id'])
                            
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None and stage_date2 is not None:
                                transitions_days["Customers"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_leads["Customers"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["M->S"] = []
                                transitions_ids["Customers"]["M->S"].append(lead['hspt_id'])
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead['hspt_id'])
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["Customers"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["Customers"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["L->M"] = []
                                transitions_ids["Customers"]["L->M"].append(lead['hspt_id'])
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead['hspt_id'])
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["Customers"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["Customers"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["S->L"] = []
                                transitions_ids["Customers"]["S->L"].append(lead['hspt_id'])
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead['hspt_id'])
                        
                        elif stage == "Opportunities":
                            stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                            if stage_date2 is not None  and started_this_stage_date is not None:
                                transitions_days["Opportunities"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                                transitions_days["all"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                                transitions_leads["Opportunities"]["S->O"] +=1
                                transitions_leads["all"]["S->O"] +=1
                                
                                if "S->O" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["S->O"] = []
                                transitions_ids["Opportunities"]["S->O"].append(lead['hspt_id'])
                                if "S->O" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->O"] = []
                                transitions_ids["all"]["S->O"].append(lead['hspt_id'])
                            
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None and stage_date2 is not None:
                                transitions_days["Opportunities"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_leads["Opportunities"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["M->S"] = []
                                transitions_ids["Opportunities"]["M->S"].append(lead['hspt_id'])
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead['hspt_id'])
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["Opportunities"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["Opportunities"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["L->M"] = []
                                transitions_ids["Opportunities"]["L->M"].append(lead['hspt_id'])
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead['hspt_id'])
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["Opportunities"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["Opportunities"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["S->L"] = []
                                transitions_ids["Opportunities"]["S->L"].append(lead['hspt_id'])
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead['hspt_id'])
                            
                        elif stage == "SQLs":
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None  and started_this_stage_date is not None:
                                transitions_days["SQLs"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                                transitions_leads["SQLs"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["M->S"] = []
                                transitions_ids["SQLs"]["M->S"].append(lead['hspt_id'])
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead['hspt_id'])
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["SQLs"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["SQLs"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["L->M"] = []
                                transitions_ids["SQLs"]["L->M"].append(lead['hspt_id'])
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead['hspt_id'])
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["SQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["SQLs"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["S->L"] = []
                                transitions_ids["SQLs"]["S->L"].append(lead['hspt_id'])
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead['hspt_id'])
                            
                        elif stage == "MQLs":
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None  and started_this_stage_date is not None:
                                transitions_days["MQLs"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                                transitions_leads["MQLs"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["MQLs"]:
                                    transitions_ids["MQLs"]["L->M"] = []
                                transitions_ids["MQLs"]["L->M"].append(lead['hspt_id'])
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead['hspt_id'])
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["MQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["MQLs"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["MQLs"]:
                                    transitions_ids["MQLs"]["S->L"] = []
                                transitions_ids["MQLs"]["S->L"].append(lead['hspt_id'])
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead['hspt_id'])
                            
                        elif stage == "Leads":
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and started_this_stage_date is not None: 
                                transitions_days["Leads"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                                transitions_leads["Leads"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Leads"]:
                                    transitions_ids["Leads"]["S->L"] = []
                                transitions_ids["Leads"]["S->L"].append(lead['hspt_id'])
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead['hspt_id'])
                    
                        #now that we have gone through all leads in this stage, calculate the average days in the current stage
                        if len(leads) > 0:
                            average_days_in_this_stage_list[stage] = average_days_in_this_stage_list[stage] / len(leads)
            
                
                queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_range_query: date_range}
                analyticsData = AnalyticsData.objects(**queryDict).first()
                if analyticsData is None:
                    analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date_range = date_range
                analyticsData.results = {}
                print '1st new save'
                analyticsData.save() 
                
                analyticsIds = AnalyticsIds.objects(**queryDict).first()
                if analyticsIds is None:
                    analyticsIds = AnalyticsIds()
                analyticsIds.system_type = 'MA'
                analyticsIds.company_id = company_id  
                analyticsIds.chart_name = chart_name
                analyticsIds.date_range = date_range
                analyticsIds.results = {}   
                print '2nd new save'
                analyticsIds.save() 
                        
                #now calculate the average number of days for each transition
                for stage in stage_field_map:
                    analyticsIds.results[stage] = {}
                    if stage == "Subscribers":
                        total_days = [{'x': 0, 'y': 0}] #
                    else:
                        total_days = []
                    for entry in  transitions_leads[stage]:
                        if transitions_leads[stage][entry] > 0:
                            transitions_days[stage][entry] = transitions_days[stage][entry] / transitions_leads[stage][entry]
                            if entry not in analyticsIds.results[stage]:
                                analyticsIds.results[stage][entry] = []
                            analyticsIds.results[stage][entry] = transitions_ids[stage][entry]
                        total_days.append({'x' : transition_label_map[entry], 'y' : transitions_days[stage][entry]})

                    analyticsData.results[stage] = total_days
                    
                    
                total_days = []
                analyticsIds.results["all"] = {}
                for entry in transitions_leads["all"]:
                        if transitions_leads["all"][entry] > 0:
                            transitions_days["all"][entry] = transitions_days["all"][entry] / transitions_leads["all"][entry]
                            analyticsIds.results["all"][entry] = transitions_ids["all"][entry]
                        total_days.append({'x' : transition_label_map[entry], 'y' : transitions_days["all"][entry]})
                analyticsData.results["All"] = total_days
                
                #result.append({'key' : "All", 'values': total_days, 'color' : '#004358'})
                average_days = []
                for stage in stage_field_map:
                    average_days.append({'x' : stage_label_map[stage], 'y' : average_days_in_this_stage_list[stage]}) #, 'shape': 'square'
   
                #result_set2['key'] = 'Days in current status'
                #result_set2['values'] = average_days
                #result_set2['area'] = True
                #result_set2['color'] = '#bedb39'
                
                analyticsData.results['Days in current status'] = average_days
                #result.append(result_set2)
                print 'range2 is ' + date_range
                AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
                #analyticsIds.save()
        #return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    

# chart- Source Distribution Pie
def hspt_contacts_sources_pie(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-1)
        else:
            start_date = start_date
            #start_date = datetime.utcnow() + timedelta(-60)
            
        print 'in there'
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        #local_start_date_str = _str_from_date(local_end_date, 'short')
        #local_end_date_str = _str_from_date(local_end_date, 'short')
        
        delta = timedelta(days=1)
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
            
        delta = timedelta(days=1)
        e = local_end_date
        
        
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            f = s + timedelta(days=1)
            f_date = f.strftime('%Y-%m-%d')
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
            
            #below code to be uncommented if IDs to be stored in AnalyticsIds
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
#             if analyticsIds is None:
#                 analyticsIds = AnalyticsIds()
#             analyticsIds.system_type = 'MA'
#             analyticsIds.company_id = company_id  
#             analyticsIds.chart_name = chart_name
#             analyticsIds.date = date
#             analyticsIds.results = {}
#             analyticsIds.save()
            
            querydict = {company_query: company_id, start_date_field_qry : date, end_date_field_qry: f_date}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            sources = Lead.objects(**querydict).item_frequencies('source_source')
            #print 'time 2 is ' + str(time.time())
            #print 'date is ' + date + ' found leads' + str(sources)
            #source_field_qry = 'leads__hspt__properties__hs_analytics_source'
            source_distr = {}
            for source in sources.keys():
                #querydict = {source_field_qry: source, company_query: company_id, start_date_field_qry : s, end_date_field_qry: f}
                encoded_source = encodeKey(source)
                source_distr[encoded_source] = sources[source]
                #below code to be uncommented if IDs to be stored in AnalyticsIds
#                 if source not in analyticsIds.results:
#                     analyticsIds.results[source] = []
#                     leads = Lead.objects(**querydict).only('hspt_id').all()
#                     for lead in leads:
#                         analyticsIds.results[source].append(lead['hspt_id'])
             
            #print 'time 3 is ' + str(time.time())
            for key in source_distr.keys():
                analyticsData.results[key] = source_distr[key]
                
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            #AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# chart- Revenue Source Distribution Pie
def hspt_contacts_revenue_sources_pie(user_id, company_id, chart_name, mode, start_date):
    print 'starting hspt revenue source pie task'
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-60)
            start_date = start_date
            
        print 'in there'
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        #local_start_date_str = _str_from_date(local_end_date, 'short')
        #local_end_date_str = _str_from_date(local_end_date, 'short')
        
        delta = timedelta(days=1)
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
        hspt_opps_field_qry = 'opportunities__hspt__ne'
        opp_created_date_qry = 'opportunities__sfdc__CreatedDate__lte'
            
        delta = timedelta(days=1)
        e = local_end_date
        
        opps = {}
        ids = {}
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            f = s + timedelta(days=1)
            f_date = f.strftime('%Y-%m-%d')
            start_date_string = _str_from_date(s)
#             print 'date is ' + str(date)
#             print 's is ' + str(s)
            print 'start date string is ' + start_date_string
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
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
            
            querydict = {company_query: company_id, hspt_opps_field_qry: None}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            leads = Lead.objects(**querydict).only('source_source').only('opportunities.hspt').only('hspt_id')
            # we have the leads with the opportunity data
            if len(leads) == 0:
                print 'no leads found'
                continue # got to next date if no valid leads for this date

            opps[date] = {}
            ids[date] = {}
            closedwon_status = 'closedwon' #need to make this configurable at company level since it can be changed in Hspt
            
            for lead in leads:
                print 'lead id is ' + lead['hspt_id']
                source = lead['source_source']
                if not 'hspt' in lead['opportunities']:
                    continue
                lead_opps = lead['opportunities']['hspt']
                for opp in lead_opps:
                    print 'starting opp ' + str(opp['dealId']) 
#                     if opp['CreatedDate'][:10] > date: # if this opp is created after today's date, go to next opp
#                         continue
                    properties = opp['properties']
                    if 'amount' in properties: #amount may be missing in Deal data
                        if properties['amount']['value'] is None: # don't consider opportunities with a null value
                            properties['amount']['value'] = 0
                    else:
                        properties['amount'] = {}
                        properties['amount']['value'] = 0
                    print 'beyond c with opp ' + str(opp['dealId'] )
                    opp_close_date = properties['closedate']['value']
                    opp_close_date = datetime.fromtimestamp(float(opp_close_date) / 1000)
                    local_opp_close_date = get_current_timezone().localize(opp_close_date, is_dst=None)
                    local_opp_close_date_string = _str_from_date(local_opp_close_date, 'short')
                    if properties['dealstage']['value'] != closedwon_status or (properties['dealstage']['value'] == closedwon_status and date < local_opp_close_date_string): #open  opportunity created on or before this date OR closed opportunity but still open on this date
                        if date not in opps: # no other opp yet for this date
                            print 'in 1/1 with ' + str(opp['dealId'] )
                            opps[date] = {}
                            opps[date][source] = {}
                            opps[date][source]['open'] = float(properties['amount']['value'])
                            opps[date][source]['closed'] = 0
                            
                            ids[date] = {}
                            ids[date][source] = {}
                            ids[date][source]['open'] = []
                            ids[date][source]['closed'] = []
                            ids[date][source]['open'].append(lead['hspt_id'])
                        else: #atleast one more opp for this date already exists
                            print 'in 2/1 with ' + str(opp['dealId'] )
                            if source not in opps[date]:
                                opps[date][source] = {}
                                opps[date][source]['open'] = float(properties['amount']['value'])
                                opps[date][source]['closed'] = 0
                        
                                ids[date][source] = {}
                                ids[date][source]['open'] = []
                                ids[date][source]['closed'] = []
                                ids[date][source]['open'].append(lead['hspt_id'])
                            else: #source already exists
                                opps[date][source]['open'] += float(properties['amount']['value'])
                                ids[date][source]['open'].append(lead['hspt_id'])
                            
                    elif properties['dealstage']['value'] == closedwon_status and date == local_opp_close_date_string: # opp is closed on this date
                        if date not in opps: # no other opp yet for this date
                            print 'in 1/2 with ' + str(opp['dealId'] )
                            opps[date] = {}
                            opps[date][source] = {}
                            opps[date][source]['open'] = 0
                            opps[date][source]['closed'] =float(properties['amount']['value'])
                            
                            ids[date] = {}
                            ids[date][source] = {}
                            ids[date][source]['closed'] = []
                            ids[date][source]['open'] = []
                            ids[date][source]['closed'].append(lead['hspt_id'])
                        else: #atleast one more opp for this date already exists
                            print 'in 2/2 with ' + str(opp['dealId'] )
                            if source not in opps[date]:
                                opps[date][source] = {}
                                opps[date][source]['open'] = 0
                                opps[date][source]['closed'] = float(properties['amount']['value'])
                                
                                ids[date][source] = {}
                                ids[date][source]['closed'] = []
                                ids[date][source]['open'] = []
                                ids[date][source]['closed'].append(lead['hspt_id'])
                            else: #source already exists
                                opps[date][source]['closed'] += float(properties['amount']['value'])
                                ids[date][source]['closed'].append(lead['hspt_id'])
                                
            # we are done for this day so do calculations and save the record in DB
            analyticsData.results = {}
            analyticsIds.results = {}
            for entry in opps[date]: 
                encoded_key = encodeKey(entry)
                analyticsData.results[encoded_key] = {}
                analyticsData.results[encoded_key]['open'] = opps[date][entry]['open']
                analyticsData.results[encoded_key]['closed'] = opps[date][entry]['closed']
                
                analyticsIds.results[encoded_key] = {}
                analyticsIds.results[encoded_key]['open'] = ids[date][entry]['open']
                analyticsIds.results[encoded_key]['closed'] = ids[date][entry]['closed']
            print 'saving' 
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            print 'saved'
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    

def hspt_contacts_sources_pie_deprecated(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-30)
            start_date = start_date
            
        
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        delta = timedelta(days=1)
        
        
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
            
        delta = timedelta(days=1)
        e = local_end_date
        
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%m-%d-%Y')
            print 'date is ' + date
            f = s + timedelta(days=1)
            
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
                analyticsData.save()
            
            #below code to be uncommented if IDs to be stored in AnalyticsIds
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
#             if analyticsIds is None:
#                 analyticsIds = AnalyticsIds()
#             analyticsIds.system_type = 'MA'
#             analyticsIds.company_id = company_id  
#             analyticsIds.chart_name = chart_name
#             analyticsIds.date = date
#             analyticsIds.results = {}
#             analyticsIds.save()
            
            querydict = {analytics_field_qry: True, company_query: company_id, start_date_field_qry : s, end_date_field_qry: f}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            sources = Lead.objects(**querydict).item_frequencies('leads.hspt.properties.hs_analytics_source')
            #print 'time 2 is ' + str(time.time())
            #print 'date is ' + date + ' found leads' + str(sources)
            source_field_qry = 'leads__hspt__properties__hs_analytics_source'
            source_distr = {}
            for source in sources.keys():
                querydict = {source_field_qry: source, company_query: company_id, start_date_field_qry : s, end_date_field_qry: f}
                source_distr[source] = sources[source]
                #below code to be uncommented if IDs to be stored in AnalyticsIds
#                 if source not in analyticsIds.results:
#                     analyticsIds.results[source] = []
#                     leads = Lead.objects(**querydict).only('hspt_id').all()
#                     for lead in leads:
#                         analyticsIds.results[source].append(lead['hspt_id'])
             
            #print 'time 3 is ' + str(time.time())
            for key in source_distr.keys():
                analyticsData.results[key] = source_distr[key]
                
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            #AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
    
def hspt_contacts_revenue_sources_pie_deprecated_2(user_id, company_id, chart_name, mode, start_date):
    
    try:
        if mode == 'delta':
            #start_date = datetime.utcnow() + timedelta(-1)
            start_date = start_date
        else:
            #start_date = datetime.utcnow() + timedelta(-30)
            start_date = start_date
        
        end_date = datetime.utcnow()
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        delta = timedelta(days=1)
        
        
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        revenue_field_qry = 'leads__hspt__properties__total_revenue__exists'
        
        delta = timedelta(days=1)
        e = local_end_date
        
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%m-%d-%Y')
            print 'date is ' + date
            f = s + timedelta(days=1)
            
            system_type_query = 'system_type'
            company_query = 'company_id'
            chart_name_query = 'chart_name'
            date_qry = 'date'
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None:
                analyticsData = AnalyticsData()
                analyticsData.system_type = 'MA'
                analyticsData.company_id = company_id  
                analyticsData.chart_name = chart_name
                analyticsData.date = date
                analyticsData.results = {}
            
            #below code to be uncommented if IDs to be stored in AnalyticsIds
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
#             if analyticsIds is None:
#                 analyticsIds = AnalyticsIds()
#             analyticsIds.system_type = 'MA'
#             analyticsIds.company_id = company_id  
#             analyticsIds.chart_name = chart_name
#             analyticsIds.date = date
#             analyticsIds.results = {}
            
            querydict = {revenue_field_qry: True, company_field_qry: company_id, start_date_field_qry : s, end_date_field_qry: f}
            leads = Lead.objects(**querydict)
            source_distr = {}
            
            for lead in leads:
                source = lead['leads']['hspt']['properties']['hs_analytics_source']
                revenue = lead['leads']['hspt']['properties']['total_revenue']
                if source in source_distr:
                    source_distr[source] += revenue
                else:
                    source_distr[source] = revenue
                
            for key in source_distr.keys():
                print 'key is ' + str(key)
                analyticsData['results'][key] = source_distr[key]
            
            analyticsData.save()
            #analyticsIds.save()
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
 

def hspt_multichannel_leads(user_id, company_id, chart_name, mode, start_date):
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
        time1 = str(time.time())
    
        delta = timedelta(days=1)
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        #analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        system_type_query = 'system_type'
        company_query = 'company_id'
        chart_name_query = 'chart_name'
        date_qry = 'date'
        
        source1_qry = 'leads__hspt__properties__hs_analytics_source_data_1'
        first_visit_date_gte_qry = 'leads__hspt__properties__hs_analytics_first_visit_timestamp__gte'
        first_visit_date_lt_qry = 'leads__hspt__properties__hs_analytics_first_visit_timestamp__lt'
         
        repeat_url_qry = 'leads__hspt__versions__hs_analytics_last_referrer__value__icontains'   
        repeat_visit_date_gte_qry = 'leads__hspt__versions__hs_analytics_last_referrer__timestamp__gte'
        repeat_visit_date_lte_qry = 'leads__hspt__properties__hs_analytics_last_referrer__timestamp__lte'
        
        delta = timedelta(days=1)
        e = local_end_date
        
        opps = {}
        ids = {}
        
        #get all the distinct sources
        subsources = {}
        collection = Lead._get_collection()
        #sources = collection.find({'company_id':int(company_id)}).distinct('source_source').hint({'company_id': 1, 'source_source': 1})
        sources = ['OFFLINE', 'DIRECT_TRAFFIC', 'REFERRALS', 'ORGANIC_SEARCH', 'OTHER_CAMPAIGNS', 'SOCIAL_MEDIA', 'PAID_SEARCH', 'EMAIL_MARKETING', 'None']
        for source in sources:
            print 'source is ' + str(source)
            subsources[source] = list(collection.find({'company_id':int(company_id), 'source_source': source}).distinct('leads.hspt.properties.hs_analytics_source_data_1'))
        print 'got subsources ' + str(subsources)
        url_map = SuperUrlMapping.objects()[0]['mappings']
        print 'got mappings ' + str(url_map)
        #return
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            #utc_day_start = datetime(s.year, s.month, s.day, tzinfo=tz.tzutc())
            #utc_day_end = utc_day_start + timedelta(1) #watch out - this is the start of the next day in UTC so search for < not <=
            utc_day_start = s.astimezone(pytz.timezone('UTC'))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            print 'utc day start is ' + str(utc_day_start)
            print 'utc day end is ' + str(utc_day_end)
            utc_day_start_epoch = time.mktime(utc_day_start.timetuple()) * 1000
            utc_day_end_epoch = time.mktime(utc_day_end.timetuple()) * 1000
            #print 'start epoch ' + str(utc_day_start_epoch)
            #print 'end epoch ' + str(utc_day_end_epoch)
            
            f = s + timedelta(days=1)
            #f_date = f.strftime('%Y-%m-%d')
            #start_date_string = _str_from_date(s)
            collection = Lead._get_collection()
            
#             print 's is ' + str(s)
            #print 'start date string is ' + start_date_string
            
            queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
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
            
            results_data = {}
            results_ids = {}
            #find all  leads who visited today from each subsource
            new_leads_by_subsource = {}
            old_leads_by_subsource = {}
            for i in range(len(sources)):
                print 'starting source ' + sources[i]
                source_count = 0
                results_data[sources[i]] = {}
                results_ids[sources[i]] = {}
                for subsource in subsources[sources[i]]:
                    #print 'starting subsource '
                    original_subsource = subsource
                    subsource = subsource.replace('.', '~')
                    results_data[sources[i]][subsource] = {}
                    results_ids[sources[i]][subsource] = {}
                    
                    #query for new leads
                    #querydict = {company_query: company_id, source1_qry: subsource, first_visit_date_gte_qry: utc_day_start, first_visit_date_lt_qry: utc_day_end}
                    #new_leads_by_subsource[subsource] = Lead.objects(**querydict).only('hspt_id').only('leads__hspt__properties__hs_analytics_source_data_1').only('leads__hspt__properties__hs_analytics_source_data_2').only('leads__hspt__properties__lifecyclestage').only('leads__hspt__versions__lifecyclestage')
                    new_leads_by_subsource[subsource] = collection.find({'company_id': int(company_id), 'source_source' : sources[i], 'leads.hspt.properties.hs_analytics_source_data_1' : original_subsource, 'leads.hspt.properties.hs_analytics_first_visit_timestamp' : {'$gte' : utc_day_start, '$lt' : utc_day_end}}, projection={'hspt_id': True, 'source_source': True, 'leads.hspt.properties.hs_analytics_source_data_1': True, 'leads.hspt.properties.hs_analytics_first_visit_timestamp':True, 'leads.hspt.properties.lifecyclestage': True, 'leads.hspt.versions.lifecyclestage': True})     
                    #print 'found new leads' 
                    subsource_new_count = new_leads_by_subsource[subsource].count()
                    #source_count += subsource_new_count
                    results_data[sources[i]][subsource]['New'] = {}
                    results_data[sources[i]][subsource]['New']['Visits'] = subsource_new_count
                    results_ids[sources[i]][subsource]['New'] = {}
                    
                    for lead in list(new_leads_by_subsource[subsource]):
                        #print 'new lead id is ' + str(lead['hspt_id']) 
                        #first, find the stage of the contact as of the day of the visit
                        lead_stage = ''
                        lead_stages = lead['leads']['hspt']['versions']['lifecyclestage']
                        if len(lead_stages) <= 1: #there's less than two status changes so stage as of visit is the same as current stage
                            lead_stage = lead['leads']['hspt']['properties']['lifecyclestage']
                        else:
                            #sorted_lead_stages = sorted(lead_stages, key=itemgetter('timestamp'), reverse=True)   
                            #we now have the stages sorted in descending order of time
                            filtered_lead_stages = list(l for l in lead_stages if l['timestamp'] < utc_day_end_epoch)
                            if len(filtered_lead_stages) > 0:
                                entry = max(filtered_lead_stages, key=lambda x:x['timestamp'])
                                if 'value' in entry:
                                    lead_stage = entry['value']
                                else:
                                    lead_stage = 'Unknown'
                            else:
                                    lead_stage = 'Unknown'
                                    
                        #print 'lead stage is ' + lead_stage   
                            
                        if lead_stage not in results_data[sources[i]][subsource]['New']:
                            results_data[sources[i]][subsource]['New'][lead_stage] = {}
                        if lead_stage not in results_ids[sources[i]][subsource]['New']:
                            results_ids[sources[i]][subsource]['New'][lead_stage] = {}
                        
                        if 'hs_analytics_source_data_2'  in lead['leads']['hspt']['properties']:
                            source_data_2 = lead['leads']['hspt']['properties']['hs_analytics_source_data_2']
                            source_data_2 = source_data_2.replace('.', '~')
                            if source_data_2 not in results_data[sources[i]][subsource]['New'][lead_stage]:
                                results_data[sources[i]][subsource]['New'][lead_stage][source_data_2] = 0
                            if source_data_2 not in results_ids[sources[i]][subsource]['New'][lead_stage]:
                                results_ids[sources[i]][subsource]['New'][lead_stage][source_data_2] = []
                            results_data[sources[i]][subsource]['New'][lead_stage][source_data_2] +=1 
                            results_ids[sources[i]][subsource]['New'][lead_stage][source_data_2].append(lead['hspt_id'])
                        else:
                            if 'Unassigned' not in results_data[sources[i]][subsource]['New'][lead_stage]:
                                results_data[sources[i]][subsource]['New'][lead_stage]['Unassigned'] = 0
                            if 'Unassigned' not in results_ids[sources[i]][subsource]['New'][lead_stage]:
                                results_ids[sources[i]][subsource]['New'][lead_stage]['Unassigned'] = []
                            results_data[sources[i]][subsource]['New'][lead_stage]['Unassigned'] +=1 
                            results_ids[sources[i]][subsource]['New'][lead_stage]['Unassigned'].append(lead['hspt_id'])
                            
                    ##find all existing leads who visited today from each subsource
                    #querydict = {company_query: company_id, repeat_visit_date_gte_qry: utc_day_start_epoch, repeat_visit_date_lte_qry: utc_day_end_epoch}    
                    search_url = None
                    if sources[i] == 'REFERRALS':
                        search_url = original_subsource
                    elif sources[i] == 'SOCIAL_MEDIA':
                        search_url = url_map.get(original_subsource, None)
                    
                    if search_url is not None:
                        original_search_url = search_url
                        search_url = '.*' + search_url + '.*'
                        ##old_leads_by_subsource[subsource] = Lead.objects(**querydict).only('hspt_id').only('leads__hspt__properties__hs_analytics_source_data_1').only('leads__hspt__properties__hs_analytics_source_data_2').only('leads__hspt__properties__lifecyclestage').only('leads__hspt__versions__hs_analytics_last_referrer')
                        #old_leads_by_subsource[subsource] = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__hs_analytics_first_visit_timestamp__lt=utc_day_start) & Q(leads__hspt__versions__hs_analytics_last_referrer__match={'value':{'$regex' : search_url}, 'timestamp': {'$gte': utc_day_start_epoch, '$lte': utc_day_end_epoch }})).only('hspt_id').only('leads__hspt__properties__hs_analytics_source_data_1').only('leads__hspt__properties__hs_analytics_source_data_2').only('leads__hspt__properties__lifecyclestage').only('leads__hspt__versions__hs_analytics_last_referrer')
                        
                        if subsource == 'Facebook':
                            print 'day start is ' + str(utc_day_start) + ' and tmiestamps are ' + str(utc_day_start_epoch) + ' and ' + str(utc_day_end_epoch) + ' for search ' + str(search_url)
                        old_leads_by_subsource[subsource] = collection.find({'company_id': int(company_id), 'source_source' : sources[i],  'leads.hspt.properties.hs_analytics_first_visit_timestamp' : {'$lt': utc_day_start}, 'leads.hspt.versions.hs_analytics_last_referrer': {'$elemMatch': {'value' : {'$regex': search_url}, 'timestamp': {'$gte': utc_day_start_epoch, '$lte': utc_day_end_epoch }}}}, projection={'hspt_id': True, 'source_source': True, 'leads.hspt.properties.hs_analytics_source_data_1': True, 'leads.hspt.properties.hs_analytics_first_visit_timestamp':True, 'leads.hspt.properties.lifecyclestage': True, 'leads.hspt.versions.lifecyclestage': True, 'leads.hspt.versions.hs_analytics_last_referrer': True})
                        #print 'found old leads'
                        #if sources[i] == 'SOCIAL_MEDIA':
                            #print '#old leads found for subsource ' + subsource + ' ' + str(old_leads_by_subsource[subsource].count())      
                        
                        subsource_old_count = old_leads_by_subsource[subsource].count()
                        if subsource_old_count == 0:
                            continue
                        #source_count += subsource_old_count
                        results_data[sources[i]][subsource]['Repeat'] = {}
                        results_data[sources[i]][subsource]['Repeat']['Visits'] = subsource_old_count
                        results_ids[sources[i]][subsource]['Repeat'] = {}
                        
                        for lead in list(old_leads_by_subsource[subsource]):
                            #print 'old lead id is ' + str(lead['hspt_id'])
                            #first, find the stage of the contact as of the day of the visit
                            lead_stage = ''
                            lead_stages = lead['leads']['hspt']['versions']['lifecyclestage']
                            if len(lead_stages) <= 1: #there's less than two status changes so stage as of visit is the same as current stage
                                lead_stage = lead['leads']['hspt']['properties']['lifecyclestage']
                            else:
                                #sorted_lead_stages = sorted(lead_stages, key=itemgetter('timestamp'), reverse=True)   
                                #we now have the stages sorted in descending order of time
                                filtered_lead_stages = list(l for l in lead_stages if l['timestamp'] < utc_day_end_epoch)
                                if len(filtered_lead_stages) > 0:
                                    entry = max(filtered_lead_stages, key=lambda x:x['timestamp'])
                                    if 'value' in entry:
                                        lead_stage = entry['value']
                                    else:
                                        lead_stage = 'Unknown'
                                else:
                                        lead_stage = 'Unknown'
                                        
                            #print 'lead stage is ' + lead_stage   
                                
                            if lead_stage not in results_data[sources[i]][subsource]['Repeat']:
                                results_data[sources[i]][subsource]['Repeat'][lead_stage] = {}
                            if lead_stage not in results_ids[sources[i]][subsource]['Repeat']:
                                results_ids[sources[i]][subsource]['Repeat'][lead_stage] = {}
                            
                            #loop through the last referring pages to find the ones relevant for this day
                            utm_campaign_string = 'utm_campaign='
                            ampersand_char = '&'
                            visits = lead['leads']['hspt']['versions']['hs_analytics_last_referrer']
                            for visit in visits:
                                if not (visit['timestamp'] >= utc_day_start_epoch and visit['timestamp'] <= utc_day_end_epoch and original_search_url in visit['value']):
                                    continue # skip to the next visit record
                                #this visit record meets the conditions so process it
                                #find the campaign from the last referring page
                                if utm_campaign_string in visit['value']: #this is from a campaign referral
                                    #this gives us the string after utm_campaign=
                                    first_split = visit['value'].split(utm_campaign_string, 1)[1]
                                    #now split again on '&' to get the campaign name
                                    campaign_name = first_split.split(ampersand_char, 1)[0]
                                    campaign_name = urllib2.unquote(campaign_name)
                                    source_data_2 = campaign_name.replace('.', '~')
                                else:
                                    source_data_2 = 'Unassigned'
                                #print 'source data 2 is ' + source_data_2
                                #capture the original source of the lead
                                original_subsource = lead['leads']['hspt']['properties'].get('hs_analytics_source_data_1', None) 
                                original_subsource = original_subsource.replace('.', '~')
                                #print 'original source is ' + original_subsource
                                if source_data_2 not in results_data[sources[i]][subsource]['Repeat'][lead_stage]:
                                    results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2] = {}
                                #print 'skip 1'
                                if original_subsource not in results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2]:
                                    results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource] = {}
                                    results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource]['Total']= 0
                                    results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource]['Average # Touches'] = 0   
                                #print 'skip 2'
                                if source_data_2 not in results_ids[sources[i]][subsource]['Repeat'][lead_stage]:
                                    results_ids[sources[i]][subsource]['Repeat'][lead_stage][source_data_2] = {}
                                if original_subsource not in results_ids[sources[i]][subsource]['Repeat'][lead_stage][source_data_2]:
                                    results_ids[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource] = []
                                #print 'skip 3'
                                results_data[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource]['Total'] +=1 
                                results_ids[sources[i]][subsource]['Repeat'][lead_stage][source_data_2][original_subsource].append(lead['hspt_id'])
                                #print 'skip 4'
           
            # we are done for this day so do calculations and save the record in DB
            analyticsData.results = results_data
            #print 'skip 5'
            analyticsIds.results = results_ids
            print 'saving' 
            try:
                AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)
            except Exception as e:
                print 'exception while saving analytics data: ' + str(e)
                continue
            print 'saved'
        print 'start time was ' + time1 + ' and end time is ' + str(time.time())
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# hspt_social_roi

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
    
        # get the FB pages for this company
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
        fbokIntegration = existingIntegration.integrations['fbok']
        fbok_pages = fbokIntegration['pages']
        
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
            
            #get FB Paid data
            results['Social']['Facebook']['Paid'] = []
            sub_object = {} 
            querydict = {company_id_qry : company_id, source_created_date_qry: date}
            fbPaidList = FbAdInsight.objects(**querydict)
            print 'starting paid'
            for entry in fbPaidList:
                if entry['source_account_id'] not in sub_object:
                    sub_object[entry['source_account_id']] = {}
                truncated_entry = {}
                for metric in fb_paid_metrics: #read all prefedined metrics and copy
                    metric = metric.replace('.', '~')
                    if metric in entry['data']:
                        truncated_entry[metric] = entry['data'][metric]
                if 'actions' in entry['data']:
                    for list_entry in entry['data']['actions']: #special treatment for actions array
                        list_entry['action_type'] = list_entry['action_type'].replace('.', '~')
                        if list_entry['action_type'] not in truncated_entry:
                            truncated_entry[list_entry['action_type']] = 0
                        truncated_entry[list_entry['action_type']] = list_entry['value']
                            
                sub_object[entry['source_account_id']] = truncated_entry     
                results['Social']['Facebook']['Paid'].append(sub_object)    
            print 'finished paid'    
            
            #get FB Organic data
            results['Social']['Facebook']['Organic'] = []  
            #filter_date = s + timedelta(days=1)
            #filter_date_str = _str_from_date(filter_date)
            filter_date_str = date + 'T07:00:00+0000' #hack - needs to be changed
            print 'filter date is ' + filter_date_str
            sub_object = {} 
            for fbok_page in fbok_pages:
                if fbok_page['id'] not in sub_object:
                    sub_object[fbok_page['id']] = {}  
                truncated_entry = {}
                
                        
                for metric in fb_organic_metrics:
                    
                    querydict = {company_id_qry : company_id, source_metric_name_qry: metric, end_time_qry: filter_date_str, source_page_id_qry: fbok_page['id']}
                    fbOrganicList = FbPageInsight.objects(**querydict).first()
                    if fbOrganicList is None: # if no data found for metric, move to the next one
                        continue
                    for value in fbOrganicList['data']['values']:
                        if value['end_time'] == filter_date_str: 
                            valuex = value['value']
                            if isinstance(valuex, (int, long)): #if it is a single value
                                print 'valuex ' + str(valuex)
                                if metric not in truncated_entry:
                                    truncated_entry[metric] = 0   
                                truncated_entry[metric] += valuex
                            else: # if it is a list of values
                                for type_entry_key, type_entry_value in valuex.iteritems():
                                    type_entry_key = type_entry_key.replace('.', '~')
                                    if type_entry_key not in truncated_entry:
                                        truncated_entry[type_entry_key] = 0  
                                    truncated_entry[type_entry_key] += type_entry_value
                                    
                sub_object[fbok_page['id']] = truncated_entry     
                results['Social']['Facebook']['Organic'].append(sub_object)             
            print 'finished organic'
            
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
                    leads_created_source['Unknown'] = leads_created_stage.pop(key) 
                      
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
                
def _process_form_list(listx):
    
    results_data = copy.deepcopy(listx)
    results_ids = list(listx)
    
    for entry in results_data:
        entry = _process_country(entry)
        for form in entry['forms']:
            del form['ids'] 
            
    for entryx in results_ids:
        entry = _process_country(entryx)
        for formx in entryx['forms']:
            del formx['count'] 
        del entryx['count']
    
    
    return results_data, results_ids

def _process_country(entry):
    #normalize countries
    from mmm.countries import countries 
    country = entry['_id']
    if country is None: # if country is None, don't try to do much more with it
        entry['geo'] = 'others'
    else:
        super_country = SuperCountry.objects(alternatives=country.lower()).first()
        if super_country is not None:
            entry['geo'] = super_country['country']
        else:
            geolocator = GoogleV3(api_key='AIzaSyD-XCrxDCWe9uJlInVElOZluoFcFPssaQU')
            location = geolocator.geocode(country)
            if location is None: #if geopy couldn't find the country, add it to "Others"
                entry['geo'] = 'others'
            else:
                entry['geo'] = location.address.lower()
                super_country = SuperCountry.objects(country=location.address.lower()).first()
                if super_country is None:
                    super_country = SuperCountry(country=location.address.lower())
                    super_country['alternatives'] = []
                    super_country['alternatives'].append(country.lower())
                    super_country['lat'] = str(location.latitude)
                    super_country['long'] = str(location.longitude)
                    super_country['continent'] = 'unknown'
                    for countryx in countries:
                        if countryx['name'].lower() == location.address.lower():
                            super_country['continent'] = countryx['continent'].lower()
                    super_country.save()
                else:
                    super_country['alternatives'].append(country.lower())
                    super_country.save()
            
    return entry  

# Buffer Analytics       
# chart - "Twitter Performance"   
def bufr_tw_performance(user_id, company_id, chart_name, mode, start_date): 
    #print 'orig start' + str(start_date)
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
        local_end_date_str = _str_from_date(local_end_date, 'short')
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        company_field_qry = 'company_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        published_date_qry = 'published_date'
            
        
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        while s < (f - delta): # outer loop on the start date
            s += delta #increment the outer loop
            start_key = _str_from_date(s, 'short')
            #array_key = s.strftime('%Y-%m-%d')
            
            # look for tweets that were published on this date 
            querydict = {company_field_qry: company_id, published_date_qry: start_key} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            interactions = PublishedTweet.objects(**querydict).all()
            
            interactions_list = list(interactions)
            #if len(interactions_list) ==  0:
            #    continue
            
            #initialize the stats and IDs for this day
            interaction_types = {'Mentions', 'Reach', 'Retweets', 'Favorites', 'Clicks'}
            
            queryDict = {company_field_qry : company_id, system_type_qry: 'SO', chart_name_qry: chart_name, date_qry: start_key}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: 
                analyticsData = AnalyticsData()
                analyticsData.results = {}
                for interaction_type in interaction_types: #only initialize if no earlier record for this day
                    analyticsData.results[interaction_type] = 0 
            analyticsData.system_type = 'SO'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = start_key
            

            queryDict = {company_field_qry : company_id, system_type_qry: 'SO', chart_name_qry: chart_name, date_qry: start_key}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.results = {}
                for interaction_type in interaction_types: #only initialize if no earlier record for this day
                    analyticsIds.results[interaction_type] = [] 
            analyticsIds.system_type = 'SO'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = start_key
            
            analyticsData.save()
            analyticsIds.save()
            
            #update the stats and IDs for this day
            for interaction in interactions_list:
                interaction_id = interaction['interaction_id']
                stats = interaction['data']['statistics']
                for stat in stats.keys():
                    analyticsData.results[stat.capitalize()] += stats[stat]
                    analyticsIds.results[stat.capitalize()].append(interaction_id)
            
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    

            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 
    
# Google Analytics       
# chart - "Google Analytics"   
def google_analytics(user_id, company_id, chart_name, mode, start_date): 
    #print 'orig start' + str(start_date)
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
        local_end_date_str = _str_from_date(local_end_date, 'short')
    
        date_array = {}
        ids_array = {}
        delta = timedelta(days=1)
        
        company_field_qry = 'company_id'
        system_type_qry = 'system_type'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        source_created_date_qry = 'source_created_date'
        source_source_query = 'source_source'
            
        
        s = local_start_date - timedelta(days=1)
        f = local_end_date #absolute last date of range
        while s < (f - delta): # outer loop on the start date
            s += delta #increment the outer loop
            start_key = _str_from_date(s, 'short')
            #array_key = s.strftime('%Y-%m-%d')
            
            # look for interactions on this date 
            querydict = {company_field_qry: company_id, source_created_date_qry: start_key, source_source_query: 'goog'} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            traffic = Traffic.objects(**querydict).all()
            
            traffic_list = list(traffic)
            #if len(interactions_list) ==  0:
            #    continue
            
            #initialize the stats and IDs for this day
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            googIntegration = existingIntegration.integrations['goog']
            goog_accounts = googIntegration['accounts']
            if goog_accounts is None: 
                return
            visitor_types = {'New', 'Returning'}
            
            queryDict = {company_field_qry : company_id, system_type_qry: 'AD', chart_name_qry: chart_name, date_qry: start_key}
            analyticsData = AnalyticsData.objects(**queryDict).first()
            if analyticsData is None: 
                analyticsData = AnalyticsData()
                analyticsData.results = {}
                for goog_account in goog_accounts:
                    profile_id = goog_account['profile_id']
                    analyticsData.results[profile_id] = {}
                    for visitor_type in visitor_types: #only initialize if no earlier record for this day
                        analyticsData.results[profile_id][visitor_type] = 0 
            analyticsData.system_type = 'AD'
            analyticsData.company_id = company_id  
            analyticsData.chart_name = chart_name
            analyticsData.date = start_key
            

            queryDict = {company_field_qry : company_id, system_type_qry: 'AD', chart_name_qry: chart_name, date_qry: start_key}
            analyticsIds = AnalyticsIds.objects(**queryDict).first()
            if analyticsIds is None:
                analyticsIds = AnalyticsIds()
                analyticsIds.results = {}
                for goog_account in goog_accounts:
                    profile_id = goog_account['profile_id']
                    analyticsIds.results[profile_id] = {}
                    for visitor_type in visitor_types: #only initialize if no earlier record for this day
                        analyticsIds.results[profile_id][visitor_type] = []
            analyticsIds.system_type = 'AD'
            analyticsIds.company_id = company_id  
            analyticsIds.chart_name = chart_name
            analyticsIds.date = start_key
            
            analyticsData.save()
            analyticsIds.save()
            
            #update the stats and IDs for this day per each profile
            for traffic in traffic_list:
                data = traffic['data']
                profile_id = traffic['source_profile_id']
                if data['ga:userType'] == 'Returning Visitor':
                    analyticsData.results[profile_id]['Returning'] += int(data['ga:users'])
                    analyticsIds.results[profile_id]['Returning'].append(traffic.id)
                elif data['ga:userType'] == 'New Visitor':
                    analyticsData.results[profile_id]['New'] += int(data['ga:users'])
                    analyticsIds.results[profile_id]['New'].append(traffic.id)
            
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
            AnalyticsIds.objects(id=analyticsIds.id).update(results = analyticsIds.results)    

            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 
