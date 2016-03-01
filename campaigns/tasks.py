from __future__ import absolute_import

import os
import datetime
from celery import shared_task
from mmm.celery import app
import datetime, calendar
from datetime import timedelta, datetime
from bson.objectid import ObjectId

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

from integrations.views import Marketo, Salesforce, Hubspot #, get_sfdc_test
from campaigns.models import Campaign, EmailEvent
from collab.signals import send_notification
from collab.models import Notification 
from mongoengine.queryset.visitor import Q
from mmm.views import _str_from_date
from mmm.views import saveTempData, saveTempDataDelta
from company.models import TempData, TempDataDelta

@app.task
def retrieveMktoCampaigns(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        mkto = Marketo(company_id)
        campaignList = mkto.get_programs()
        saveMktoCampaigns(user_id=user_id, company_id=company_id, campaignList=campaignList, job_id=job_id, run_type=run_type)
        try:
            message = 'Campaigns retrieved from Marketo'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Campaigns'
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
        return campaignList
    except Exception as e:
        print 'error while retrieving marketo campaigns: ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    

@app.task        
def retrieveSfdcCampaigns(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        sdfc = Salesforce()
        campaignList = sdfc.get_campaigns_delta(user_id, company_id, _str_from_date(sinceDateTime), run_type)
        saveSfdcCampaigns(user_id=user_id, company_id=company_id, campaignList=campaignList, job_id=job_id, run_type=run_type)
        try:
            message = 'Campaigns retrieved from Salesforce'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Campaigns'
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
        return campaignList
    except Exception as e:
        print 'error while retrieving sfdc campaigns: ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    
        
# @app.task        
# def retrieveSfdcCampaignsDaily(user_id=None, company_id=None, job_id=None, run_type=None):
#     try:
#         sdfc = Salesforce()
#         sinceDateTime = (datetime.now() - timedelta(days=1)).date()
#         campaignList = sdfc.get_campaigns_daily(user_id, company_id, _str_from_date(sinceDateTime))
#         saveSfdcCampaigns(user_id=user_id, company_id=company_id, campaignList=campaignList, job_id=job_id)
#         try:
#             message = 'Daily campaigns retrieved from Salesforce'
#             notification = Notification()
#             #notification.company_id = company_id
#             notification.owner = user_id
#             notification.module = 'Campaigns'
#             notification.type = 'Background task' 
#             notification.method = os.path.basename(__file__)
#             notification.message = message
#             notification.success = True
#             notification.read = False
#             notification.save()
#         except Exception as e:
#             send_notification(dict(
#                  type='error',
#                  success=False,
#                  message=str(e)
#                 ))    
#         return campaignList
#     except Exception as e:
#         send_notification(dict(
#              type='error',
#              success=False,
#              message=str(e)
#             ))    

@app.task
def retrieveHsptCampaigns(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    '''remember that campaigns in HSPT API terms refers to email templates! here, we use actualCampaign to represent the Campaign and campaign to refer to email templates '''
    try:
        actualCampaigns = []
        actualCampaignsDict = {}
        actualCampaignsTempList = []
        
        utc_day_start_epoch = calendar.timegm(sinceDateTime.timetuple()) * 1000 #use calendar.timegm and not mktime because of UTC
        utc_day_start_epoch = str('{0:f}'.format(utc_day_start_epoch).rstrip('0').rstrip('.'))
        print 'utc start epoch is ' + str(utc_day_start_epoch)
        utc_day_end_epoch = calendar.timegm(datetime.now().timetuple()) * 1000
        utc_day_end_epoch = str('{0:f}'.format(utc_day_end_epoch).rstrip('0').rstrip('.'))
        print 'utc end epoch is ' + str(utc_day_end_epoch)
        
        hspt = Hubspot(company_id)
        if run_type == 'initial':
            campaignList = hspt.get_all_campaigns()
            #campaignList = hspt.get_recent_campaigns()
        else:
            campaignList = hspt.get_recent_campaigns()
        
        #print 'campaign list has entries' + str(len(campaignList['results']))
        #print 'campaign list is ' + str(campaignList)
        #campaignIds = [i['id'] for i in campaignList['results']]
        for i in campaignList['results']:
            #if i['id'] != 23202074:
            #    continue
            campaignStats = hspt.get_campaign_stats(i['id'])
            i['stats'] = campaignStats.get('stats', None)
            
            campaignDetails = hspt.get_campaign_details(campaignId=i['id'], appId=i['appId'])
            i['details'] = campaignDetails
            
            if 'contentId' not in campaignDetails:
                continue
            contentId = campaignDetails['contentId']
            email_content = hspt.get_email_by_content_id(contentId)
            #get events
            #i['events'] = {}
            
            email_events = hspt.get_campaign_events(i['id'], i['appId'], utc_day_start_epoch, utc_day_end_epoch)
           
            #i['events'] = email_events
            #print 'email events are ' + str(email_events)
            #process each event to add to lead record
            #for event in i['events']:
          
            #set other variables
            i['name'] = email_content['name']
            i['created'] = email_content['created']
            i['last_event_timestamp'] = 0
            #print 'guid is ' + str(email_content['campaign'])
            #if campaign GUID found, do actualCampaign stuff
            if 'campaign' in email_content and email_content['campaign'] is not None and email_content['campaign'] != "":
                if email_content['campaign'] not in actualCampaignsTempList: #first time this actualcampaign is being encountered
                    #print 'campaign not found'
                    actualCampaignsTempList.append(email_content['campaign'])
                    #print '1'
                    actualCampaignsDict[email_content['campaign']] = {}
                    actualCampaignsDict[email_content['campaign']]['guid'] = email_content['campaign']
                    actualCampaignsDict[email_content['campaign']]['name'] = email_content['campaign_name']
                    #print '2'
                    actualCampaignsDict[email_content['campaign']]['emails'] = []
                    actualCampaignsDict[email_content['campaign']]['emails'].append(i)
                    #print '3'
                    #print '1st dict is ' + str(actualCampaignsDict)
                else: #this actualcampaign has already been found before so add this email template to it
                    #print 'campaign exists ' + str(actualCampaignsDict)
                    actualCampaignsDict[email_content['campaign']]['emails'].append(i)
                #save email events separately to prevent Mongo size error
                #print 'email events is ' + str(email_events)
                if email_events is None:
                    continue
                for eventType, events in email_events.iteritems():
                    for event in events:
                        event_record = {'company_id': company_id, 'source_system':'hspt', 'campaign_guid': email_content['campaign'], 'email_id': i['id'], 'event_id': event['id'], 'event_type': eventType, 'created': event['created'], 'recipient': event['recipient'], 'details': event}
                        saveHsptCampaignEmailEvent(user_id=user_id, company_id=company_id, event=event_record, job_id=job_id, run_type=run_type)
                #break       
        #now that all email templates have been processed, iterate through the dict to fill the final array
        #print 'dict is ' + str(actualCampaignsDict)
        for key, value in actualCampaignsDict.iteritems():
            actualCampaigns.append(value)
            
        #print 'campaigns result is ' + str(actualCampaigns)
                        
            #with the content id, find the actual Campaign GUID and Name
            #campaignEventsTemp = hspt.get_campaign_events(campaignId=i['id'], appId=i['appId'])
            #i['events'] = campaignEventsTemp.get('results', None)
            
#             #campaignContacts = hspt.get_campaign_contacts(i['id'])
#             #i['contacts] = 
#             #print 'campaign contacts are ' + str(campaignContacts)
        for campaign in actualCampaigns: 
            saveHsptCampaigns(user_id=user_id, company_id=company_id, campaign=campaign, job_id=job_id, run_type=run_type)
        try:
            message = 'Email templates (Campaigns) retrieved from Hubspot'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Campaigns'
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
        return campaignList
    except Exception as e:
        print 'error while retrieving hspt campaigns: ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    

#save the data in the temp table
def saveMktoCampaigns(user_id=None, company_id=None, campaignList=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        for campaign in campaignList:
            saveTempData(company_id=company_id, record_type="campaign", source_system="mkto", source_record=campaign, job_id=job_id)
    else:
        for campaign in campaignList:
            saveTempDataDelta(company_id=company_id, record_type="campaign", source_system="mkto", source_record=campaign, job_id=job_id)
    
def saveMktoCampaignsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #job_id = ObjectId("56d25c6af6fd2a15df46cd60")
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    campaignListTemp = list(campaigns)
    campaignList = [i['source_record'] for i in campaignListTemp]
    
    try: 
        for newCampaign in campaignList: 
            #company_id = request.user.company_id
            guid = 'mkto_' + str(newCampaign['id']) 
            Campaign.objects(Q(guid = guid) & Q(company_id=company_id)).modify(upsert=True, new=True, set__campaigns__mkto = newCampaign, set__updated_date = datetime.utcnow, set_on_insert__source_system = 'mkto', set_on_insert__guid = guid, set_on_insert__company_id = company_id)
    
#             mktoCampaigns = []  
#             mktoCampaigns.append(campaign)            
#             campaign = Campaign()
#             campaign.company_id = request.user.company_id
#             campaign.derived_id = 'mkto_' + str(oldCampaign['id'])
#             campaign.campaigns["mkto"] = oldCampaign
#             campaign.save()
    except Exception as e:
        print 'error while saving mkto campaign: ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    


#save the data in the temp table
def saveSfdcCampaigns(user_id=None, company_id=None, campaignList=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        for campaign in campaignList['records']:
            saveTempData(company_id=company_id, record_type="campaign", source_system="sfdc", source_record=campaign, job_id=job_id)
    else:
        for campaign in campaignList['records']:
            saveTempDataDelta(company_id=company_id, record_type="campaign", source_system="sfdc", source_record=campaign, job_id=job_id)
       
def saveSfdcCampaignsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #job_id = ObjectId("56d25c6af6fd2a15df46cd60")
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    campaignListTemp = list(campaigns)
    campaignList = [i['source_record'] for i in campaignListTemp]
    
    try: 
        for newCampaign in campaignList: #['records']: 
            #company_id = request.user.company_id
            guid = 'sfdc_' + str(newCampaign['Id']) 
            Campaign.objects(Q(guid = guid) & Q(company_id=company_id)).modify(upsert=True, new=True, set__campaigns__sfdc = newCampaign, set__updated_date = datetime.utcnow, set_on_insert__source_system = 'sfdc', set_on_insert__guid = guid, set_on_insert__company_id = company_id)

#         for oldCampaign in campaignList['records']: 
# #             mktoCampaigns = []  
# #             mktoCampaigns.append(campaign)            
#             campaign = Campaign()
#             campaign.company_id = request.user.company_id
#             campaign.derived_id = 'sfdc_' + str(oldCampaign['Id'])
#             campaign.campaigns["sfdc"] = oldCampaign
#             campaign.save()
    except Exception as e:
        print 'error while saving sfdc campaign: ' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))    

#save the data in the temp table
def saveHsptCampaigns(user_id=None, company_id=None, campaign=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        saveTempData(company_id=company_id, record_type="campaign", source_system="hspt", source_record=campaign, job_id=job_id)
    else:
        #for campaign in campaignList['results']:
        #for campaign in campaignList:
        saveTempDataDelta(company_id=company_id, record_type="campaign", source_system="hspt", source_record=campaign, job_id=job_id)

def saveHsptCampaignEmailEvent(user_id=None, company_id=None, event=None, job_id=None, run_type=None):
    #print 'saving hspt email event in temp'
    if run_type == 'initial':
        saveTempData(company_id=company_id, record_type="campaign_email_event", source_system="hspt", source_record=event, job_id=job_id)
    else:
        saveTempDataDelta(company_id=company_id, record_type="campaign_email_event", source_system="hspt", source_record=event, job_id=job_id)
                                 
def saveHsptCampaignsToMasterDeprecated(user_id=None, company_id=None, job_id=None, run_type=None):   
    pass

def saveHsptCampaignsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    campaignListTemp = list(campaigns)
    campaignList = [i['source_record'] for i in campaignListTemp]
    
    try: 
        for newCampaign in campaignList: 
            #company_id = request.user.company_id
            #derived_id = 'hspt_' + str(newCampaign['id']) 
            guid = newCampaign['guid']
            name = newCampaign['name']
            source_system = 'hspt'
            channel = 'email'
            emails = newCampaign['emails']
            
            #save all email events for this campaign first
            saveHsptCampaignEmailEventRecords(company_id=company_id, run_type=run_type, job_id=job_id, guid=guid)
            
            #now update or create campaign record
            existingCampaign = Campaign.objects(Q(guid = guid) & Q(company_id=company_id) & Q(source_system=source_system)).first() #.modify(upsert=True, new=True, set__emails = emails, set_on_insert__name = name, set_on_insert__guid = guid, set_on_insert__company_id = company_id, set_on_insert__updated_date=datetime.utcnow)
            if existingCampaign is None: #new campaign so add it
                newCampaign = Campaign(emails = emails, name = name, guid = guid, company_id = company_id, updated_date=datetime.utcnow, source_system=source_system)
                newCampaign.save()
            else: #campaign already exists so update relevant fields
                #print 'existing campaign is ' + str(existingCampaign)
                if 'emails' not in existingCampaign: #should never happen
                    continue
                #print 'before emails ' + str(emails)
                for email in emails: #loop through each email found in API call for this campaign
                    #save events separately
                    #print 'entering emails'
                    
                    #now create/update the campaign record        
                    email_found = False
                    for existingEmail in existingCampaign['emails']: #check if the API email already exists
                        if email['id'] == existingEmail['id']: #we found this email already existing so update specific fields
                            email_found = True
                            existingEmail['stats'] = email['stats']
                            existingEmail['details'] = email['details']
                            
                        if email_found:
                            existingCampaign.save()
                            break #move to the next API email since we already found a match
                    if email_found == False: #email was not found so add it to existing emails
                        existingCampaign['emails'].append(email)
                        existingCampaign.save()
                    
        
    except Exception as e:
        print 'exception ' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))    

def saveHsptCampaignEmailEventRecords(company_id=None, run_type=None, job_id=None, guid=None):
    '''called from saveHsptCampaignsToMaster to save all events for a single Hspt campaign email record'''
    try:
        #print 'saving single event'
        if run_type == 'initial':
            events = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign_email_event') & Q(source_system='hspt') & Q(job_id=job_id) & Q(source_record__campaign_guid=guid) ).only('source_record') #& Q(job_id=job_id) 
        else:
            events = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign_email_event') & Q(source_system='hspt') & Q(job_id=job_id) & Q(source_record__campaign_guid=guid) ).only('source_record') #& Q(job_id=job_id) 
        eventsListTemp = list(events)
        eventsList = [j['source_record'] for j in eventsListTemp]
        #print 'found events ' + str(eventsList)
        for event in eventsList:
            #print 'about to check for event with ' + guid + ' email id ' + str(email['id'])  + ' event id ' +  str(event['event_id']) + ' recipient ' + str(event['recipient']) + ' created ' + str(event['created']) + ' details ' + str(event)    
            existingEvent = EmailEvent.objects(Q(company_id=company_id) & Q(campaign_guid=guid) & Q(email_id=event['email_id']) & Q(event_id=event['event_id'])).first()
            if existingEvent is None:
                newEvent = EmailEvent(company_id=company_id, source_system='hspt',  campaign_guid=guid, email_id=event['email_id'], event_id=event['event_id'], details=event['details'], recipient=event['recipient'], created=event['created'], event_type=event['event_type'])
                #print 'about to save new event with ' + guid + ' email id ' + str(email['id'])  + ' event id ' +  str(event['event_id']) + ' recipient ' + str(event['recipient']) + ' created ' + str(event['created']) + ' details ' + str(event)
                newEvent.save()   
    except Exception as e:
        print 'error while saving single Hspt campaign event record  ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))      
                
                
def createHsptCampaignFromTraffic(name, channel, company_id):
    '''Create campaigns for Hubspot from website traffic because there is no direct API method to extract campaigns '''
    try:
        existingCampaign = Campaign.objects(Q(name=name) & Q(channel=channel) & Q(company_id=company_id) & Q(source_system='hspt')).first()
        if existingCampaign is None:
            newCampaign = Campaign(name=name, channel=channel, company_id=company_id, source_system='hspt')
            newCampaign.save()
    except Exception as e:
        print 'error while saving Hspt campaign from traffic ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))     
        
def associateEmailWithCampaign(name, channel, company_id, email_id, job_id, run_type):
    '''Associate an email template with a Hubspot campaign - from website traffic because there is no direct API method to extract campaigns '''
    try:
        existingCampaign = Campaign.objects(Q(name=name) & Q(channel=channel) & Q(company_id=company_id) & Q(source_system='hspt')).first()
        if existingCampaign is None:
            return #this should not happen
        else:
            emails = existingCampaign['emails']
            if emails is None: #create a new email for the campaign
                _doAssociationEmailWithCampaign(email_id, existingCampaign, company_id, job_id, run_type)
            else:
                email_exists = False
                for email in emails:
                    emailDetails = None
                    if email['id'] == email_id: #if email exists, only update the details
                        email_exists = True
                        emailDetails = _get_hspt_email_details(email_id, existingCampaign, company_id, job_id, run_type)
                        email['details'] = emailDetails
                        existingCampaign.save()
                        print 'existing email updated'
                if email_exists == False: #else, create a new email for the campaign
                    _doAssociationEmailWithCampaign(email_id, existingCampaign, company_id, job_id, run_type)
                
    except Exception as e:
        print 'error while associating email with Hspt campaign from traffic ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))     
       
def _doAssociationEmailWithCampaign(email_id, existingCampaign, company_id, job_id, run_type):
    try:
        #first get email templates stored in temp table
        emailDetails = _get_hspt_email_details(email_id, existingCampaign, company_id, job_id, run_type)
        #now populate details in the record and save back into campaign
        emails = existingCampaign['emails']
        new_email = {}
        new_email['id'] = email_id
        new_email['details'] = emailDetails
        emails.append(new_email)
        existingCampaign['emails'] = emails
        existingCampaign.save()
    except Exception as e:
        print 'error while doing association of email with Hspt campaign from traffic ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))  

def _get_hspt_email_details(email_id, existingCampaign, company_id, job_id, run_type):
    try:
        if run_type == 'initial':
            campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
        else:
            campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
        campaignListTemp = list(campaigns)
        campaignList = [i['source_record'] for i in campaignListTemp]
        #print 'temp recs found ' + str(len(campaignList))
        #now get the appId for this email Id
        app_id = None
        int_email_id = 0
        for campaign in campaignList:
            #print 'campaign in temp ' + str(campaign)
            if str(campaign['id']) == email_id:
                print 'campaign id is ' + str(campaign['id']) + ' and email id is ' + email_id
                app_id = campaign['appId']
                int_email_id = campaign['id']
                break
        #if appId found, get details
        emailDetails = None
        if app_id is not None:
            hspt = Hubspot(company_id)
            emailDetails = hspt.get_campaign_details(campaignId=int_email_id, appId=app_id) 
        return emailDetails   
    except Exception as e:
        print 'error while getting email details with Hspt campaign from traffic ' + str(e)
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))  
