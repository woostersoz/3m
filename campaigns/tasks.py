from __future__ import absolute_import

import os
import datetime
from celery import shared_task
from mmm.celery import app
import datetime
from datetime import timedelta, datetime

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

from integrations.views import Marketo, Salesforce, Hubspot #, get_sfdc_test
from campaigns.models import Campaign
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
        campaignList = mkto.get_campaigns()
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
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))    

@app.task        
def retrieveSfdcCampaigns(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        sdfc = Salesforce()
        campaignList = sdfc.get_campaigns_delta(user_id, company_id, _str_from_date(sinceDateTime))
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
    try:
        hspt = Hubspot(company_id)
        campaignList = hspt.get_campaigns()
        print 'campaign list has ' + str(campaignList)
        saveHsptCampaigns(user_id=user_id, company_id=company_id, campaignList=campaignList, job_id=job_id, run_type=run_type)
        try:
            message = 'Campaigns retrieved from Hubspot'
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
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    campaignListTemp = list(campaigns)
    campaignList = [i['source_record'] for i in campaignListTemp]
    
    try: 
        for newCampaign in campaignList: 
            #company_id = request.user.company_id
            derived_id = 'mkto_' + str(newCampaign['id']) 
            Campaign.objects(Q(derived_id = derived_id) & Q(company_id=company_id)).modify(upsert=True, new=True, set__campaigns__mkto = newCampaign, set_on_insert__derived_id = derived_id, set_on_insert__company_id = company_id)
    
#             mktoCampaigns = []  
#             mktoCampaigns.append(campaign)            
#             campaign = Campaign()
#             campaign.company_id = request.user.company_id
#             campaign.derived_id = 'mkto_' + str(oldCampaign['id'])
#             campaign.campaigns["mkto"] = oldCampaign
#             campaign.save()
    except Exception as e:
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
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    campaignListTemp = list(campaigns)
    campaignList = [i['source_record'] for i in campaignListTemp]
    
    try: 
        for newCampaign in campaignList: #['records']: 
            #company_id = request.user.company_id
            derived_id = 'sfdc_' + str(newCampaign['Id']) 
            Campaign.objects(Q(derived_id = derived_id) & Q(company_id=company_id)).modify(upsert=True, new=True, set__campaigns__sfdc = newCampaign, set_on_insert__derived_id = derived_id, set_on_insert__company_id = company_id)

#         for oldCampaign in campaignList['records']: 
# #             mktoCampaigns = []  
# #             mktoCampaigns.append(campaign)            
#             campaign = Campaign()
#             campaign.company_id = request.user.company_id
#             campaign.derived_id = 'sfdc_' + str(oldCampaign['Id'])
#             campaign.campaigns["sfdc"] = oldCampaign
#             campaign.save()
    except Exception as e:
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))    

#save the data in the temp table
def saveHsptCampaigns(user_id=None, company_id=None, campaignList=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        for campaign in campaignList['campaigns']:
            saveTempData(company_id=company_id, record_type="campaign", source_system="hspt", source_record=campaign, job_id=job_id)
    else:
        for campaign in campaignList['campaigns']:
            saveTempDataDelta(company_id=company_id, record_type="campaign", source_system="hspt", source_record=campaign, job_id=job_id)
            
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
            derived_id = 'hspt_' + str(newCampaign['id']) 
            Campaign.objects(Q(derived_id = derived_id) & Q(company_id=company_id)).modify(upsert=True, new=True, set__campaigns__hspt = newCampaign, set_on_insert__derived_id = derived_id, set_on_insert__company_id = company_id, set_on_insert__updated_date=datetime.utcnow)
    except Exception as e:
        print 'exception ' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))    


       