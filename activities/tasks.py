from __future__ import absolute_import
from datetime import timedelta, datetime
import os

from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from mongoengine.queryset.visitor import Q

from leads.models import Lead
from company.models import CompanyIntegration, TempData, TempDataDelta
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from mmm.views import saveTempData, saveTempDataDelta, _str_from_date


@app.task
def retrieveMktoActivities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    #return
    try:
        print 'getting mkto activities'
        #company_id = request.user.company_id
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
        activityTypeIds = []
#         if existingIntegration is not None:
#             activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
#             for i in range(len(activityTypeArray)):
#                 if (activityTypeArray[i]['name'] == 'Send Email' or activityTypeArray[i]['name'] == 'Email Delivered' or activityTypeArray[i]['name'] == 'Open Email' or activityTypeArray[i]['name'] == 'Visit Webpage' or activityTypeArray[i]['name'] == 'Fill out Form' or activityTypeArray[i]['name'] == 'Click Link' or activityTypeArray[i]['name'] == 'Email Bounced' or activityTypeArray[i]['name'] == 'Email Unsubscribed'  or activityTypeArray[i]['name'] == 'Change Data Value'):
#                     activityTypeIds.append(str(activityTypeArray[i]['id']))

        if existingIntegration is not None:
            activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
            for i in range(len(activityTypeArray)):
                activityTypeIds.append(str(activityTypeArray[i]['id']))

        if activityTypeIds is None:
            return []
        
        if sinceDateTime is None:
            sinceDateTime = datetime.now() - timedelta(days=30) #change to 365
        mkto = Marketo(company_id)

        batch_size = 10  #10 Activity Types at a time
        activityList = []
        for i in range(0, len(activityTypeIds), batch_size):
            activityTypeIdsTemp =  activityTypeIds[i:i+batch_size]
            print 'gettng activities for ' + str(activityTypeIdsTemp)
            activityList.extend(mkto.get_lead_activity(activityTypeIdsTemp, sinceDatetime=sinceDateTime))
        
        print 'going to save mkto activities - count ' + str(len(activityList))
        saveMktoActivities(user_id=user_id, company_id=company_id, activityList=activityList, activityTypeArray=activityTypeArray, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Activities retrieved from Marketo'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Activities'
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
        return activityList
    except Exception as e:
        send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))   
        
# @app.task
# def retrieveMktoActivitiesDaily(user_id=None, company_id=None, job_id=None, sinceDateTime=None):
#     try:
#         #company_id = request.user.company_id
#         existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
#         activityTypeIds = []
#         if existingIntegration is not None:
#             activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
#             for i in range(len(activityTypeArray)):
#                 activityTypeIds.append(str(activityTypeArray[i]['id']))
# 
#         if activityTypeIds is None:
#             return []
#         
#         mkto = Marketo(company_id)
#         if sinceDateTime is None:
#             sinceDateTime = datetime.now() - timedelta(days=1) # for the past 24 hours
#         batch_size = 10  #10 Activity Types at a time
#         activityList = []
#         for i in range(0, len(activityTypeIds), batch_size):
#             activityTypeIdsTemp =  activityTypeIds[i:i+batch_size]
#             activityList.extend(mkto.get_lead_activity(activityTypeIdsTemp, sinceDatetime=sinceDateTime))
#         saveMktoActivitiesDelta(user_id=user_id, company_id=company_id, activityList=activityList, activityTypeArray=activityTypeArray, job_id=job_id)
# #         fields = []
# #         fields.append('leadStatus')
# #         changeList = mkto.get_lead_changes(fields, sinceDatetime=datetime.now() - timedelta(days=365))
# #         print 'gto back mkto changes ' + str(len(changeList))
#         try:
#             message = 'Daily activities retrieved from Marketo'
#             notification = Notification()
#             #notification.company_id = company_id
#             notification.owner = user_id
#             notification.module = 'Activities'
#             notification.type = 'Background task' 
#             notification.method = os.path.basename(__file__)
#             notification.message = message
#             notification.success = True
#             notification.read = False
#             notification.save()
#         except Exception as e:
#             send_notification(dict(
#              type='error',
#              success=False,
#              message=str(e)
#             ))         
#         return activityList
#     except Exception as e:
#         send_notification(dict(
#              type='error',
#              success=False,
#              message=str(e)
#             ))   

