from __future__ import absolute_import
import os
import datetime, json, time
from datetime import timedelta, date, datetime
import pytz
from pprint import pprint
from celery import shared_task
from mmm.celery import app
from bson.objectid import ObjectId

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from django.utils.encoding import smart_str

from integrations.views import Marketo, Salesforce, Hubspot, Google, Sugar, Pardot  # , get_sfdc_test
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
from itertools import izip_longest
from operator import itemgetter

@app.task
def retrieveMktoLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        leadList = []
        mkto = Marketo(company_id)
#         listList = mkto.get_lists(id=None , name=None, programName=None, workspaceName=None, batchSize=None)
#         if listList:
#             for i in range(len(listList)):
#                 results = mkto.get_leads_by_listId(listId=listList[i]['id'])
#                 #print "got back leads from Mkto list: " + str(listList[i]['name']) + " :" + str(len(results))
#                 leadList.extend(results)
#                 print 'going to save Mkto Leads ' + str(len(results))
#                 saveMktoLeads(user_id=user_id, company_id=company_id, leadList=leadList, newList=listList[i], job_id=job_id)
        #mkto = Marketo(company_id)
        #results = mkto.get_leads_by_changes_today(current_date_string)
        #allActivities = retrieveMktoActivities(user_id, company_id) #all activties in the last 24 hours
        
        #delete later
        #job_id = ObjectId("569d26008afb0063430a7818")
        if run_type == 'initial':
            allActivities = TempData.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            allActivities = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        #print "got back Mkto activities: " + str(len(allActivities)) 
        leadIds = [str(e['source_record']['leadId']) for e in allActivities]
        leadIds = list(set(leadIds))
        batch_size = 100  #100 Lead IDs at a time
        leadList = []
        for i in range(0, len(leadIds), batch_size):
            leadIdsTemp =  leadIds[i:i+batch_size]
            leadList.extend(mkto.get_leads_by_changes(leadIdsTemp))
            print "got back leads from Mkto: " + str(len(leadList)) 
        #leadList = mkto.get_leads_by_changes(leadIds) - this bombs because of too many IDs being passed
        
        #save the leads to the temp collection
        saveMktoLeads(user_id=user_id, company_id=company_id, leadList=leadList, newList=None, job_id=job_id, run_type=run_type)
        
        #save these leads to the 'Claritix Leads List' list for retrieving activities later
        batch_size = 300 #can add 300 leads to the list at a time
        leadList = []
        listList = mkto.get_lists(id=None , name=['Claritix Leads List'], programName=None, workspaceName=None, batchSize=None)
        if listList and listList[0]:
            for i in range(0, len(leadIds), batch_size):
                results = mkto.save_leads_to_list(listId=listList[0]['id'], leadsIds = leadIds[i:i+batch_size])
                print 'Mkto return is ' + str(results)
        else:
            raise ValueError('Claritix Leads List not found')
                
        
        try:
            message = 'Leads retrieved from Marketo'
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
        print 'Error while retrieving leads from Marketo ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))       
        
