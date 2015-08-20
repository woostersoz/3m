from __future__ import absolute_import
import os
import datetime
from datetime import timedelta, datetime
from celery import shared_task
from mmm.celery import app

import json
from django.http import HttpResponse, JsonResponse
from django.utils.timezone import get_current_timezone
from rest_framework.response import Response

from integrations.views import Marketo, Salesforce, Hubspot  # , get_sfdc_test
from company.models import CompanyIntegration, TempData, TempDataDelta
from collab.signals import send_notification
from collab.models import Notification 
from integrations.views import Buffer, Facebook, FacebookPage
from social.models import PublishedTweet, FbAdInsight, FbPageInsight, FbPostInsight

from hubspot.contacts._schemas.contacts import CONTACT_SCHEMA

from mongoengine.queryset.visitor import Q
from mmm.views import saveTempData, saveTempDataDelta, _str_from_date, replace_dots

@app.task
def retrieveBufrTwInteractions(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'starting retrieveBufrTwInteractions for company ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
        if 'bufr' in existingIntegration['integrations']: # if Buffer is present and configured
            print 'found buffer'
            client_id = existingIntegration['integrations']['bufr']['client_id']
            client_secret = existingIntegration['integrations']['bufr']['client_secret']
            access_token = existingIntegration['integrations']['bufr']['access_token']
            buffer = Buffer()
            api = Buffer.get_api(buffer, client_id=client_id, client_secret=client_secret, access_token=access_token)
            profiles = Buffer.get_twitter_profiles(buffer, api)
            for profile in profiles:
                results = buffer.get_twitter_updates(profile)
                saveBufrTwInteractions(user_id=user_id, company_id=company_id, results=results, job_id=job_id, run_type=run_type)
                #print 'Tw results are ' + str(results)
        else:
            print 'No integration found with Buffer'
            return JsonResponse({'error' : 'No integration found with Buffer'})
        try:
            message = 'Twitter interactions retrieved from Buffer'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Social'
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
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))      

#save the data in the temp table
def saveBufrTwInteractions(user_id=None, company_id=None, results=None, job_id=None, run_type=None):
    #import pprint
    #pp = pprint.PrettyPrinter(indent=4)
    if run_type == 'initial':
        for result in results:
            #pp.pprint(result)
            result.pop("api", None)
            saveTempData(company_id=company_id, record_type="tw_interaction", source_system="bufr", source_record=result, job_id=job_id)
    else:
        for result in results:
            result.pop("api", None)
            saveTempDataDelta(company_id=company_id, record_type="tw_interaction", source_system="bufr", source_record=result, job_id=job_id)

def saveBufrTwInteractionsToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    
    if run_type == 'initial':
        tw_interactions = TempData.objects(Q(company_id=company_id) & Q(record_type='tw_interaction') & Q(source_system='bufr') & Q(job_id=job_id) ).only('source_record')
    else:
        tw_interactions = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='tw_interaction') & Q(source_system='bufr') & Q(job_id=job_id) ).only('source_record')
    
    company_query = 'company_id'
    interaction_id_query = 'interaction_id'
        
    tw_interactionsList = list(tw_interactions)
    tw_interactionsList = [i['source_record'] for i in tw_interactionsList]
    
    try:
        for interaction in tw_interactionsList:
            profile_id = interaction['profile_id']
            
            published_date = datetime.fromtimestamp(float(interaction['sent_at']))
            local_published_date = get_current_timezone().localize(published_date, is_dst=None)
            date = local_published_date.strftime('%Y-%m-%d')
            
            queryDict = {company_query : company_id, interaction_id_query: interaction['id']}
                
            publishedTweet = PublishedTweet.objects(**queryDict).first()
            if publishedTweet is None: #this tweet's record not found
                publishedTweet = PublishedTweet()
            publishedTweet.company_id = company_id
            publishedTweet.interaction_id = interaction['id']
            publishedTweet.published_date = date
            publishedTweet.published_timestamp = interaction['sent_at']
            publishedTweet.data = interaction
            
            publishedTweet.save()
#                         
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))     
        