@app.task    
def retrieveSfdcActivities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None): #needs to be changed - satya
    try:
        #for leads
        leads = TempData.objects(Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        leadListTemp = list(leads)
        leadList = [i['source_record'] for i in leadListTemp]
        lead_list = '('
        for lead in leadList:
            lead_list += '\'' + lead['Id'] + '\'' + ', '
        lead_list = lead_list[:-2]
        lead_list += ')'
        sfdc = Salesforce()
        activitiesList = sfdc.get_activities_for_lead_delta(user_id, company_id, lead_list, _str_from_date(sinceDateTime))
        print 'got back activities for leads ' + str(len(activitiesList))
        saveSfdcActivities(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id, run_type=run_type)
        
        #for contacts
        contacts = TempData.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        contactListTemp = list(contacts)
        contactList = [i['source_record'] for i in contactListTemp]
        contact_list = '('
        for contact in contactList:
            contact_list += '\'' + contact['Id'] + '\'' + ', '
        contact_list = contact_list[:-2]
        contact_list += ')'
        sfdc = Salesforce()
        activitiesList = sfdc.get_activities_for_contact_delta(user_id, company_id, contact_list, _str_from_date(sinceDateTime))
        print 'got back activities for contacts ' + str(len(activitiesList))
        saveSfdcActivities(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id, run_type=run_type)
        
        
        try:
            message = 'Activities retrieved from Salesforce'
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
        return leadList
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))   
        
# @app.task    
# def retrieveSfdcActivitiesDaily(user_id=None, company_id=None, job_id=None, sinceDateTime=None): #needs to be changed - satya
#     try:
#         #for leads
#         leads = TempData.objects(Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
#         leadListTemp = list(leads)
#         leadList = [i['source_record'] for i in leadListTemp]
#         lead_list = '('
#         for lead in leadList:
#             lead_list += '\'' + lead['Id'] + '\'' + ', '
#         lead_list = lead_list[:-2]
#         lead_list += ')'
#         sfdc = Salesforce()
#         activitiesList = sfdc.get_activities_for_lead_delta(user_id, company_id, lead_list, sinceDateTime)
#         print 'got back activities for leads ' + str(len(activitiesList))
#         saveSfdcActivitiesDelta(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id)
#         
#         #for contacts
#         contacts = TempData.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
#         contactListTemp = list(contacts)
#         contactList = [i['source_record'] for i in contactListTemp]
#         contact_list = '('
#         for contact in contactList:
#             contact_list += '\'' + contact['Id'] + '\'' + ', '
#         contact_list = contact_list[:-2]
#         contact_list += ')'
#         sfdc = Salesforce()
#         activitiesList = sfdc.get_activities_for_contact_delta(user_id, company_id, contact_list, sinceDateTime)
#         print 'got back activities for contacts ' + str(len(activitiesList))
#         saveSfdcActivitiesDelta(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id)
#         
#         
#         try:
#             message = 'Activities retrieved from Salesforce'
#             notification = Notification()
#             #notification.company_id = company_id
#             notification.owner = user_id
#             notification.module = 'Leads'
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
#         return leadList
#     except Exception as e:
#         send_notification(dict(type='error', success=False, message=str(e)))   
        
@app.task        
def retrieveHsptActivities(user_id=None, company_id=None, job_id=None): #needs to be changed - satya
    pass        
    #return HttpResponse(leadList, status.HTTP_200_OK)

#save the data in the temp table
def saveMktoActivities(user_id=None, company_id=None, activityList=None, activityTypeArray=None, job_id=None, run_type=None):
    print 'saving mkto activities'
    if run_type == 'initial':
        for activity in activityList:
            saveTempData(company_id=company_id, record_type="activity", source_system="mkto", source_record=activity, job_id=job_id)
    else:
        for activity in activityList:
            saveTempDataDelta(company_id=company_id, record_type="activity", source_system="mkto", source_record=activity, job_id=job_id)