@app.task
def retrieveMktoLeadsByProgram(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        leadList = []
        mkto = Marketo(company_id)
        
        if run_type == 'initial':
            allCampaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            allCampaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        #print "got back Mkto activities: " + str(len(allActivities)) 
        programIds = [str(e['source_record']['id']) for e in allCampaigns if e['source_record']['createdAt'] >= _str_from_date(sinceDateTime, 'with_zeros')] #or e['source_record']['updatedAt'] >= _str_from_date(sinceDateTime, 'with_zeros')
        programIds = list(set(programIds))
        print 'found programs after start date ' + str(len(programIds))
        #batch_size = 300  #100 Lead IDs at a time
        leadList = []
        for programId in programIds:
            temp_leads = mkto.get_leads_by_programId(programId)
            for lead in temp_leads:
                if 'membership' in lead:
                    lead['membership']['program_id'] = programId
            leadList.extend(temp_leads)
            print "got back leads from Mkto: " + str(len(leadList)) 
        #leadList = mkto.get_leads_by_changes(leadIds) - this bombs because of too many IDs being passed
        
        #save the leads to the temp collection
        saveMktoLeadsByProgram(user_id=user_id, company_id=company_id, leadList=leadList, newList=None, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Leads retrieved from Marketo programs'
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
        print 'Error while retrieving leads from Marketo programs ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         
  
@app.task    
def retrievePrdtLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        prdt = Pardot(company_id)
        leadList = prdt.get_leads_by_changes(_str_from_date(sinceDateTime))
        #save the leads to the temp collection
        savePrdtLeads(user_id=user_id, company_id=company_id, leadList=leadList, newList=None, job_id=job_id, run_type=run_type)
        print 'pardot leads ' + str(leadList)
    except Exception as e:
        print 'Error while retrieving prospects from Pardot ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))   


@app.task    
def retrieveSfdcLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        sdfc = Salesforce()
        if sinceDateTime is None:
            sinceDateTime = (datetime.now() - timedelta(days=1)).date()
        leadList = sdfc.get_leads_delta(user_id, company_id, _str_from_date(sinceDateTime), run_type)
        print 'got back leads ' + str(len(leadList['records']))
        saveSfdcLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
        try:
            message = 'Leads retrieved from Salesforce'
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
# def retrieveSfdcLeadsDaily(user_id=None, company_id=None, job_id=None, run_type=None): # for cron job
#     try:
#         sdfc = Salesforce()
#         sinceDateTime = (datetime.now() - timedelta(days=1)).date()
#         leadList = sdfc.get_leads_daily(user_id, company_id, _str_from_date(sinceDateTime))
#         print 'got back leads ' + str(len(leadList))
#         saveSfdcLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id)
#         try:
#             message = 'Leads retrieved from Salesforce'
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
#         
@app.task
def retrieveHsptLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        leadList = []
        hspt = Hubspot(company_id)
        if run_type == 'initial':
            print 'initial run for leads'
            try:
                for lead in hspt.get_all_contacts():
                    leadList.append(lead)
                    if len(leadList) == 100:
                        saveHsptLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
                        leadList = []
            except Exception as e:
                print 'exception: ' + str(e)
        else:
            try:
                for lead in hspt.get_recent_contacts(sinceDateTime):
                    leadList.append(lead)
                    if len(leadList) == 100:
                        saveHsptLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
                        leadList = []
            except Exception as e:
                print 'exception: ' + str(e)
#             leadList = hspt.get_recent_contacts(sinceDateTime)
#             saveHsptLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
        
        #print 'Leads got: ' + str(leadList[0])
        
        #saveHsptLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
        
        try:
            message = 'Leads retrieved from Hubspot'
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
        
   
@app.task    
def retrieveSugrLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    if run_type == 'initial':
        print 'initial run for leads'
        try:
            sugr = Sugar(company_id)
            leadList = sugr.get_leads()
            print 'lead list is ' + str(leadList)
            saveSugrLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
        except Exception as e:
            print 'error while retrieving leads from SugarCRM: ' + str(e)
            send_notification(dict(type='error', success=False, message=str(e))) 
#save the data in the temp table
def saveMktoLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    try:
        print 'saving Mkto Leads'
        if run_type == 'initial':
            for lead in leadList:
                saveTempData(company_id=company_id, record_type="lead", source_system="mkto", source_record=lead, job_id=job_id)
        else:
            for lead in leadList:
                saveTempDataDelta(company_id=company_id, record_type="lead", source_system="mkto", source_record=lead, job_id=job_id)
                
    except Exception as e:
        print 'error while saving Mkto leads to temp ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))   
        
def saveMktoLeadsByProgram(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    try:
        print 'saving Mkto Leads from programs'
        if run_type == 'initial':
            for lead in leadList:
                saveTempData(company_id=company_id, record_type="lead_by_program", source_system="mkto", source_record=lead, job_id=job_id)
        else:
            for lead in leadList:
                saveTempDataDelta(company_id=company_id, record_type="lead_by_program", source_system="mkto", source_record=lead, job_id=job_id)
                
    except Exception as e:
        print 'error while saving Mkto leads from program to temp ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))  


#     for list in newList:
#         saveTempData(company_id=company_id, record_type="list", source_system="mkto", source_record=list, job_id=job_id)


def saveMktoLeadsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #delete later
    #job_id = ObjectId("569d26008afb0063430a7818")
    
    if run_type == 'initial':
        leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    leadListTemp = list(leads)
    leadList = [i['source_record'] for i in leadListTemp]
   
    try: 
        for newLead in leadList: 
            # company_id = request.user.company_id
            mkto_id = str(newLead['id']) 
            print 'mkto id is ' + mkto_id
            mkto_sfdc_id = ''
            mkto_sfdc_contact_id = ''
            if 'sfdcLeadId' in newLead:
                mkto_sfdc_id = newLead['sfdcLeadId']  # check if there is a corresponding lead from SFDC
            if 'sfdcContactId' in newLead:
                mkto_sfdc_contact_id = newLead['sfdcContactId']  # check if there is a corresponding contact from SFDC
            created_date = _date_from_str(newLead['createdAt'])
            addThisList = True
            existingLeadSfdc = None
            existingContactSfdc = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(mkto_id=mkto_id)).first()
            
            if existingLead is not None and 'mkto' in existingLead.leads:  # we found this lead already in the DB
                existingLead.source_first_name = newLead['firstName']
                existingLead.source_last_name = newLead['lastName']
                existingLead.source_email = newLead['email']
                existingLead.source_company = newLead['company']
                #existingLead.source_created_date = created_date
                existingLead.source_status = newLead['leadStatus']
                existingLead.source_stage = newLead['leadRevenueStageId']
                #existingLead.source_source = newLead['leadSource']
                existingLead.sfdc_account_id = newLead.get('sfdcAccountId', None)
                existingLead.leads["mkto"] = newLead
                existingLead.save()
                
                #Lead.objects(Q(company_id=company_id) & Q(mkto_id=mkto_id)).update(leads__mkto=newLead)
#                 if newList is not None:
#                     if 'mkto' in existingLead.lists:
#                         currentLists = existingLead.lists['mkto']        
#                         for i in range(len(currentLists)):
#                             if currentLists[i]['id'] == newList['id']:  # check if this activity already exists in the lead dict
#                                 addThisList = False
#                         if addThisList == True:
#                             currentLists.append(newList)
#                             existingLead.update(lists__mkto=currentLists)
#                         else:
#                             currentLists = []
#                             currentLists.append(newList)
#                             existingLead.update(lists__mkto=currentLists)
                
            elif existingLead is None:  # this lead does not exist 
                
                if mkto_sfdc_contact_id is not None: # but has a SFDC contact id
                    existingContactSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=mkto_sfdc_contact_id)).first()
                    if existingContactSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingContactSfdc.mkto_id = mkto_id
                        existingContactSfdc.leads['mkto'] = newLead
                        existingContactSfdc.sfdc_account_id = newLead.get('ConvertedAccountId', None)
                        existingContactSfdc.save()
            
                
                elif mkto_sfdc_id is not None:  # but has a SFDC lead id
                    existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_id=mkto_sfdc_id)).first()
                    if existingLeadSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingLeadSfdc.mkto_id = mkto_id
                        existingLeadSfdc.leads['mkto'] = newLead
                        existingLeadSfdc.sfdc_account_id = newLead.get('ConvertedAccountId', None)
                        existingLeadSfdc.save()
#                         if newList is not None:
#                             currentLists = []
#                             currentLists.append(newList)
#                             existingLeadSfdc.update(lists__mkto=currentLists)
                
            if existingLeadSfdc is None and existingContactSfdc is None and existingLead is None:  # no matches found so save new record
                lead = Lead()
                lead.mkto_id = mkto_id
                lead.company_id = company_id
                lead.source_first_name = newLead['firstName']
                lead.source_last_name = newLead['lastName']
                lead.source_email = newLead['email']
                lead.source_company = newLead['company']
                lead.source_created_date = created_date
                lead.source_status = newLead['leadStatus']
                lead.source_stage = newLead['leadRevenueStageId']
                lead.source_source = newLead['leadSource']
                lead.sfdc_account_id =  newLead.get('sfdcAccountId', None)
                lead.leads["mkto"] = newLead
                lead.save()
#                 if newList is not None:
#                     currentLists = []
#                     currentLists.append(newList)
#                     lead.update(lists__mkto=currentLists)
                
    except Exception as e:
        print 'error while saving Mkto leads to master ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         

def saveMktoLeadsByProgramToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #delete later
    #job_id = ObjectId("56d399ddf6fd2a7976ac264e")
    
    if run_type == 'initial':
        leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead_by_program') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead_by_program') & Q(source_system='mkto') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    leadListTemp = list(leads)
    leadList = [i['source_record'] for i in leadListTemp]
   
    try: 
        for newLead in leadList: 
            # company_id = request.user.company_id
            mkto_id = str(newLead['id']) 
            print 'mkto id is ' + mkto_id
            mkto_sfdc_id = ''
            mkto_sfdc_contact_id = ''
            if 'sfdcLeadId' in newLead:
                mkto_sfdc_id = newLead['sfdcLeadId']  # check if there is a corresponding lead from SFDC
            if 'sfdcContactId' in newLead:
                mkto_sfdc_contact_id = newLead['sfdcContactId']  # check if there is a corresponding contact from SFDC
            created_date = _date_from_str(newLead['createdAt'])
            
            existingLeadSfdc = None
            existingContactSfdc = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(mkto_id=mkto_id)).first()
            
            if existingLead is not None: # and 'mkto' in existingLead.leads:  # we found this lead already in the DB
                existingLead = _add_membership(existingLead, newLead)
                

            elif existingLead is None:  # this lead does not exist 
                
                if mkto_sfdc_contact_id is not None: # but has a SFDC contact id
                    existingContactSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=mkto_sfdc_contact_id)).first()
                    if existingContactSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingContactSfdc = _add_membership(existingContactSfdc, newLead) 
            
                
                elif mkto_sfdc_id is not None:  # but has a SFDC lead id
                    existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_id=mkto_sfdc_id)).first()
                    if existingLeadSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingLeadSfdc = _add_membership(existingLeadSfdc, newLead) 
#                         if newList is not None:
#                             currentLists = []
#                             currentLists.append(newList)
#                             existingLeadSfdc.update(lists__mkto=currentLists)
                
            if existingLeadSfdc is None and existingContactSfdc is None and existingLead is None:  # no matches found so save new record
                lead = Lead()
                lead.mkto_id = mkto_id
                lead.company_id = company_id
                lead.source_first_name = newLead['firstName']
                lead.source_last_name = newLead['lastName']
                lead.source_email = newLead['email']
                lead.source_company = newLead['company']
                lead.source_created_date = created_date
                lead.source_status = newLead['leadStatus']
                lead.source_stage = newLead['leadRevenueStageId']
                lead.source_source = newLead['leadSource']
                lead.sfdc_account_id =  newLead.get('sfdcAccountId', None)
                lead.leads["mkto"] = newLead
                lead.memberships["mkto"] = []
                lead.memberships["mkto"].append(newLead['membership'])
                del lead.leads["mkto"]['membership']
                lead.save()
                print 'new new'
#                 if newList is not None:
#                     currentLists = []
#                     currentLists.append(newList)
#                     lead.update(lists__mkto=currentLists)
                
    except Exception as e:
        print 'error while saving Mkto membership to master ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         

def _add_membership(existingLead, newLead):
    try:
#         if not 'memberships' in existingLead:
#             existingLead['memberships'] = {}
#             existingLead.save()
        #print 'existing lead is ' + str(existingLead)
        if 'mkto' not in existingLead.memberships:
            currentMemberships = []
            currentMemberships.append(newLead['membership'])
            print 'new 1'
            existingLead.update(memberships__mkto = currentMemberships)
            print 'new 2'
        else:
            print 'old 1'
            membershipFound = False
            for membership in existingLead['memberships']['mkto']:
                if membership['program_id'] == newLead['membership']['program_id'] and membership['progressionStatus'] == newLead['membership']['progressionStatus']:
                    membershipFound = True
                    break
            if not membershipFound:
                existingLead['memberships']['mkto'].append(newLead['membership'])
                existingLead.save()
                print 'old 2'
        return existingLead
    except Exception as e:
        print 'error in sub while saving Mkto lead membership to master ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))    
        
#save the data in the temp table
def saveSfdcLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    if run_type == 'initial':
        for lead in leadList['records']:
            saveTempData(company_id=company_id, record_type="lead", source_system="sfdc", source_record=lead, job_id=job_id)
    else:
        for lead in leadList['records']:
            saveTempDataDelta(company_id=company_id, record_type="lead", source_system="sfdc", source_record=lead, job_id=job_id)
    
def saveSfdcLeadsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #job_id = ObjectId("55e89c348afb00347b3e4bd1")
    
    if run_type == 'initial':
        leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    leadListTemp = list(leads)
    leadList = [i['source_record'] for i in leadListTemp]
    
