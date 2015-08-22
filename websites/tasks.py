from __future__ import absolute_import
import os
import datetime, json, time
from datetime import timedelta, date, datetime
from dateutil import parser
from dateutil.tz import gettz, tzutc
import pytz, calendar
from pprint import pprint
from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

from integrations.views import Marketo, Salesforce, Hubspot, Google  # , get_sfdc_test
from leads.models import Lead
from collab.signals import send_notification
from collab.models import Notification 
from activities.tasks import retrieveMktoActivities
from company.models import TempData, TempDataDelta
from analytics.models import AnalyticsData, AnalyticsIds

from hubspot.contacts._schemas.contacts import CONTACT_SCHEMA

from mongoengine.queryset.visitor import Q
from mmm.views import _str_from_date
from mmm.views import saveTempData, saveTempDataDelta, _date_from_str
from websites.models import Traffic

from django.utils.timezone import get_current_timezone


@app.task
def retrieveHsptWebsiteTraffic(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        trafficList = []
        hspt = Hubspot(company_id)
        if run_type == 'initial':
            print 'initial run for website traffic'
            trafficList = hspt.get_traffic()
        else:
            trafficList = hspt.get_traffic()
        print 'Traffic got: ' + str(len(trafficList))
        #tzinfos = {"UTC" : gettz(tzutc().tzname)}
        #print 'tzinfos is ' + str(tzinfos)
        for traffic in trafficList:
            date_str = traffic + " 00:00:00 UTC"
            #print 'date str is ' + date_str
            utc_day_start = parser.parse(date_str)
            #print 'utc day start is ' + str(parser.parse(date_str))
            utc_day_end = utc_day_start + timedelta(seconds=86399)
            utc_day_start_epoch = calendar.timegm(utc_day_start.timetuple()) * 1000 #use calendar.timegm and not mktime because of UTC
            utc_day_start_epoch = str('{0:f}'.format(utc_day_start_epoch).rstrip('0').rstrip('.'))
            print 'utc epoch is ' + str(utc_day_start_epoch)
            utc_day_end_epoch = calendar.timegm(utc_day_end.timetuple()) * 1000
            utc_day_end_epoch = str('{0:f}'.format(utc_day_end_epoch).rstrip('0').rstrip('.'))
            #return
            for record in trafficList[traffic]: # this gives each 'breakdown' entry for the day
                channel = record['breakdown']
                if channel == 'social': # for now, only consider social
                    detailedTraffic = hspt.get_detailed_traffic(channel, utc_day_start_epoch, utc_day_start_epoch)
                    record['breakdowns'] = detailedTraffic.get('breakdowns', None)
        saveHsptWebsiteTraffic(user_id=user_id, company_id=company_id, trafficList=trafficList, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Website traffic retrieved from Hubspot'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Leads'
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
        return trafficList
    except Exception as e:
        print 'exception while retrieving sources data from hspt: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         
      
@app.task
def retrieveGoogWebsiteTraffic(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'starting GA traffic'
        trafficList = []
        
        print 'run for GA traffic'
        goog = Google(company_id)
        service = goog.create_service()
        accounts_list = goog.get_accounts(service)
        print 'got back goog accounts ' + str(len(accounts_list.get('items')))
        #if run_type == 'initial':
       
        start_date = sinceDateTime.strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=1)).date()
        end_date = end_date.strftime('%Y-%m-%d')
        for account in accounts_list.get('items'): #for each GA account
            try:
                account_id = account.get('id')
                account_name = account.get('name')
                profiles = goog.get_profiles(service, account_id) #find all profiles
                for profile in profiles.get('items', []): # for each GA profile
                    profile_id = profile.get('id')
                    profile_name = profile.get('name')
                    print 'profile id is ' + str(profile_id)
                    print 'start is ' + str(start_date) + ' and end is ' + str(end_date)
                    ids = 'ga:' + str(profile_id) 
                    metrics = 'ga:sessions, ga:bounces, ga:users, ga:newUsers, ga:pageviews'
                    dimensions = 'ga:userType, ga:date, ga:hour, ga:minute, ga:pageTitle, ga:source, ga:operatingSystem'
                    sort = 'ga:date, ga:hour'
                    trafficList = goog.get_metrics(service, ids, start_date, end_date, metrics, dimensions, sort)
                    print 'GA Traffic got: ' + str(len(trafficList))
                    saveGoogWebsiteTraffic(user_id=user_id, company_id=company_id, account_id=account_id, account_name=account_name, profile_id=profile_id, profile_name=profile_name, trafficList=trafficList, job_id=job_id, run_type=run_type)
            except Exception as e:
                print 'exception while retrieving GA data ' + str(e)
                send_notification(dict(type='error', success=False, message=str(e)))  
        try:
            message = 'Website traffic retrieved from Google Analytics'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Leads'
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
        return trafficList
    except Exception as e:
        print 'exception while retrieving GA data ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         
      

        
#save the data in the temp table
def saveHsptWebsiteTraffic(user_id=None, company_id=None, trafficList=None, job_id=None, run_type=None):
    print 'saving Hspt website traffic'
    
    if run_type == 'initial':
        for traffic in trafficList:
            record = {}
            record['date'] = traffic
            record['data'] = trafficList[traffic]
            saveTempData(company_id=company_id, record_type="traffic", source_system="hspt", source_record=record, job_id=job_id)
    else:
        for traffic in trafficList:
            record = {}
            record['date'] = traffic
            record['data'] = trafficList[traffic]
            saveTempDataDelta(company_id=company_id, record_type="traffic", source_system="hspt", source_record=record, job_id=job_id)
 
def saveHsptWebsiteTrafficToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    #job_id = ObjectId("55d76fb556ea06636022e016")
    if run_type == 'initial':
        traffic = TempData.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record')
    else:
        traffic = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record')
    
    #system_type_query = 'system_type'
    company_query = 'company_id'
    #chart_name_query = 'chart_name'
    #date_query = 'date'
    #chart_name = 'website_traffic'
    source_system_temp = 'hspt'
    source_system_qry = 'source_system'
    date_query = 'source_created_date'
        
    trafficList = list(traffic)
    trafficList = [i['source_record'] for i in trafficList]
    
    try:
        for traffic in trafficList:
            date = traffic['date']
            newTrafficData = traffic['data'] 
            #queryDict = {company_query : company_id, system_type_query: 'MA', chart_name_query: chart_name, date_query: date}
            queryDict = {company_query : company_id, source_system_qry: source_system_temp, date_query: date}
                
            trafficData = Traffic.objects(**queryDict).first()
            if trafficData is None:  
                trafficData = Traffic(company_id = company_id)
            trafficData.source_system = source_system_temp
            trafficData.source_created_date = date
            trafficData.data = {}
            trafficData.save() 
            for record in newTrafficData:
                source = record['breakdown']
                trafficData.data[source] = {}
                for datapoint in record:
                    if datapoint != 'breakdown':
                        trafficData.data[source][datapoint] = record[datapoint]
             
            Traffic.objects(id=trafficData.id).update(data = trafficData.data)
            
#             analyticsData = AnalyticsData.objects(**queryDict).first()
#             if analyticsData is None: #though not Initial, this date's record not found
#                 analyticsData = AnalyticsData()
#             analyticsData.system_type = 'MA'
#             analyticsData.company_id = company_id  
#             analyticsData.chart_name = chart_name
#             analyticsData.date = date
#             analyticsData.results = {}
#             analyticsData.save()
#             
#             analyticsData.date = date
#             
#             for record in trafficData:
#                 source = record['breakdown']
#                 analyticsData.results[source] = {}
#                 for datapoint in record:
#                     if datapoint != 'breakdown':
#                         analyticsData.results[source][datapoint] = record[datapoint]
#              
#             AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                        
    except Exception as e:
        print 'exception while saving hspt website data ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))     
        
#save the data in the temp table
def saveGoogWebsiteTraffic(user_id=None, company_id=None, account_id=None, account_name=None, profile_id=None, profile_name=None, trafficList=None, job_id=None, run_type=None):
    print 'saving GA website traffic'
    
    if run_type == 'initial':
        record = {}
        record['account_id'] = account_id
        record['account_name'] = account_name
        record['profile_id'] = profile_id
        record['profile_name'] = profile_name
        record['columns'] = trafficList.get('columnHeaders')
        record['data'] = trafficList.get('rows')
        saveTempData(company_id=company_id, record_type="traffic", source_system="goog", source_record=record, job_id=job_id)
    else:
        record = {}
        record['account_id'] = account_id
        record['account_name'] = account_name
        record['profile_id'] = profile_id
        record['profile_name'] = profile_name
        record['columns'] = trafficList.get('columnHeaders')
        record['data'] = trafficList.get('rows')
        saveTempDataDelta(company_id=company_id, record_type="traffic", source_system="goog", source_record=record, job_id=job_id)
         
def saveGoogleWebsiteTrafficToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    if run_type == 'initial':
        traffic = TempData.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='goog') & Q(job_id=job_id) ).only('source_record')
    else:
        traffic = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='goog') & Q(job_id=job_id) ).only('source_record')
        
    trafficList = list(traffic)
    trafficList = [i['source_record'] for i in trafficList]
    
    try:
        for i in range(len(trafficList)):
            ga_record = {}
            source_account_id = trafficList[i].get('account_id')
            source_account_name = trafficList[i].get('account_name')
            source_profile_id = trafficList[i].get('profile_id')
            source_profile_name = trafficList[i].get('profile_name')
            data = trafficList[i]['data']
            columns = trafficList[i]['columns']
            for data_single in data:
                for j in range(len(columns)):
                    ga_record[columns[j]['name']] = data_single[j]
                source_id = ga_record.get('ga:userType') + '-' + ga_record.get('ga:date') + '-' + ga_record.get('ga:hour') + '-' + ga_record.get('ga:minute') + '-' + ga_record.get('ga:pageTitle') + '-' + ga_record.get('ga:source') + '-' + ga_record.get('ga:operatingSystem')
                source_created_date = datetime.strptime(ga_record.get('ga:date'), '%Y%m%d').date()
                source_created_date = _str_from_date(source_created_date, 'short')            
                Traffic.objects(Q(company_id=company_id) & Q(source_id=source_id)).delete()
                website = Traffic(data=ga_record, company_id=company_id, source_system='goog', source_id=source_id, source_created_date=source_created_date, source_account_id=source_account_id, source_account_name=source_account_name, source_profile_id=source_profile_id, source_profile_name=source_profile_name)
                website.save()
            
    except Exception as e:
        print 'exception is ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e))) 
       