#save the data in the temp table
# def saveMktoActivitiesDelta(user_id=None, company_id=None, activityList=None, activityTypeArray=None, job_id=None):
#     print 'saving mkto activities'
#     for activity in activityList:
#         saveTempDataDelta(company_id=company_id, record_type="activity", source_system="mkto", source_record=activity, job_id=job_id)

def saveMktoActivitiesToMaster(user_id=None, company_id=None, job_id=None, run_type=None): 
    if run_type == 'initial':   
        activities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
    else:
        activities = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
    activityListTemp = list(activities)
    activityList = [i['source_record'] for i in activityListTemp]
    
    existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
    if existingIntegration is not None:
        activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
    else:
        print 'No activity type metadata found for Marketo'
        raise ValueError('No activity type metadata found for Marketo')
    
    try: 
        for i in range(len(activityTypeArray)):
            if activityTypeArray[i]['name'] == 'Change Data Value':
                changeActivityId = activityTypeArray[i]['id']
        print 'change id is ' + str(changeActivityId)
        
        for newActivity in activityList: 
            
            addThisActivity = True
            
            #company_id = request.user.company_id
            mkto_id = str(newActivity['leadId'])
            
            existingLead = Lead.objects(Q(mkto_id = str(mkto_id)) & Q(company_id = company_id)).first()
            if existingLead is not None: # we found this lead to attach the activities
                if 'mkto' in existingLead.activities:
                    currentActivities = existingLead.activities['mkto']        
                    for i in range(len(currentActivities)):
                        if currentActivities[i]['id'] == newActivity['id']: #check if this activity already exists in the lead dict
                            addThisActivity = False
                            break
                    if addThisActivity == True:
                        for i in range(len(activityTypeArray)):
                            if activityTypeArray[i]['id'] == newActivity['activityTypeId']:
                                newActivity['activityTypeName'] = activityTypeArray[i]['name']
                                break
                        currentActivities.append(newActivity)
                        existingLead.update(activities__mkto = currentActivities)
                        
                else:
                    currentActivities = []
                    for i in range(len(activityTypeArray)):
                        if activityTypeArray[i]['id'] == newActivity['activityTypeId']:
                            newActivity['activityTypeName'] = activityTypeArray[i]['name']
                            break
                    currentActivities.append(newActivity)
                    existingLead.update(activities__mkto = currentActivities)
                #addThisActivity == True and    
                if addThisActivity == True and newActivity['activityTypeId'] == changeActivityId and newActivity['primaryAttributeValue'] == 'Lead Status':
                    print 'processing status activity for id ' + mkto_id
                    #statusRecord = [];
                    for attribute in newActivity['attributes']:
                        if attribute['name'] == 'New Value':
                            newStatus = attribute['value']
                            break
                    #statusRecord.append({'status': newStatus, 'date': newActivity['activityDate']})
                    if 'mkto' in existingLead.statuses:
                        currentStatuses = existingLead.statuses['mkto']
                        currentStatuses.append({'status': newStatus, 'date': newActivity['activityDate']})
                        existingLead.update(statuses__mkto = currentStatuses)
                    else:
                        currentStatuses = []
                        currentStatuses.append({'status': newStatus, 'date': newActivity['activityDate']})
                        existingLead.update(statuses__mkto = currentStatuses)
                        
#                 if addThisActivity == True: # this activity was not foudn in the lead, so add it
#                     existingLead.activities['mkto'].append(newActivity)
#                 existingLead.save() # no concept of saving the activity if the lead does not exist
    except Exception as e:
            send_notification(dict(
             type='error',
             success=False,
             message=str(e)
            ))   
    
def saveSfdcActivities(user_id=None, company_id=None, activityList=None, job_id=None, run_type=None):    
    print 'saving sfdc activities for leads'
    if run_type == 'initial':
        for activity in activityList:
            saveTempData(company_id=company_id, record_type="activity", source_system="sfdc", source_record=activity, job_id=job_id)
    else:
        for activity in activityList:
            saveTempDataDelta(company_id=company_id, record_type="activity", source_system="sfdc", source_record=activity, job_id=job_id)
    



