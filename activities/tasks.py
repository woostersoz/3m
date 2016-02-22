from __future__ import absolute_import
from datetime import timedelta, datetime
import os

from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from mongoengine.queryset.visitor import Q
from bson.objectid import ObjectId

from leads.models import Lead
from company.models import CompanyIntegration, TempData, TempDataDelta
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from accounts.models import Account
from mmm.views import saveTempData, saveTempDataDelta, _str_from_date


@app.task
def retrieveMktoLeadCreatedActivities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    #return
    try:
        print 'getting mkto lead created activities'
#         #company_id = request.user.company_id
#         existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
#         activityTypeIds = []
# #         if existingIntegration is not None:
# #             activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
# #             for i in range(len(activityTypeArray)):
# #                 if (activityTypeArray[i]['name'] == 'Send Email' or activityTypeArray[i]['name'] == 'Email Delivered' or activityTypeArray[i]['name'] == 'Open Email' or activityTypeArray[i]['name'] == 'Visit Webpage' or activityTypeArray[i]['name'] == 'Fill out Form' or activityTypeArray[i]['name'] == 'Click Link' or activityTypeArray[i]['name'] == 'Email Bounced' or activityTypeArray[i]['name'] == 'Email Unsubscribed'  or activityTypeArray[i]['name'] == 'Change Data Value'):
# #                     activityTypeIds.append(str(activityTypeArray[i]['id']))
# 
#         if existingIntegration is not None:
#             activityTypeArray = existingIntegration.integrations['mkto']['metadata']['activity']
#             for i in range(len(activityTypeArray)):
#                 activityTypeIds.append(str(activityTypeArray[i]['id']))
# 
#         if activityTypeIds is None:
#             return []
        
        activityTypeIds = ['12'] #hard coded Mkto Activity Type for 'New Lead'
        activityTypeArray = [] # redundant - should be removed later
        
        if sinceDateTime is None:
            sinceDateTime = datetime.now() - timedelta(days=30) #change to 365
        mkto = Marketo(company_id)

        batch_size = 10  #10 Activity Types at a time
        activityList = []
        for i in range(0, len(activityTypeIds), batch_size):
            activityTypeIdsTemp =  activityTypeIds[i:i+batch_size]
            print 'gettng activities for ' + str(activityTypeIdsTemp)
            activityList.extend(mkto.get_lead_activity(activityTypeIdsTemp, sinceDatetime=sinceDateTime))
        
        print 'going to save mkto lead created activities - count ' + str(len(activityList))
        saveMktoActivities(user_id=user_id, company_id=company_id, activityList=activityList, activityTypeArray=activityTypeArray, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Lead Created Activities retrieved from Marketo'
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
        
        #get the 'Claritix Lead List' in order to only get activities for leads in that list
        listList = mkto.get_lists(id=None , name=['Claritix Leads List'], programName=None, workspaceName=None, batchSize=None)
        if listList and listList[0]:
            leadListId = listList[0]['id']
        else:
            raise ValueError('Claritix Leads List not found')
        

        batch_size = 10  #10 Activity Types at a time
        activityList = []
        for i in range(0, len(activityTypeIds), batch_size):
            activityTypeIdsTemp =  activityTypeIds[i:i+batch_size]
            print 'gettng activities for ' + str(activityTypeIdsTemp)
            activityList.extend(mkto.get_lead_activity(activityTypeIdsTemp, sinceDatetime=sinceDateTime, leadListId=leadListId))
        
        
        #delete leads from lead list in Marketo
        deleteList = mkto.get_leads_by_listId(listId=leadListId)
        deleteLeadIds = [str(e['id']) for e in deleteList]
        print 'leads to be removed from CX List are ' + str(deleteLeadIds)
        batch_size = 300
        for i in range(0, len(deleteLeadIds), batch_size):
            mkto.remove_leads_from_list(listId=leadListId, leadsIds = deleteLeadIds[i:i+batch_size])
            print 'leads removed from Mkto CX List'
            
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
        print 'Error while retrieving activities from Marketo ' + str(e)
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
def retrieveSfdcLeadHistory(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None): #needs to be changed - satya
    try:
        #delete later
        #job_id_new = job_id
        #job_id = ObjectId("56a690e98afb006883048e7e")

        #set variables
        sfdc = Salesforce()
        
        #for leads
        if run_type == 'initial':
            leads = TempData.objects(Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            leads = TempDataDelta.objects(Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        leadListTemp = list(leads)
        if not leadListTemp:
            print 'no leads found'
            return
        leadList = [i['source_record'] for i in leadListTemp]
        
        
        
        batch_size = 500  #10 Activity Types at a time
        activitiesList = []
        
        for i in range(0, len(leadList), batch_size):
            lead_list = '('
            for lead in leadList[i:i+batch_size]:
                lead_list += '\'' + lead['Id'] + '\'' + ', '
            lead_list = lead_list[:-2]
            lead_list += ')'
            activitiesList.extend(sfdc.get_history_for_lead(user_id, company_id, lead_list, _str_from_date(sinceDateTime)))
        
        print 'got back history for SFDC leads ' + str(len(activitiesList))
        #delete later
        #job_id = job_id_new
        saveSfdcLeadHistory(user_id=user_id, company_id=company_id, activityList=activitiesList, job_id=job_id, run_type=run_type)
        
#         #for contacts
#         if run_type == 'initial':
#             contacts = TempData.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
#         else:
#             contacts = TempDataDelta.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
#             
#         contactListTemp = list(contacts)
#         contactList = [i['source_record'] for i in contactListTemp]
#         
#         sfdc = Salesforce()
#         
#         batch_size = 500  #10 Activity Types at a time
#         activitiesList = []
#         
#         for i in range(0, len(contactList), batch_size):
#             contact_list = '('
#             for contact in contactList[i:i+batch_size]:
#                 contact_list += '\'' + contact['Id'] + '\'' + ', '
#             contact_list = contact_list[:-2]
#             contact_list += ')'
#             activitiesList.extend(sfdc.get_history_for_contact(user_id, company_id, contact_list, _str_from_date(sinceDateTime)))
# 
#         print 'got back history for SFDC contacts ' + str(len(activitiesList))
#         saveSfdcHistory(user_id=user_id, company_id=company_id, activityList=activitiesList, job_id=job_id, run_type=run_type)
#         
        
        try:
            message = 'Lead history retrieved from Salesforce'
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
        print 'exception while retrieving SFDC lead history: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))   
        
@app.task    
def retrieveSfdcContactHistory(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None): #needs to be changed - satya
    try:
        #delete later
        #job_id_new = job_id
        #job_id = ObjectId("56a690e98afb006883048e7e")

        #set variables
        sfdc = Salesforce()
        #for leads
        if run_type == 'initial':
            contacts = TempData.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            contacts = TempDataDelta.objects(Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        contactListTemp = list(contacts)
        if not contactListTemp:
            print 'no contacts found'
            return
        contactList = [i['source_record'] for i in contactListTemp]
 
        batch_size = 500  #10 Activity Types at a time
        activitiesList = []
        
        for i in range(0, len(contactList), batch_size):
            contact_list = '('
            for lead in contactList[i:i+batch_size]:
                contact_list += '\'' + lead['Id'] + '\'' + ', '
            contact_list = contact_list[:-2]
            contact_list += ')'
            activitiesList.extend(sfdc.get_history_for_contact(user_id, company_id, contact_list, _str_from_date(sinceDateTime)))
        
        print 'got back history for SFDC contacts ' + str(len(activitiesList))
        #delete later
        #job_id = job_id_new
        saveSfdcContactHistory(user_id=user_id, company_id=company_id, activityList=activitiesList, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Contact history retrieved from Salesforce'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Contacts'
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
        return contactList
    except Exception as e:
        print 'exception while retrieving SFDC contact history: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))          
# @app.task    
# def retrieveSfdcActivities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None): #needs to be changed - satya
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
#         activitiesList = sfdc.get_activities_for_lead_delta(user_id, company_id, lead_list, _str_from_date(sinceDateTime))
#         print 'got back activities for leads ' + str(len(activitiesList))
#         saveSfdcActivities(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id, run_type=run_type)
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
#         activitiesList = sfdc.get_activities_for_contact_delta(user_id, company_id, contact_list, _str_from_date(sinceDateTime))
#         print 'got back activities for contacts ' + str(len(activitiesList))
#         saveSfdcActivities(user_id=user_id, company_id=company_id, activitiesList=activitiesList, job_id=job_id, run_type=run_type)
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
def retrieveSfdcOppHistory(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None): #needs to be changed - satya
    try:
        #delete later
        #job_id_new = job_id
        #job_id = ObjectId("56a690e98afb006883048e7e")

        #set variables
        sfdc = Salesforce()
        #for leads
        if run_type == 'initial':
            opps = TempData.objects(Q(record_type='opportunity') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            opps = TempDataDelta.objects(Q(record_type='opportunity') & Q(source_system='sfdc') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        oppListTemp = list(opps)
        if not oppListTemp:
            print 'no opps found'
            return
        oppList = [i['source_record'] for i in oppListTemp]
 
        batch_size = 500  #10 Activity Types at a time
        activitiesList = []
        
        for i in range(0, len(oppList), batch_size):
            opp_list = '('
            for opp in oppList[i:i+batch_size]:
                opp_list += '\'' + opp['Id'] + '\'' + ', '
            opp_list = opp_list[:-2]
            opp_list += ')'
            activitiesList.extend(sfdc.get_history_for_opportunity(user_id, company_id, opp_list, _str_from_date(sinceDateTime)))
        
        print 'got back history for SFDC opportunities ' + str(len(activitiesList))
        #delete later
        #job_id = job_id_new
        saveSfdcOppHistory(user_id=user_id, company_id=company_id, activityList=activitiesList, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Opportunity history retrieved from Salesforce'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Opportunities'
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
        return opp_list
    except Exception as e:
        print 'exception while retrieving SFDC opportunity history: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))   
        
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
    #job_id = ObjectId("56a2dd408afb006f9e7cb851") 
    
    
    if run_type == 'initial':   
        #activities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
        collection = TempData._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'activity', 'source_system': 'mkto', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    else:
        collection = TempDataDelta._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'activity', 'source_system': 'mkto', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
        #activities = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
    
    
#     activityListTemp = list(activities)
#     activityList = [i['source_record'] for i in activityListTemp]
    
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
        
        for activity in activities: 
            
            newActivity = activity['source_record']
            addThisActivity = True
            
            #company_id = request.user.company_id
            mkto_id = str(newActivity['leadId'])
            print 'doing lead ' + mkto_id
            
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
                    newStatus = ''
                    oldStatus = ''
                    for attribute in newActivity['attributes']:
                        if attribute['name'] == 'New Value':
                            newStatus = attribute['value']
                        elif attribute['name'] == 'Old Value':
                            oldStatus = attribute['value']
#                         elif attribute['name'] == 'Reason':
#                             reason = attribute['value']    
                            #break
                    #statusRecord.append({'status': newStatus, 'date': newActivity['activityDate']})
                    newActivity['newStatus'] = newStatus 
                    newActivity['oldStatus'] = oldStatus 
                    newActivity['date'] = newActivity['activityDate']
                    if 'mkto' in existingLead.statuses:
                        currentStatuses = existingLead.statuses['mkto']
                        currentStatuses.append(newActivity) # changed on 1/22/2016 {'status': newStatus, 'date': newActivity['activityDate']})
                        existingLead.update(statuses__mkto = currentStatuses)
                    else:
                        currentStatuses = []
                        currentStatuses.append(newActivity) # changed on 1/22/2016{'status': newStatus, 'date': newActivity['activityDate']})
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
    
# def saveSfdcActivities(user_id=None, company_id=None, activityList=None, job_id=None, run_type=None):    
#     print 'saving sfdc activities for leads'
#     if run_type == 'initial':
#         for activity in activityList:
#             saveTempData(company_id=company_id, record_type="activity", source_system="sfdc", source_record=activity, job_id=job_id)
#     else:
#         for activity in activityList:
#             saveTempDataDelta(company_id=company_id, record_type="activity", source_system="sfdc", source_record=activity, job_id=job_id)
#     

def saveSfdcLeadHistory(user_id=None, company_id=None, activityList=None, job_id=None, run_type=None):    
    print 'saving sfdc activities for leads and contacts'
    if run_type == 'initial':
        for activity in activityList:
            saveTempData(company_id=company_id, record_type="lead_history", source_system="sfdc", source_record=activity, job_id=job_id)
    else:
        for activity in activityList:
            saveTempDataDelta(company_id=company_id, record_type="lead_history", source_system="sfdc", source_record=activity, job_id=job_id)
    

def saveSfdcLeadHistoryToMaster(user_id=None, company_id=None, job_id=None, run_type=None): 
    #job_id = ObjectId("56a6faa28afb00042171cd89")

    if run_type == 'initial':   
        #activities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
        collection = TempData._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'lead_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    else:
        collection = TempDataDelta._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'lead_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
    
    try:
        print 'got history ' + str(activities.count())
        for activity in activities: 
                
            newActivity = activity['source_record']
            addThisActivity = True
            print 'act is ' + str(newActivity)
            leadId = newActivity["LeadId"]
            if leadId is not None:
                print 'trying to get lead'
                existingLead = Lead.objects(Q(company_id = company_id) & Q(sfdc_id = leadId)).first()
                print 'lead is ' + str(existingLead)
            else:
                continue
            if existingLead is None:
                continue
            
            if 'sfdc' in existingLead['activities']: # there are activities from SFDC for this leadId
                for existingActivity in existingLead['activities']['sfdc']:
                    if existingActivity['Id'] == newActivity['Id']: # this activity already exists so exit the loop
                        addThisActivity = False
                        break
                if addThisActivity:
                    existingLead['activities']['sfdc'].append(newActivity)
                    existingLead.save()
                    print 'saved new activity 1'
            else:
                print 'no sfdc acts'
                addThisActivity = True
                sfdc = []
                print 'appending'
                sfdc.append(newActivity)
                print 'appended'
                existingLead['activities']['sfdc'] = sfdc
                existingLead.save()
                print 'saved new activity 2'

    except Exception as e:
        print 'exception  while saving SFDC Lead history to master' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))         
        
def saveSfdcContactHistory(user_id=None, company_id=None, activityList=None, job_id=None, run_type=None):    
    print 'saving sfdc history for contacts'
    if run_type == 'initial':
        for activity in activityList:
            saveTempData(company_id=company_id, record_type="contact_history", source_system="sfdc", source_record=activity, job_id=job_id)
    else:
        for activity in activityList:
            saveTempDataDelta(company_id=company_id, record_type="contact_history", source_system="sfdc", source_record=activity, job_id=job_id)
    

def saveSfdcContactHistoryToMaster(user_id=None, company_id=None, job_id=None, run_type=None): 
    #job_id = ObjectId("56a6faa28afb00042171cd89")

    if run_type == 'initial':   
        #activities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
        collection = TempData._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'contact_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    else:
        collection = TempDataDelta._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'contact_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
    
    try:
        print 'got history ' + str(activities.count())
        for activity in activities: 
                
            newActivity = activity['source_record']
            addThisActivity = True
            print 'act is ' + str(newActivity)
            leadId = newActivity["ContactId"]
            if leadId is not None:
                print 'trying to get lead'
                existingLead = Lead.objects(Q(company_id = company_id) & Q(sfdc_contact_id = leadId)).first()
                print 'contact is ' + str(existingLead)
            else:
                continue
            if existingLead is None:
                continue
            
            if 'sfdc' in existingLead['activities']: # there are activities from SFDC for this leadId
                for existingActivity in existingLead['activities']['sfdc']:
                    if existingActivity['Id'] == newActivity['Id']: # this activity already exists so exit the loop
                        addThisActivity = False
                        break
                if addThisActivity:
                    existingLead['activities']['sfdc'].append(newActivity)
                    existingLead.save()
                    print 'saved new activity 1'
            else:
                print 'no sfdc acts'
                addThisActivity = True
                sfdc = []
                print 'appending'
                sfdc.append(newActivity)
                print 'appended'
                existingLead['activities']['sfdc'] = sfdc
                existingLead.save()
                print 'saved new activity 2'

    except Exception as e:
        print 'exception  while saving SFDC Contact history to master' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))             
        
def saveSfdcOppHistory(user_id=None, company_id=None, activityList=None, job_id=None, run_type=None):    
    print 'saving sfdc history for opportunities'
    if run_type == 'initial':
        for activity in activityList:
            saveTempData(company_id=company_id, record_type="opp_history", source_system="sfdc", source_record=activity, job_id=job_id)
    else:
        for activity in activityList:
            saveTempDataDelta(company_id=company_id, record_type="opp_history", source_system="sfdc", source_record=activity, job_id=job_id)
    

def saveSfdcOppHistoryToMaster(user_id=None, company_id=None, job_id=None, run_type=None): 
    #job_id = ObjectId("56b2b92c8afb0070a795c4b2")

    if run_type == 'initial':   
        #activities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') 
        collection = TempData._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'opp_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    else:
        collection = TempDataDelta._get_collection()
        activities = collection.find({'company_id': int(company_id), 'record_type': 'opp_history', 'source_system': 'sfdc', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
    
    try:
        print 'got history ' + str(activities.count())
        for activity in activities: 
            skipThis = False
            newActivity = activity['source_record']
            addThisActivity = True
            print 'act is ' + str(newActivity)
            newOppId = newActivity["OpportunityId"]
            if newOppId is not None:
                print 'trying to get opp'
                existingAccount = Account.objects(Q(company_id = company_id) & Q(opportunities__sfdc__Id = newOppId)).first()
                print 'account is ' + str(existingAccount)
            else:
                continue
            if existingAccount is None:
                continue
            
            for existingOpp in existingAccount['opportunities']['sfdc']: #loop through each opp to find the right one
                if existingOpp['Id'] == newOppId:
                    if 'activities' not in existingOpp: #if no prior activities
                        existingOpp['activities'] = [] #create list
                        existingOpp['activities'].append(newActivity) #save activity
                        print 'saved virgin activity for opp'
                    else:
                        for existingActivity in existingOpp['activities']: #check if this activity already exists
                            if existingActivity['Id'] == newActivity['Id']: #it exists, so skip the activity
                                skipThis = True
                                print 'skipping opp activity'
                                break
                        if skipThis:
                            break # get out of this for loop
                        else:
                            existingOpp['activities'].append(newActivity)
                            print 'saved activity for opp'
                    existingAccount.save()
                            
            

    except Exception as e:
        print 'exception while saving SFDC Opp history to master' + str(e)
        send_notification(dict(
         type='error',
         success=False,
         message=str(e)
        ))                     