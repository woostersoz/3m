from __future__ import absolute_import
from datetime import timedelta, date, datetime
import pytz
import os
import time
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
from social.models import PublishedTweet
from analytics.models import AnalyticsData, AnalyticsIds
from websites.models import Traffic

from django.utils.timezone import get_current_timezone

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
    method_map = { "sources_bar" : mkto_sources_bar_chart, "contacts_distr" : mkto_contacts_distr_chart, "source_pie" : mkto_contacts_sources_pie, "pipeline_duration" : mkto_contacts_pipeline_duration, "revenue_source_pie" : mkto_contacts_revenue_sources_pie}
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
    method_map = { "sources_bar" : hspt_sources_bar_chart, "contacts_distr" : hspt_contacts_distr_chart, "pipeline_duration" : hspt_contacts_pipeline_duration, "source_pie" : hspt_contacts_sources_pie, "revenue_source_pie" : hspt_contacts_revenue_sources_pie, "facebook_leads" : hspt_facebook_leads}
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
#                         analyticsIds.results[source].append(lead.hspt_id)
             
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
            firstDate = Lead.objects(**querydict).only('source_created_date').order_by('source_created_date').first()
            print 'date string is ' + str(firstDate['source_created_date'])
            start_date = firstDate['source_created_date']
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
        system_field_qry = 'leads__hspt__exists'
        
        querydict = {system_field_qry: True, company_field_qry: company_id, end_date_created_field_qry: local_end_date} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            
        existingLeads = Lead.objects(**querydict)
        #print ' count of leads ' + str(len(existingLeads))
        if existingLeads is None:
            return 
        delta = timedelta(days=1)
        e = local_end_date
        #date_field_map = { "subscriber" : 'hs_lifecyclestage_subscriber_date', "lead" : 'hs_lifecyclestage_lead_date', "marketingqualifiedlead" : 'hs_lifecyclestage_marketingqualifiedlead_date', "salesqualifiedlead" : 'hs_lifecyclestage_salesqualifiedlead_date', "opportunity" : 'hs_lifecyclestage_opportunity_date', "customer" : 'hs_lifecyclestage_customer_date' } 
        date_field_map = { "subscriber" : 'hspt_subscriber_date', "lead" : 'hspt_lead_date', "marketingqualifiedlead" : 'hspt_mql_date', "salesqualifiedlead" : 'hspt_sql_date', "opportunity" : 'hspt_opp_date', "customer" : 'hspt_customer_date' } 
        this_lead_done_for_day = False
        
        for lead in existingLeads:
            print 'lead id is ' + str(lead.hspt_id)
            s = local_start_date - timedelta(days=1)
            #properties = lead.leads['hspt']['properties']
            current_stage = lead.source_stage
            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
            current_stage_date = current_stage_date.astimezone(get_current_timezone())
            #print 'current stage date is ' + str(current_stage_date) + ' and stage is ' + current_stage
            while s < (e - delta):
                #print 's is ' + str(s) + ' and e is ' + str(e)
                s += delta #increment the day counter
                this_lead_done_for_day = False
                current_stage = lead.source_stage # needs to be repeated here since current_stage is changed in the steps below
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
                        customer_ids_temp_array[array_key].append(lead.hspt_id)
                        this_lead_done_for_day = True
                        continue  
                    if this_lead_done_for_day == False:
                        current_stage = 'opportunity'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in opp_values_temp_array:
                                    opp_values_temp_array[array_key] += 1
                                else:
                                    opp_values_temp_array[array_key] = 1
                                if not array_key in opp_ids_temp_array:
                                    opp_ids_temp_array[array_key] = []
                                opp_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                if not array_key in sql_ids_temp_array:
                                    sql_ids_temp_array[array_key] = []
                                sql_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'opportunity':
                    #current_stage = 'opportunity'
                    if date_field_map[current_stage] in lead:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in opp_values_temp_array:
                                opp_values_temp_array[array_key] += 1
                            else:
                                opp_values_temp_array[array_key] = 1
                            if not array_key in opp_ids_temp_array:
                                opp_ids_temp_array[array_key] = []
                            opp_ids_temp_array[array_key].append(lead.hspt_id)
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                if not array_key in sql_ids_temp_array:
                                    sql_ids_temp_array[array_key] = []
                                sql_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'salesqualifiedlead':
                    #current_stage = 'salesqualifiedlead'
                    if date_field_map[current_stage] in lead:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in sql_values_temp_array:
                                sql_values_temp_array[array_key] += 1
                            else:
                                sql_values_temp_array[array_key] = 1
                            if not array_key in sql_ids_temp_array:
                                sql_ids_temp_array[array_key] = []
                            sql_ids_temp_array[array_key].append(lead.hspt_id)
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                if not array_key in mql_ids_temp_array:
                                    mql_ids_temp_array[array_key] = []
                                mql_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'marketingqualifiedlead':
                    if date_field_map[current_stage] in lead:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in mql_values_temp_array:
                                mql_values_temp_array[array_key] += 1
                            else:
                                mql_values_temp_array[array_key] = 1
                            if not array_key in mql_ids_temp_array:
                                mql_ids_temp_array[array_key] = []
                            mql_ids_temp_array[array_key].append(lead.hspt_id)
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                if not array_key in lead_ids_temp_array:
                                    lead_ids_temp_array[array_key] = []
                                lead_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'lead':
                    if date_field_map[current_stage] in lead:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in lead_values_temp_array:
                                lead_values_temp_array[array_key] += 1
                            else:
                                lead_values_temp_array[array_key] = 1
                            if not array_key in lead_ids_temp_array:
                                lead_ids_temp_array[array_key] = []
                            lead_ids_temp_array[array_key].append(lead.hspt_id)
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in lead:
                            current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                if not array_key in subscriber_ids_temp_array:
                                    subscriber_ids_temp_array[array_key] = []
                                subscriber_ids_temp_array[array_key].append(lead.hspt_id)
                                this_lead_done_for_day = True 
                                continue
                                    
                elif current_stage == 'subscriber':
                    if date_field_map[current_stage] in lead:
                        current_stage_date = pytz.utc.localize(lead[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in subscriber_values_temp_array:
                                subscriber_values_temp_array[array_key] += 1
                            else:
                                subscriber_values_temp_array[array_key] = 1
                            if not array_key in subscriber_ids_temp_array:
                                subscriber_ids_temp_array[array_key] = []
                            subscriber_ids_temp_array[array_key].append(lead.hspt_id)
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
                            ids_array[range]['Customers'].append(lead.hspt_id)  
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
                            ids_array[range]['Opportunities'].append(lead.hspt_id)  
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
                            ids_array[range]['SQLs'].append(lead.hspt_id) 
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
                            ids_array[range]['MQLs'].append(lead.hspt_id) 
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
                            ids_array[range]['Leads'].append(lead.hspt_id) 
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
                            ids_array[range]['Subscribers'].append(lead.hspt_id) 
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
                                transitions_ids["Customers"]["O->C"].append(lead.hspt_id)
                                if "O->C" not in transitions_ids["all"]:
                                    transitions_ids["all"]["O->C"] = []
                                transitions_ids["all"]["O->C"].append(lead.hspt_id)
                            
                            stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                            if stage_date2 is not None and stage_date1 is not None:
                                transitions_days["Customers"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                                transitions_days["all"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                                transitions_leads["Customers"]["S->O"] +=1
                                transitions_leads["all"]["S->O"] +=1
                                
                                if "S->O" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["S->O"] = []
                                transitions_ids["Customers"]["S->O"].append(lead.hspt_id)
                                if "S->O" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->O"] = []
                                transitions_ids["all"]["S->O"].append(lead.hspt_id)
                            
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None and stage_date2 is not None:
                                transitions_days["Customers"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_leads["Customers"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["M->S"] = []
                                transitions_ids["Customers"]["M->S"].append(lead.hspt_id)
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead.hspt_id)
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["Customers"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["Customers"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["L->M"] = []
                                transitions_ids["Customers"]["L->M"].append(lead.hspt_id)
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead.hspt_id)
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["Customers"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["Customers"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Customers"]:
                                    transitions_ids["Customers"]["S->L"] = []
                                transitions_ids["Customers"]["S->L"].append(lead.hspt_id)
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead.hspt_id)
                        
                        elif stage == "Opportunities":
                            stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                            if stage_date2 is not None  and started_this_stage_date is not None:
                                transitions_days["Opportunities"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                                transitions_days["all"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                                transitions_leads["Opportunities"]["S->O"] +=1
                                transitions_leads["all"]["S->O"] +=1
                                
                                if "S->O" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["S->O"] = []
                                transitions_ids["Opportunities"]["S->O"].append(lead.hspt_id)
                                if "S->O" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->O"] = []
                                transitions_ids["all"]["S->O"].append(lead.hspt_id)
                            
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None and stage_date2 is not None:
                                transitions_days["Opportunities"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                                transitions_leads["Opportunities"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["M->S"] = []
                                transitions_ids["Opportunities"]["M->S"].append(lead.hspt_id)
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead.hspt_id)
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["Opportunities"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["Opportunities"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["L->M"] = []
                                transitions_ids["Opportunities"]["L->M"].append(lead.hspt_id)
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead.hspt_id)
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["Opportunities"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["Opportunities"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Opportunities"]:
                                    transitions_ids["Opportunities"]["S->L"] = []
                                transitions_ids["Opportunities"]["S->L"].append(lead.hspt_id)
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead.hspt_id)
                            
                        elif stage == "SQLs":
                            stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                            if stage_date3 is not None  and started_this_stage_date is not None:
                                transitions_days["SQLs"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                                transitions_days["all"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                                transitions_leads["SQLs"]["M->S"] +=1
                                transitions_leads["all"]["M->S"] +=1
                                
                                if "M->S" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["M->S"] = []
                                transitions_ids["SQLs"]["M->S"].append(lead.hspt_id)
                                if "M->S" not in transitions_ids["all"]:
                                    transitions_ids["all"]["M->S"] = []
                                transitions_ids["all"]["M->S"].append(lead.hspt_id)
                            
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None and stage_date3 is not None: 
                                transitions_days["SQLs"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                                transitions_leads["SQLs"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["L->M"] = []
                                transitions_ids["SQLs"]["L->M"].append(lead.hspt_id)
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead.hspt_id)
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["SQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["SQLs"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["SQLs"]:
                                    transitions_ids["SQLs"]["S->L"] = []
                                transitions_ids["SQLs"]["S->L"].append(lead.hspt_id)
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead.hspt_id)
                            
                        elif stage == "MQLs":
                            stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                            if stage_date4 is not None  and started_this_stage_date is not None:
                                transitions_days["MQLs"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                                transitions_days["all"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                                transitions_leads["MQLs"]["L->M"] +=1
                                transitions_leads["all"]["L->M"] +=1
                                
                                if "L->M" not in transitions_ids["MQLs"]:
                                    transitions_ids["MQLs"]["L->M"] = []
                                transitions_ids["MQLs"]["L->M"].append(lead.hspt_id)
                                if "L->M" not in transitions_ids["all"]:
                                    transitions_ids["all"]["L->M"] = []
                                transitions_ids["all"]["L->M"].append(lead.hspt_id)
                            
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and stage_date4 is not None: 
                                transitions_days["MQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                                transitions_leads["MQLs"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["MQLs"]:
                                    transitions_ids["MQLs"]["S->L"] = []
                                transitions_ids["MQLs"]["S->L"].append(lead.hspt_id)
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead.hspt_id)
                            
                        elif stage == "Leads":
                            stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                            if stage_date5 is not None and started_this_stage_date is not None: 
                                transitions_days["Leads"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                                transitions_days["all"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                                transitions_leads["Leads"]["S->L"] +=1
                                transitions_leads["all"]["S->L"] +=1
                                
                                if "S->L" not in transitions_ids["Leads"]:
                                    transitions_ids["Leads"]["S->L"] = []
                                transitions_ids["Leads"]["S->L"].append(lead.hspt_id)
                                if "S->L" not in transitions_ids["all"]:
                                    transitions_ids["all"]["S->L"] = []
                                transitions_ids["all"]["S->L"].append(lead.hspt_id)
                    
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
#                         analyticsIds.results[source].append(lead.hspt_id)
             
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
#                         analyticsIds.results[source].append(lead.hspt_id)
             
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
 

def hspt_facebook_leads(user_id, company_id, chart_name, mode, start_date):
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
        collection = Lead._get_collection()
        sources = list(collection.find({'company_id':int(company_id)}).distinct('leads.hspt.properties.hs_analytics_source'))
        subsources = {}
        for i in range(len(sources)):
            subsources[sources[i]] = list(collection.find({'company_id':int(company_id), 'leads.hspt.properties.hs_analytics_source': sources[i]}).distinct('leads.hspt.properties.hs_analytics_source_data_1'))
        print 'got subsources ' + str(subsources)
    
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + date
            utc_day_start = datetime(s.year, s.month, s.day, tzinfo=tz.tzutc())
            utc_day_end = utc_day_start + timedelta(1) #watch out - this is the start of the next day in UTC so search for < not <=
            
            utc_day_start_epoch = time.mktime(utc_day_start.timetuple()) * 1000
            utc_day_end_epoch = time.mktime(utc_day_end.timetuple()) * 1000
            #print 'start epoch ' + str(utc_day_start_epoch)
            #print 'end epoch ' + str(utc_day_end_epoch)
            
            f = s + timedelta(days=1)
            #f_date = f.strftime('%Y-%m-%d')
            #start_date_string = _str_from_date(s)
            print 'date is ' + str(date)
#             print 's is ' + str(s)
            #print 'start date string is ' + start_date_string
            
#             queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_qry: date}
#             analyticsData = AnalyticsData.objects(**queryDict).first()
#             if analyticsData is None:
#                 analyticsData = AnalyticsData()
#                 analyticsData.system_type = 'MA'
#                 analyticsData.company_id = company_id  
#                 analyticsData.chart_name = chart_name
#                 analyticsData.date = date
#                 analyticsData.results = {}
#                 analyticsData.save()
#                 
#             analyticsIds = AnalyticsIds.objects(**queryDict).first()
#             if analyticsIds is None:
#                 analyticsIds = AnalyticsIds()
#                 analyticsIds.system_type = 'MA'
#                 analyticsIds.company_id = company_id  
#                 analyticsIds.chart_name = chart_name
#                 analyticsIds.date = date
#                 analyticsIds.results = {}
#                 analyticsIds.save()
            
            results_data = {}
            results_ids = {}
            #find all new leads who visited today from each subsource
            new_leads_by_subsource = {}
            for i in range(len(sources)):
                source_count = 0
                results_data[sources[i]] = {}
                results_ids[sources[i]] = {}
                for subsource in subsources[sources[i]]:
                    results_data[sources[i]][subsource] = {}
                    results_ids[sources[i]][subsource] = {}
                    
                    #query for new leads
                    querydict = {company_query: company_id, source1_qry: subsource, first_visit_date_gte_qry: utc_day_start, first_visit_date_lt_qry: utc_day_end}
            #print 'time 1 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
                    new_leads_by_subsource[subsource] = Lead.objects(**querydict).only('hspt_id').only('leads__hspt__properties__hs_analytics_source_data_1').only('leads__hspt__properties__hs_analytics_source_data_2').only('leads__hspt__properties__lifecyclestage').only('leads__hspt__versions__lifecyclestage')
                    subsource_count = new_leads_by_subsource[subsource].count()
                    source_count += subsource_count
                    results_data[sources[i]][subsource]['New'] = {}
                    results_data[sources[i]][subsource]['New']['Visits'] = subsource_count
                    results_ids[sources[i]][subsource]['New'] = {}
                    #print 'goibg ubti sirce 2'
                    for lead in list(new_leads_by_subsource[subsource]):
                        print 'lead id is ' + str(lead['hspt_id']) + ' and day end is ' + str(utc_day_end_epoch)
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
                                    
                        print 'lead stage is ' + lead_stage   
                            
                        if lead_stage not in results_data[sources[i]][subsource]['New']:
                            results_data[sources[i]][subsource]['New'][lead_stage] = {}
                        if lead_stage not in results_ids[sources[i]][subsource]['New']:
                            results_ids[sources[i]][subsource]['New'][lead_stage] = {}
                        
                        if 'hs_analytics_source_data_2'  in lead['leads']['hspt']['properties']:
                            source_data_2 = lead['leads']['hspt']['properties']['hs_analytics_source_data_2']
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
                            
                          
                if sources[i] == 'SOCIAL_MEDIA':
                    print 'new leads on social media '+ str(results_data[sources[i]])
                    
            continue
        
            #find all existing leads who visited today from each subsource
            querydict = {company_query: company_id, repeat_url_qry: 'facebook.com', repeat_visit_date_gte_qry: utc_day_start_epoch, repeat_visit_date_lte_qry: utc_day_end_epoch}
            #print 'time 3 is ' + str(time.time())
            #leads = Lead.objects(**querydict).only('leads__hspt__properties__hs_analytics_source')
            old_leads_repeat_visit = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__hs_analytics_first_visit_timestamp__lt=utc_day_start) & Q(leads__hspt__versions__hs_analytics_last_referrer__match={'value':{'$regex' : '.*facebook.*'}, 'timestamp': {'$gte': utc_day_start_epoch, '$lte': utc_day_end_epoch }})).only('hspt_id')
            #print 'time 4 is ' + str(time.time())
            print '#oldleads found ' + str(old_leads_repeat_visit.count())
            continue
            # we have the leads 
            
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
        print 'start time was ' + time1 + ' and end time is ' + str(time.time())
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    



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