@app.task
def retrieveFbokAdStats(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'starting retrieveFbokAdStats for company ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
        if 'fbok' not in existingIntegration['integrations']: # if Buffer is present and configured
            print 'did not find fbok'
            raise Exception('Facebook integration not found')
        integration = existingIntegration.integrations['fbok']
        if integration['access_token'] is None:
            raise Exception('Facebook access token not found')
        fbok = Facebook(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'])
        if fbok is None:
            raise Exception('Facebook object could not be created')
        
        print 'calling campaigns'
        campaigns = fbok.get_campaign_stats(company_id, run_type)
        print 'found FB campaigns: ' + str(campaigns)
        saveFbokAdStats(user_id=user_id, company_id=company_id, results=campaigns, job_id=job_id, run_type=run_type)
                
        
    except Exception as e:
        print 'exception was ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))      
        
#save the data in the temp table
def saveFbokAdStats(user_id=None, company_id=None, results=None, job_id=None, run_type=None):
    if run_type == 'initial':
        for result in results:
            saveTempData(company_id=company_id, record_type="fb_ad_stat", source_system="fbok", source_record=result, job_id=job_id)
    else:
        for result in results:
            saveTempDataDelta(company_id=company_id, record_type="fb_ad_stat", source_system="fbok", source_record=result, job_id=job_id)

def saveFbokAdStatsToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    
    if run_type == 'initial':
        fb_stats = TempData.objects(Q(company_id=company_id) & Q(record_type='fb_ad_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
    else:
        fb_stats = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='fb_ad_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
  
  
    fbList = list(fb_stats)
    fbList = [i['source_record'] for i in fbList]
    
    try:
        for i in range(len(fbList)):
            fb_record = {}
            source_campaign_id = fbList[i].get('id')
            source_campaign_name = fbList[i].get('name')
            source_account_id = fbList[i].get('account_id') 
            insights = fbList[i]['insights']
            for insight in insights:
                fb_record = insight['data']
                source_created_date = fb_record['date_stop']
                source_source = 'fbok'  
               
                FbAdInsight.objects(Q(company_id=company_id) & Q(source_created_date=source_created_date)& Q(source_campaign_id=source_campaign_id)).delete()
                fbAdInsight = FbAdInsight(data=fb_record, company_id=company_id, source_campaign_id=source_campaign_id, source_campaign_name=source_campaign_name, source_account_id=source_account_id, source_created_date=source_created_date)
                fbAdInsight.save()
            
    except Exception as e:
        print 'exception is ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e))) 
        
@app.task
def retrieveFbokPageStats(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'starting retrieveFbokPageStats for company ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
        if 'fbok' not in existingIntegration['integrations']: # if Buffer is present and configured
            print 'did not find fbok'
            raise Exception('Facebook integration not found')
        integration = existingIntegration.integrations['fbok']
        if integration['access_token'] is None:
            raise Exception('Facebook access token not found')
        fbok = FacebookPage(integration['access_token'])
        if fbok is None:
            raise Exception('Facebook Page object could not be created')
        
        print 'calling pages'
        pages = fbok.get_pages()['data']
        print 'found FB pages: ' + str(pages)
        for page in pages:
            page_token = page['access_token']
            page_id = page['id']
            page_insights = fbok.get_page_insights(page_id, page_token)
            #print 'page insights for ' + page['name'] + ': ' + str(page_insights)
            page_insights_cleaned = json.loads(json.dumps(page_insights['data']), object_hook = replace_dots)
            results = {'page_id': page_id, 'insights': page_insights_cleaned}
            saveFbokPageStats(user_id=user_id, company_id=company_id, results=results, job_id=job_id, run_type=run_type)
        #saveFbokAdStats(user_id=user_id, company_id=company_id, results=campaigns, job_id=job_id, run_type=run_type)
                
        
    except Exception as e:
        print 'exception was ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))      
   
#save the data in the temp table
def saveFbokPageStats(user_id=None, company_id=None, results=None, job_id=None, run_type=None):
    if run_type == 'initial':
        print 'results are ' + str(results)
        #for result in results:
        saveTempData(company_id=company_id, record_type="fb_page_stat", source_system="fbok", source_record=results, job_id=job_id)
    else:
        #for result in results:
        saveTempDataDelta(company_id=company_id, record_type="fb_page_stat", source_system="fbok", source_record=results, job_id=job_id)
      
      
def saveFbokPageStatsToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    
    if run_type == 'initial':
        fb_stats = TempData.objects(Q(company_id=company_id) & Q(record_type='fb_page_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
    else:
        fb_stats = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='fb_page_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
  
  
    fbList = list(fb_stats)
    fbList = [i['source_record'] for i in fbList]
    
    try:
        for i in range(len(fbList)):
            fb_record = {}
            source_page_id = fbList[i].get('page_id', None)
            insights = fbList[i].get('insights', None)
            for insight in insights:
                fb_record = insight
                source_metric_id = fb_record['id']
                source_metric_name = fb_record['name']
               
                fbPageInsight = FbPageInsight.objects(Q(company_id=company_id) & Q(source_metric_id=source_metric_id)& Q(source_page_id=source_page_id)).first()
                if fbPageInsight is None:
                    fbPageInsight = FbPageInsight(data=fb_record, company_id=company_id, source_metric_id=source_metric_id, source_metric_name=source_metric_name, source_page_id=source_page_id)
                else:
                    fbPageInsight['source_metric_name'] = source_metric_name
                    fbValuesList = fbPageInsight['data']['values']
                    for entry in fb_record['values']: #iterate through each new date value of metric to see if it already exists
                        if fb_record['period'] == 'lifetime':
                            fbPageInsight['data']['values'][0]['value'] = entry['value']
                        else:
                            if not any(d['end_time'] == entry['end_time'] for d in fbValuesList): # does this already exist?
                                fbValuesList.extend(entry) #if not, add the date entry to the existing record
                fbPageInsight.save()
            
    except Exception as e:
        print 'exception is ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e))) 
        
#FB Posts
@app.task
def retrieveFbokPostStats(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'starting retrieveFbokPostStats for company ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
        if 'fbok' not in existingIntegration['integrations']: # if Buffer is present and configured
            print 'did not find fbok'
            raise Exception('Facebook integration not found')
        integration = existingIntegration.integrations['fbok']
        if integration['access_token'] is None:
            raise Exception('Facebook access token not found')
        fbok = FacebookPage(integration['access_token'])
        if fbok is None:
            raise Exception('Facebook Page object could not be created')
        
        print 'calling pages'
        pages = fbok.get_pages()['data']
        print 'found FB pages: ' + str(pages)
        for page in pages:
            page_token = page['access_token']
            page_id = page['id']
            posts = fbok.get_posts(page_id, page_token)['data']
            for post in posts:
                post_insights = fbok.get_post_insights(post['id'], page_token)
                print 'post insights for ' + post['id'] + ': ' + str(post_insights)
                post_insights_cleaned = json.loads(json.dumps(post_insights['data']), object_hook = replace_dots)
                results = {'page_id': page_id, 'post_id' : post['id'], 'insights': post_insights_cleaned}
                saveFbokPostStats(user_id=user_id, company_id=company_id, results=results, job_id=job_id, run_type=run_type)
        #saveFbokAdStats(user_id=user_id, company_id=company_id, results=campaigns, job_id=job_id, run_type=run_type)
                
        
    except Exception as e:
        print 'exception was ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))      

#save the data in the temp table
def saveFbokPostStats(user_id=None, company_id=None, results=None, job_id=None, run_type=None):
    if run_type == 'initial':
        print 'results are ' + str(results)
        #for result in results:
        saveTempData(company_id=company_id, record_type="fb_post_stat", source_system="fbok", source_record=results, job_id=job_id)
    else:
        #for result in results:
        saveTempDataDelta(company_id=company_id, record_type="fb_post_stat", source_system="fbok", source_record=results, job_id=job_id)
  
def saveFbokPostStatsToMaster(user_id=None, company_id=None, job_id=None, run_type=None): #behaves differently because it directly saves the data to the AnalyticsData collection   
    
    if run_type == 'initial':
        fb_stats = TempData.objects(Q(company_id=company_id) & Q(record_type='fb_post_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
    else:
        fb_stats = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='fb_post_stat') & Q(source_system='fbok') & Q(job_id=job_id) ).only('source_record')
  
  
    fbList = list(fb_stats)
    fbList = [i['source_record'] for i in fbList]
    
    try:
        for i in range(len(fbList)):
            fb_record = {}
            source_page_id = fbList[i].get('page_id', None)
            source_post_id = fbList[i].get('post_id', None)
            insights = fbList[i].get('insights', None)
            for insight in insights:
                fb_record = insight
                source_metric_id = fb_record['id']
                source_metric_name = fb_record['name']
               
                fbPostInsight = FbPostInsight.objects(Q(company_id=company_id) & Q(source_metric_id=source_metric_id)& Q(source_page_id=source_page_id) & Q(source_post_id=source_post_id)).first()
                if fbPostInsight is None:
                    fbPostInsight = FbPostInsight(data=fb_record, company_id=company_id, source_metric_id=source_metric_id, source_metric_name=source_metric_name, source_page_id=source_page_id, source_post_id=source_post_id)
                else:
                    fbPostInsight['source_metric_name'] = source_metric_name
                    fbValuesList = fbPostInsight['data']['values']
                    for entry in fb_record['values']: #iterate through each new date value of metric to see if it already exists
                        if fb_record['period'] == 'lifetime':
                            fbPostInsight['data']['values'][0]['value'] = entry['value']
                        else:
                            if not any(d['end_time'] == entry['end_time'] for d in fbValuesList): # does this already exist?
                                fbValuesList.extend(entry) #if not, add the date entry to the existing record
                fbPostInsight.save()
            
    except Exception as e:
        print 'exception is ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e))) 
             