#     mkto_sync_user = None
#     existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
#     if 'sfdc' in existingIntegration['integrations']:
#         try:
#             marketo_sync_user = existingIntegration['integrations']['mapping']['mkto_sync_user']
#         except Exception as e:
#             print 'Marketo Sync User not defined in SFDC integration'
            
    
    try: 
        for newLead in leadList: #['records']:

            # company_id = request.user.company_id
            sfdc_Id = str(newLead['Id']) 
            print 'got sfdc lead with id ' + sfdc_Id
            sfdc_contact_id = None
            sfdc_account_id = None
            if 'ConvertedContactId' in newLead and newLead['ConvertedContactId'] is not None:
                sfdc_contact_id = newLead['ConvertedContactId']
                print 'found converted contact with id' + str(sfdc_contact_id)
            if 'ConvertedAccountId' in newLead and newLead['ConvertedAccountId'] is not None:
                sfdc_account_id = newLead['ConvertedAccountId']
            # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
            existingLeadMkto = None
            existingLeadHspt = None
            existingContactSfdc = None #to search for converted contacts
            existingContactHspt = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(sfdc_id=sfdc_Id)).first()
            
            if existingLead is not None:  # we found this lead already in the DB
                if  'sfdc' in existingLead.leads:
                    existingLead.source_first_name = newLead['FirstName']
                    existingLead.source_last_name = newLead['LastName']
                    existingLead.source_email = newLead['Email']
                    #existingLead.source_created_date = newLead['CreatedDate']
                    existingLead.source_source = newLead['LeadSource']
                    existingLead.source_status = newLead['Status']
                    existingLead.sfdc_account_id = sfdc_account_id
                    existingLead.leads['sfdc'] = newLead
                    #print 'first save'
                    existingLead.save()
                    
                    #Lead.objects(Q(company_id=company_id) & Q(sfdc_id=sfdc_Id)).update(leads__sfdc=newLead)
                else:
                    existingLead.leads['sfdc'] = {}
                    #existingLead.sfdc_account_id = sfdc_account_id
                    existingLead.leads['sfdc'] = newLead
                    existingLead.source_first_name = newLead['FirstName']
                    existingLead.source_last_name = newLead['LastName']
                    existingLead.source_email = newLead['Email']
                    #existingLead.source_created_date = newLead['CreatedDate']
                    existingLead.source_source = newLead['LeadSource']
                    existingLead.source_status = newLead['Status']
                    existingLead.sfdc_account_id = sfdc_account_id
                    #print '2nd save'
                    existingLead.save()
                    
            elif existingLead is None:  # this lead does not exist 
                existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcLeadId=sfdc_Id)).first()
                if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                    existingLeadMkto.sfdc_id = sfdc_Id
                    existingLeadMkto.sfdc_account_id = sfdc_account_id
                    existingLeadMkto.leads['sfdc'] = newLead
                    if existingLeadMkto.leads['mkto']['originalSourceType'] == 'salesforce.com': #this lead origniated from SFDC
                        existingLeadMkto.source_first_name = newLead['FirstName']
                        existingLeadMkto.source_last_name = newLead['LastName']
                        existingLeadMkto.source_email = newLead['Email']
                        #existingLeadMkto.source_created_date = newLead['CreatedDate']
                        existingLeadMkto.source_source = newLead['LeadSource']
                        existingLeadMkto.source_status = newLead['Status']
                        existingLeadMkto.sfdc_account_id = sfdc_account_id
                    #print '3rd save'
                    existingLeadMkto.save()
                    
                existingLeadHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforceleadid=sfdc_Id)).first()
                if existingLeadHspt is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                    existingLeadHspt.sfdc_id = sfdc_Id
                    existingLeadHspt.sfdc_account_id = sfdc_account_id
                    existingLeadHspt.leads['sfdc'] = newLead
                    existingLeadHspt.save()
                elif sfdc_contact_id is not None:
                    existingContactSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_id)).first()
                    if existingContactSfdc is not None:  # we found a HSPT record which is matched to this new Sfdc lead which is converted to a contact
                        existingContactSfdc.sfdc_id = sfdc_Id
                        existingContactSfdc.sfdc_contact_id = sfdc_contact_id
                        existingContactSfdc.sfdc_account_id = sfdc_account_id
                        existingContactSfdc.leads['sfdc'] = newLead
                        #print '4th save'
                        existingContactSfdc.save()
                        
                    
                    existingContactHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforcecontactid=sfdc_contact_id)).first()
                    if existingContactHspt is not None:  # we found a HSPT record which is matched to this new Sfdc lead which is converted to a contact
                        existingContactHspt.sfdc_id = sfdc_Id
                        existingContactHspt.sfdc_contact_id = sfdc_contact_id
                        existingContactHspt.sfdc_account_id = sfdc_account_id
                        existingContactHspt.leads['sfdc'] = newLead
                        existingContactHspt.save()
                    
            if existingLeadMkto is None and existingLeadHspt is None and existingContactHspt is None and existingContactSfdc is None and existingLead is None:  # no matches found so save new record
                lead = Lead()
                lead.sfdc_id = sfdc_Id
                lead.company_id = company_id
                lead.source_first_name = newLead['FirstName']
                lead.source_last_name = newLead['LastName']
                lead.source_email = newLead['Email']
                lead.source_created_date = str(newLead['CreatedDate'])
                lead.source_source = newLead['LeadSource']
                lead.source_status = newLead['Status']
                lead.sfdc_account_id = sfdc_account_id
                lead.leads["sfdc"] = newLead
                #print '5th save'
                lead.save()
                
            # lead = Lead()
#             company_id = request.user.company_id
#             derived_id = 'sfdc_' + str(newLead['Id']) 
#             Lead.objects(derived_id = derived_id).modify(upsert=True, new=True, set__leads__sfdc = newLead, set_on_insert__derived_id = derived_id, set_on_insert__company_id = company_id)
#             
#             oldLead = Lead.objects(derived_id = lead.derived_id)
#             if oldLead.count() == 0:
#                 lead.leads["sfdc"] = newLead
#                 lead.save()
#             else:
#                 oldLead.leads["sfdc"] = newLead 
#                 Lead.objects(derived_id = lead.derived_id).update(oldLead)
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))         


#save the data in the temp table
def saveHsptLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    print 'saving Hspt Leads'
    if run_type == 'initial':
        for lead in leadList:
            saveTempData(company_id=company_id, record_type="lead", source_system="hspt", source_record=vars(lead)['_field_values'], job_id=job_id)
    else:
        for lead in leadList:
            saveTempDataDelta(company_id=company_id, record_type="lead", source_system="hspt", source_record=vars(lead)['_field_values'], job_id=job_id)


    
def saveHsptLeadsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #job_id = ObjectId("55e6b0198afb002ef6a8c292")
    if run_type == 'initial':
        collection = TempData._get_collection()
        leads = collection.find({'company_id': int(company_id), 'record_type': 'lead', 'source_system': 'hspt', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        #leads = collection.find({"company_id" : company_id, "record_type": "lead", "source_system":"hspt", "job_id": job_id}, projection={"source_record": True}, batch_size=100)
        #leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
    else:
        #leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
        collection = TempDataDelta._get_collection()
        leads = collection.find({'company_id': int(company_id), 'record_type': 'lead', 'source_system': 'hspt', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    #leadList = list(leads)
    #leadList = [i['source_record'] for i in leadList]
    
    try: 
        #for newLead in leadList: 
        numLeads = 0
        for lead in leads:
            numLeads = numLeads + 1
            print 'num leads is ' + str(numLeads)
            newLead = lead['source_record']
            #newLead = vars(newLead)['_field_values']
            hspt_id = str(newLead['vid']) 
            print 'hs id is ' + str(hspt_id)
            #hspt_sfdc_id = str(newLead['sfdcLeadId'])  # check if there is a corresponding lead from SFDC
            hspt_sfdc_id = None
            hspt_sfdc_contact_id = None
            hspt_subscriber_date = newLead['properties'].get('hs_lifecyclestage_subscriber_date', None)
            hspt_lead_date = newLead['properties'].get('hs_lifecyclestage_lead_date', None)
            hspt_mql_date = newLead['properties'].get('hs_lifecyclestage_marketingqualifiedlead_date', None)
            hspt_sql_date = newLead['properties'].get('hs_lifecyclestage_salesqualifiedlead_date', None)
            hspt_opp_date = newLead['properties'].get('hs_lifecyclestage_opportunity_date', None)
            hspt_customer_date = newLead['properties'].get('hs_lifecyclestage_customer_date', None)
            hspt_created_date = newLead['properties'].get('createdate', None)
            if hspt_created_date is None:
                hspt_created_date = newLead['properties'].get('hs_analytics_first_timestamp', None)
            if hspt_created_date is None:
                continue
            
            if 'salesforceleadid' in newLead['properties']:
                hspt_sfdc_id = str(newLead['properties']['salesforceleadid']) # temp fix by satya till SFDC ID field in Hubspot is discovered
            if 'salesforcecontactid' in newLead['properties']:
                hspt_sfdc_contact_id = str(newLead['properties']['salesforcecontactid']) # temp fix by satya till SFDC ID field in Hubspot is discovered
                print 'found SFDC contact with id ' + str(hspt_sfdc_contact_id)   
            
            #the below mappings are needed to prevent encoding errors
            hspt_first_name = smart_str(newLead['properties'].get('firstname', None))
            hspt_last_name = smart_str(newLead['properties'].get('lastname', None))
            hspt_email = smart_str(newLead.get('email_address', None))
            hspt_company = smart_str(newLead.get('company', None))
            hspt_analytics_source = smart_str(newLead['properties'].get('hs_analytics_source', None))
            #print 'fname is ' + hspt_first_name
            #print 'lanme is ' + hspt_last_name 
            #addThisList = True
            existingLeadSfdc = None
            existingContactSfdc = None
            existingLead = None
            #existingLead = Lead.objects(Q(company_id=company_id) & Q(hspt_id=hspt_id)).first()
            collection2 = Lead._get_collection()
            existingLead = collection2.find_one({'company_id': int(company_id), 'hspt_id': hspt_id})
            
            if existingLead is not None and 'hspt' in existingLead['leads']:  # we found this lead already in the DB
                existingLead['source_first_name'] = hspt_first_name
                existingLead['source_last_name'] = hspt_last_name
                existingLead['source_email'] = hspt_email
                existingLead['source_company'] = hspt_company
                existingLead['source_created_date'] = hspt_created_date
                existingLead['source_status'] = newLead['properties'].get('leadstatus', None)
                existingLead['source_stage'] = newLead['properties'].get('lifecyclestage', None)
                existingLead['source_source'] = hspt_analytics_source
                existingLead['hspt_subscriber_date'] = hspt_subscriber_date
                existingLead['hspt_lead_date'] = hspt_lead_date
                existingLead['hspt_mql_date'] = hspt_mql_date
                existingLead['hspt_sql_date'] = hspt_sql_date
                existingLead['hspt_opp_date'] = hspt_opp_date
                existingLead['hspt_customer_date'] = hspt_customer_date
                
                existingLead['leads']["hspt"] = newLead
                collection2.save(existingLead)
                #Lead.objects(Q(company_id=company_id) & Q(hspt_id=hspt_id)).update(leads__hspt=newLead)
#                 if 'hspt' in existingLead.lists:
#                     currentLists = existingLead.lists['mkto']        
#                     for i in range(len(currentLists)):
#                         if currentLists[i]['id'] == newList['id']:  # check if this activity already exists in the lead dict
#                             addThisList = False
#                     if addThisList == True:
#                         currentLists.append(newList)
#                         existingLead.update(lists__mkto=currentLists)
#                     else:
#                         currentLists = []
#                         currentLists.append(newList)
#                         existingLead.update(lists__mkto=currentLists)
                
            elif existingLead is None:  # this lead does not exist 
                if hspt_sfdc_id is not None:  # but has a SFDC lead id
                    #print 'found lead with SFDC ID ' + str(hspt_sfdc_id)
                    #existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(leads__sfdc__Id=hspt_sfdc_id)).first()
                    existingLeadSfdc = collection2.find_one({'company_id': int(company_id), 'leads.sfdc.Id': hspt_sfdc_id})
                    if existingLeadSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingLeadSfdc['hspt_id'] = hspt_id
                        existingLeadSfdc['leads']['hspt'] = newLead
                        existingLeadSfdc['hspt_subscriber_date'] = hspt_subscriber_date
                        existingLeadSfdc['hspt_lead_date'] = hspt_lead_date
                        existingLeadSfdc['hspt_mql_date'] = hspt_mql_date
                        existingLeadSfdc['hspt_sql_date'] = hspt_sql_date
                        existingLeadSfdc['hspt_opp_date'] = hspt_opp_date
                        existingLeadSfdc['hspt_customer_date'] = hspt_customer_date
                        collection2.save(existingLeadSfdc)
#                         currentLists = []
#                         currentLists.append(newList)
#                         existingLeadSfdc.update(lists__mkto=currentLists)
                elif hspt_sfdc_contact_id is not None:  # but has a SFDC contact id
                    print 'found contact with SFDC ID ' + str(hspt_sfdc_contact_id)
                    #existingContactSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=hspt_sfdc_contact_id)).first()
                    existingContactSfdc = collection2.find_one({'company_id': int(company_id), 'sfdc_contact_id': hspt_sfdc_contact_id})
                    if existingContactSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingContactSfdc['hspt_id'] = hspt_id
                        existingContactSfdc['leads']['hspt'] = newLead
                        existingContactSfdc['hspt_subscriber_date'] = hspt_subscriber_date
                        existingContactSfdc['hspt_lead_date'] = hspt_lead_date
                        existingContactSfdc['hspt_mql_date'] = hspt_mql_date
                        existingContactSfdc['hspt_sql_date'] = hspt_sql_date
                        existingContactSfdc['hspt_opp_date'] = hspt_opp_date
                        existingContactSfdc['hspt_customer_date'] = hspt_customer_date
                        collection2.save(existingContactSfdc)
#                         currentLists = []
#                         currentLists.append(newList)
#                         existingLeadSfdc.update(lists__mkto=currentLists)
            
            if existingLeadSfdc is None and existingContactSfdc is None and existingLead is None:  # no matches found so save new record
                print 'this is a new lead'
                lead = Lead()
                lead.hspt_id = hspt_id
                lead.company_id = company_id
                lead.source_first_name = hspt_first_name
                lead.source_last_name = hspt_last_name
                lead.source_email = hspt_email
                lead.source_company = hspt_company
                lead.source_created_date = hspt_created_date
                lead.source_status = newLead['properties'].get('leadstatus', None)
                lead.source_stage = newLead['properties'].get('lifecyclestage', None)
                lead.source_source = hspt_analytics_source
                lead.hspt_subscriber_date = hspt_subscriber_date
                lead.hspt_lead_date = hspt_lead_date
                lead.hspt_mql_date = hspt_mql_date
                lead.hspt_sql_date = hspt_sql_date
                lead.hspt_opp_date = hspt_opp_date
                lead.hspt_customer_date = hspt_customer_date
                lead.leads = {}
                lead.leads["hspt"] = newLead
                lead.save()
                
#                 lead = {}
#                 lead['hspt_id'] = hspt_id
#                 lead['company_id'] = company_id
#                 lead['source_first_name'] = hspt_first_name
#                 lead['source_last_name'] = hspt_last_name
#                 lead['source_email'] = hspt_email
#                 lead['source_company'] = hspt_company
#                 lead['source_created_date'] = hspt_created_date
#                 lead['source_status'] = newLead['properties'].get('leadstatus', None)
#                 lead['source_stage'] = newLead['properties'].get('lifecyclestage', None)
#                 lead['source_source'] = hspt_analytics_source
#                 lead['hspt_subscriber_date'] = hspt_subscriber_date
#                 lead['hspt_lead_date'] = hspt_lead_date
#                 lead['hspt_mql_date'] = hspt_mql_date
#                 lead['hspt_sql_date'] = hspt_sql_date
#                 lead['hspt_opp_date'] = hspt_opp_date
#                 lead['hspt_customer_date'] = hspt_customer_date
#                 lead['leads'] = {}
#                 lead['leads']["hspt"] = newLead
#                 collection2.save(lead)
#                 currentLists = []
#                 currentLists.append(newList)
#                 lead.update(lists__mkto=currentLists)
                
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))  
        
#save the data in the temp table
def saveSugrLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    print 'saving Sugr Leads'
    if run_type == 'initial':
        for lead in leadList:
            saveTempData(company_id=company_id, record_type="lead", source_system="sugr", source_record=lead, job_id=job_id)
    else:
        for lead in leadList:
            saveTempDataDelta(company_id=company_id, record_type="lead", source_system="sugr", source_record=lead, job_id=job_id)

def saveSugrLeadsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    #job_id = ObjectId("55e6b0198afb002ef6a8c292")
    if run_type == 'initial':
        collection = TempData._get_collection()
        leads = collection.find({'company_id': int(company_id), 'record_type': 'lead', 'source_system': 'sugr', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        #leads = collection.find({"company_id" : company_id, "record_type": "lead", "source_system":"hspt", "job_id": job_id}, projection={"source_record": True}, batch_size=100)
        #leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
    else:
        #leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
        collection = TempDataDelta._get_collection()
        leads = collection.find({'company_id': int(company_id), 'record_type': 'lead', 'source_system': 'sugr', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        
    try: 
        numLeads = 0
        for lead in leads:
            numLeads = numLeads + 1
            print 'num leads is ' + str(numLeads)
            newLead = lead['source_record']
            sugr_id = newLead['id']
            print 'got sugr lead with id ' + sugr_id
            sugr_contact_id = None
            sugr_account_id = None
            if 'account_id' in newLead and newLead['account_id']:
                sugr_account_id = newLead['account_id']
                print 'found converted account with id' + str(sugr_account_id)
            if 'contact_id' in newLead and newLead['contact_id']:
                sugr_contact_id = newLead['contact_id']
            lead_email = newLead.get('email1', None)
            # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
            existingLeadMkto = None
            existingLeadHspt = None
            existingContactSugr = None #to search for converted contacts
            existingContactHspt = None
            existingLeadEmail = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(sugr_id=sugr_id)).first()
            
            if existingLead is not None:  # we found this lead already in the DB
                if  'sugr' in existingLead.leads:
                    existingLead.source_first_name = newLead.get('first_name', None)
                    existingLead.source_last_name = newLead.get('last_name', None)
                    existingLead.source_email = lead_email
                    existingLead.source_created_date = newLead.get('date_entered', None)
                    existingLead.source_source = newLead.get('lead_source', None)
                    existingLead.source_status = newLead.get('status', None)
                    existingLead.sugr_account_id = sugr_account_id
                    existingLead.sugr_contact_id = sugr_contact_id
                    existingLead.leads['sugr'] = newLead
                    #print 'first save'
                    existingLead.save()
                    
                    #Lead.objects(Q(company_id=company_id) & Q(sfdc_id=sfdc_Id)).update(leads__sfdc=newLead)
                else:
                    existingLead.leads['sugr'] = {}
                    existingLead.sugr_account_id = sugr_account_id
                    existingLead.leads['sugr'] = newLead
                    #print '2nd save'
                    existingLead.save()
                    
            elif existingLead is None:  # this lead does not exist 
                if lead_email:
                    existingLeadEmail = Lead.objects(Q(company_id=company_id) & Q(source_email=lead_email)).first()
                    if existingLeadEmail is not None:
                        existingLeadEmail.leads['sugr'] = newLead
                        existingLeadEmail.save()
                    
#                 existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcLeadId=sfdc_Id)).first()
#                 if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
#                     existingLeadMkto.sfdc_id = sfdc_Id
#                     existingLeadMkto.sfdc_account_id = sfdc_account_id
#                     existingLeadMkto.leads['sfdc'] = newLead
#                     if existingLeadMkto.leads['mkto']['originalSourceType'] == 'salesforce.com': #this lead origniated from SFDC
#                         existingLeadMkto.source_first_name = newLead['FirstName']
#                         existingLeadMkto.source_last_name = newLead['LastName']
#                         existingLeadMkto.source_email = newLead['Email']
#                         existingLeadMkto.source_created_date = newLead['CreatedDate']
#                         existingLeadMkto.source_source = newLead['LeadSource']
#                         existingLeadMkto.source_status = newLead['Status']
#                         existingLeadMkto.sfdc_account_id = sfdc_account_id
#                     #print '3rd save'
#                     existingLeadMkto.save()
                    
#                 existingLeadHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforceleadid=sfdc_Id)).first()
#                 if existingLeadHspt is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
#                     existingLeadHspt.sfdc_id = sfdc_Id
#                     existingLeadHspt.sfdc_account_id = sfdc_account_id
#                     existingLeadHspt.leads['sfdc'] = newLead
#                     existingLeadHspt.save()
#                 elif sfdc_contact_id is not None:
#                     existingContactSfdc = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_id)).first()
#                     if existingContactSfdc is not None:  # we found a HSPT record which is matched to this new Sfdc lead which is converted to a contact
#                         existingContactSfdc.sfdc_id = sfdc_Id
#                         existingContactSfdc.sfdc_contact_id = sfdc_contact_id
#                         existingContactSfdc.sfdc_account_id = sfdc_account_id
#                         existingContactSfdc.leads['sfdc'] = newLead
#                         #print '4th save'
#                         existingContactSfdc.save()
#                         
#                     
#                     existingContactHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforcecontactid=sfdc_contact_id)).first()
#                     if existingContactHspt is not None:  # we found a HSPT record which is matched to this new Sfdc lead which is converted to a contact
#                         existingContactHspt.sfdc_id = sfdc_Id
#                         existingContactHspt.sfdc_contact_id = sfdc_contact_id
#                         existingContactHspt.sfdc_account_id = sfdc_account_id
#                         existingContactHspt.leads['sfdc'] = newLead
#                         existingContactHspt.save()
                    
            if existingLeadMkto is None and existingLeadHspt is None and existingContactHspt is None and existingLeadEmail is None and existingLead is None:  # no matches found so save new record
                lead = Lead()
                lead.sugr_id = sugr_id
                lead.company_id = company_id
                lead.source_first_name = newLead.get('first_name', None)
                lead.source_last_name = newLead.get('last_name', None)
                lead.source_email = lead_email
                lead.source_created_date =  newLead.get('date_entered', None)
                lead.source_source = newLead.get('lead_source', None)
                lead.source_status = newLead.get('status', None)
                lead.sugr_account_id = sugr_account_id
                lead.sugr_contact_id = sugr_contact_id
                lead.leads["sugr"] = newLead
                #print '5th save'
                lead.save()
                
    except Exception as e:
        print 'exception while saving Sugr Lead: ' + str(e)
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
         
def tempDataCleanup(user_id=None, company_id=None, job_id=None, run_type=None):
    # remove documents from TempData whose IDs already exist in lead
    targetLeads = []
    collection = Lead._get_collection()
    print 'getting leads'
    existingLeads = collection.find({'company_id': int(company_id)}, projection={'leads.hspt.vid': True}, batch_size=1000)     
    print 'got cursor'
    
    for lead in existingLeads:
        targetLeads.append(lead['leads']['hspt']['vid'])
    print 'got leads'
     
    collection2 = TempData._get_collection()
    targetLeadsSubsets = list(_grouper(targetLeads, 100))
    print 'got subsets'
    for targetLeadsSubset in targetLeadsSubsets:
        print 'deleting subset'
        collection2.remove({'company_id' : int(company_id), 'source_record.vid' : {'$in' : targetLeadsSubset} })   
    
def _grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)

def saveHsptCampaignEmailEventsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    ''' Update lead records with interactions based on email campaign events '''
    if run_type == 'initial':
        campaigns = TempData.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        campaigns = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='campaign') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    #leadList = list(leads)
    #leadList = [i['source_record'] for i in leadList]
    
#save the data in the temp table
def savePrdtLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    try:
        print 'saving Prdt Leads'
        if run_type == 'initial':
            for lead in leadList['prospect']: #watch out for the 'prospect' entry for Pardot
                saveTempData(company_id=company_id, record_type="lead", source_system="prdt", source_record=lead, job_id=job_id)
        else:
            for lead in leadList['prospect']:
                saveTempDataDelta(company_id=company_id, record_type="lead", source_system="prdt", source_record=lead, job_id=job_id)
                
    except Exception as e:
        print 'error while saving Prdt leads to temp ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))   
    
def mergeMktoSfdcLeads(user_id=None, company_id=None, job_id=None, run_type=None):
    
    #get all leads which have a Marketo ID
    company_id_qry = 'company_id'
    mkto_id_qry = 'mkto_id__exists'
    leads_mkto_qry = 'leads__mkto__exists'
    
    querydict = {company_id_qry: company_id, mkto_id_qry: True, leads_mkto_qry: True}
    
    
    leads = Lead.objects(**querydict)
    try:
        count = 0
        #loop through each Mkto lead and see if it has a SFDC Lead ID or SFDC Contact ID
        for lead in leads:
            
            thisId = lead['id']
            thisMktoId = lead['mkto_id']
            thisSourceType = lead['leads']['mkto'].get('originalSourceType', None)
            salesforce = 'salesforce.com'
            mkto_sfdc_id = None
            mkto_sfdc_contact_id = None
            
            #print 'marketo lead id is ' + str(thisId)
            if 'sfdcLeadId' in lead['leads']['mkto']:
                mkto_sfdc_id = lead['leads']['mkto']['sfdcLeadId']  # check if there is a corresponding lead from SFDC
            if 'sfdcContactId' in lead['leads']['mkto']:
                mkto_sfdc_contact_id = lead['leads']['mkto']['sfdcContactId']  # check if there is a corresponding contact from SFDC
            #print 'this lead has lead id ' + str(mkto_sfdc_id) + ' and contact id ' + str(mkto_sfdc_contact_id)
            #print 'query0'
            if mkto_sfdc_contact_id is not None:
                #print 'entered contact with sfdc id ' + str(mkto_sfdc_contact_id)
                existingContactSfdcQset = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=mkto_sfdc_contact_id))
                existingContactSfdcQset = list(existingContactSfdcQset)
                for existingContactSfdc in existingContactSfdcQset:
                    #print 'found sfdc contact with id ' + str(existingContactSfdc['id']) + ' for Mkto id ' + str(thisId)
                    if existingContactSfdc is not None and existingContactSfdc['id'] != thisId:
                        print 'found2 sfdc contact with id ' + str(existingContactSfdc['id']) + ' for Mkto id ' + str(thisId)
                        count += 1
                        if thisSourceType == salesforce: #this was a contact from Salesforce so update the SFDC record
                            existingContactSfdc.mkto_id = thisMktoId
                            if 'mkto' not in existingContactSfdc.leads:
                                existingContactSfdc.leads['mkto'] = {}
                            existingContactSfdc.leads['mkto'] = lead.leads['mkto']
                            if 'mkto' in lead.activities:
                                if 'mkto' not in existingContactSfdc.activities:
                                    existingContactSfdc.activities['mkto'] = {}
                                existingContactSfdc.activities['mkto'] = lead.activities['mkto']
                            if 'mkto' in lead.statuses:
                                if 'mkto' not in existingContactSfdc.statuses:
                                    existingContactSfdc.statuses['mkto'] = {}
                                existingContactSfdc.statuses['mkto'] = lead.statuses['mkto']
                            existingContactSfdc.sfdc_account_id = lead['leads']['mkto'].get('ConvertedAccountId', None)
                            existingContactSfdc.save()
                            if 'to_be_deleted' not in lead:
                                lead['to_be_deleted'] = False
                            lead['to_be_deleted'] = True
                            lead.save()
                            print 'MKTO lead ' + str(thisMktoId) + ' needs to be deleted due to contact ' + str(mkto_sfdc_contact_id) 
                        else:
                            lead.sfdc_contact_id = mkto_sfdc_contact_id
                            lead.sfdc_id = existingContactSfdc.sfdc_id
                            lead.sfdc_account_id = existingContactSfdc.sfdc_account_id
                            if 'sfdc' in existingContactSfdc.leads:
                                if 'sfdc' not in lead.leads:
                                    lead.leads['sfdc'] = {}
                                lead.leads['sfdc'] = existingContactSfdc.leads['sfdc']
                            if 'sfdc' in existingContactSfdc.activities:
                                if 'sfdc' not in lead.activities:
                                    lead.activities['sfdc'] = {}
                                lead.activities['sfdc'] = existingContactSfdc.activities['sfdc']
                            if 'sfdc' in existingContactSfdc.opportunities:
                                if 'sfdc' not in lead.opportunities:
                                    lead.opportunities['sfdc'] = {}
                                lead.opportunities['sfdc'] = existingContactSfdc.opportunities['sfdc']
                            if 'sfdc' in existingContactSfdc.contacts:
                                if 'sfdc' not in lead.contacts:
                                    lead.contacts['sfdc'] = {}
                                lead.contacts['sfdc'] = existingContactSfdc.contacts['sfdc']
                            lead.save()
                            if 'to_be_deleted' not in existingContactSfdc:
                                existingContactSfdc['to_be_deleted'] = False
                            existingContactSfdc['to_be_deleted'] = True
                            existingContactSfdc.save()
                            print 'SFDC contact '+ str(mkto_sfdc_contact_id) + ' needs to be deleted due to lead ' + str(thisMktoId)
                        
            elif mkto_sfdc_id is not None:
                #print 'entered lead with sfdc id ' + str(mkto_sfdc_id)
                existingLeadSfdcQset = Lead.objects(Q(company_id=company_id) & Q(sfdc_id=mkto_sfdc_id))
                existingLeadSfdcQset = list(existingLeadSfdcQset)
                for existingLeadSfdc in existingLeadSfdcQset:
                    #print 'found sfdc lead with id ' + str(existingLeadSfdc['id']) + ' for Mkto id ' + str(thisId)
                    if existingLeadSfdc is not None and existingLeadSfdc['id'] != thisId:
                        count += 1
                        print 'found2 sfdc lead with id ' + str(existingLeadSfdc['id']) + ' for Mkto id ' + str(thisId)
                        if thisSourceType == salesforce: #this was a lead from Salesforce so update the SFDC record
                            existingLeadSfdc.mkto_id = thisMktoId
                            if 'mkto' not in existingLeadSfdc.leads:
                                existingLeadSfdc.leads['mkto'] = {}
                            existingLeadSfdc.leads['mkto'] = lead.leads['mkto']
                            if 'mkto' in lead.activities:
                                if 'mkto' not in existingLeadSfdc.activities:
                                    existingLeadSfdc.activities['mkto'] = {}
                                existingLeadSfdc.activities['mkto'] = lead.activities['mkto']
                            if 'mkto' in lead.statuses:
                                if 'mkto' not in existingLeadSfdc.statuses:
                                    existingLeadSfdc.statuses['mkto'] = {}
                                existingLeadSfdc.statuses['mkto'] = lead.statuses['mkto']
                            existingLeadSfdc.sfdc_account_id = lead['leads']['mkto'].get('ConvertedAccountId', None)
                            existingLeadSfdc.save()
                            if 'to_be_deleted' not in lead:
                                lead['to_be_deleted'] = False
                            lead['to_be_deleted'] = True
                            lead.save()
                            print 'MKTO lead ' + str(thisMktoId) + ' needs to be deleted due to contact ' + str(mkto_sfdc_id) 
                        else:
                            lead.sfdc_id = mkto_sfdc_id
                            lead.sfdc_contact_id = existingLeadSfdc.sfdc_contact_id
                            lead.sfdc_account_id = existingLeadSfdc.sfdc_account_id
                            if 'sfdc' not in lead.leads:
                                lead.leads['sfdc'] = {}
                            lead.leads['sfdc'] = existingLeadSfdc.leads['sfdc']
                            if 'sfdc' in existingLeadSfdc.activities:
                                if 'sfdc' not in lead.activities:
                                    lead.activities['sfdc'] = {}
                                lead.activities['sfdc'] = existingLeadSfdc.activities['sfdc']
                            if 'sfdc' in existingLeadSfdc.opportunities:
                                if 'sfdc' not in lead.opportunities:
                                    lead.opportunities['sfdc'] = {}
                                lead.opportunities['sfdc'] = existingLeadSfdc.opportunities['sfdc']
                            if 'sfdc' in existingLeadSfdc.contacts:
                                if 'sfdc' not in lead.contacts:
                                    lead.contacts['sfdc'] = {}
                                lead.contacts['sfdc'] = existingLeadSfdc.contacts['sfdc']
                            lead.save()
                            if 'to_be_deleted' not in existingLeadSfdc:
                                existingLeadSfdc['to_be_deleted'] = False
                            existingLeadSfdc['to_be_deleted'] = True
                            existingLeadSfdc.save()
                            print 'SFDC lead '+ str(mkto_sfdc_id) + ' needs to be deleted due to lead ' + str(thisMktoId)
        print 'number of records merged ' + str(count)                
                    
    except Exception as e:
        print 'exception while merging Mkto and SFDC leads: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         
        
    
def deleteLeads(user_id=None, company_id=None, job_id=None, run_type=None):
    
    #get all leads which have 'to_be_deleted' flag set to True
    company_id_qry = 'company_id'
    deleted_qry = 'to_be_deleted'
    
    querydict = {company_id_qry: company_id, deleted_qry: True}

    try:   
        count = Lead.objects(**querydict).count()
        print 'Number of leads to be deleted: ' + str(count)
        count = Lead.objects(**querydict).delete()
        print 'Number of leads deleted: ' + str(count)
    except Exception as e:
        print 'exception while deleting leads en-masse: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))  
        
def deleteDuplicateMktoIdLeads(user_id=None, company_id=None, job_id=None, run_type=None):
    
    #get all leads which have 'to_be_deleted' flag set to True
    company_id_qry = 'company_id'
    deleted_qry = 'to_be_deleted'
    
    
    querydict = {company_id_qry: company_id}
    
    
    try:   
        dupe_leads = Lead.objects(**querydict).aggregate({'$group': {'_id': '$mkto_id', 'count': {'$sum': 1} } }, {'$match': {'_id': {'$ne': None}, 'count': {'$gt': 1} } }, {'$project': {'mkto_id': '$_id', '_id': 0} })
        dupe_leads = list(dupe_leads)
        print 'dupe leads are ' + str(len(dupe_leads))
        for lead in dupe_leads:
            print 'doing mkto id ' + str(lead['mkto_id'])
            all_leads = Lead.objects(Q(company_id=company_id) & Q(mkto_id=lead['mkto_id']))
            print 'found ' + str(len(list(all_leads))) + ' leads for mkto id ' + str(lead['mkto_id'])
            all_leads = sorted(list(all_leads), key=itemgetter('updated_date'), reverse=True)
            print 'latest updated date ' + str(all_leads[0]['updated_date'])
            all_leads.pop(0)
            for remaining_lead in all_leads:
                Lead.objects(Q(company_id=company_id) & Q(id=remaining_lead['id'])).delete()
    except Exception as e:
        print 'exception while deleting leads en-masse: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))  