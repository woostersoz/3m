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
from itertools import izip_longest

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
        mkto = Marketo(company_id)
        #results = mkto.get_leads_by_changes_today(current_date_string)
        #allActivities = retrieveMktoActivities(user_id, company_id) #all activties in the last 24 hours
        if run_type == 'initial':
            allActivities = TempData.objects(Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        else:
            allActivities = TempDataDelta.objects(Q(record_type='activity') & Q(source_system='mkto') & Q(job_id=job_id)) #Q(job_id=job_id) & 
        
        #print "got back Mkto activities: " + str(len(allActivities)) 
        leadIds = [str(e['source_record']['leadId']) for e in allActivities]
        leadIds = list(set(leadIds))
        batch_size = 300  #100 Lead IDs at a time
        leadList = []
        for i in range(0, len(leadIds), batch_size):
            leadIdsTemp =  leadIds[i:i+batch_size]
            leadList.extend(mkto.get_leads_by_changes(leadIdsTemp))
            print "got back leads from Mkto: " #+ str(leadList) 
        #leadList = mkto.get_leads_by_changes(leadIds) - this bombs because of too many IDs being passed
        
        saveMktoLeads(user_id=user_id, company_id=company_id, leadList=leadList, newList=None, job_id=job_id, run_type=run_type)
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
        send_notification(dict(type='error', success=False, message=str(e)))         

# @app.task
# def retrieveMktoLeadsDaily(user_id=None, company_id=None, job_id=None):
#     try:
#         current_date_string = _str_from_date(datetime.utcnow())
#         mkto = Marketo(company_id)
#         #results = mkto.get_leads_by_changes_today(current_date_string)
#         allActivities = retrieveMktoActivitiesDaily(user_id, company_id) #all activties in the last 24 hours
#         print "got back Mkto activities: " #+ str(allActivities) 
#         leadIds = [str(e['leadId']) for e in allActivities]
#         leadList = mkto.get_leads_by_changes(leadIds)
#         print "got back leads from Mkto: " #+ str(leadList) 
#         saveMktoLeads(user_id=user_id, company_id=company_id, leadList=leadList, newList=None, job_id=job_id)
#         try:
#             message = 'Daily leads retrieved from Marketo'
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
def retrieveSfdcLeads(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        sdfc = Salesforce()
        if sinceDateTime is None:
            sinceDateTime = (datetime.now() - timedelta(days=1)).date()
        leadList = sdfc.get_leads_delta(user_id, company_id, _str_from_date(sinceDateTime))
        print 'got back leads ' + str(len(leadList))
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
            leadList = hspt.get_recent_contacts(sinceDateTime)
            saveHsptLeads(user_id=user_id, company_id=company_id, leadList=leadList, job_id=job_id, run_type=run_type)
        
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
        
   
      
#save the data in the temp table
def saveMktoLeads(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):
    print 'saving Mkto Leads'
    if run_type == 'initial':
        for lead in leadList:
            saveTempData(company_id=company_id, record_type="lead", source_system="mkto", source_record=lead, job_id=job_id)
    else:
        for lead in leadList:
            saveTempDataDelta(company_id=company_id, record_type="lead", source_system="mkto", source_record=lead, job_id=job_id)


#     for list in newList:
#         saveTempData(company_id=company_id, record_type="list", source_system="mkto", source_record=list, job_id=job_id)


def saveMktoLeadsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
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
            if 'sfdcLeadId' in newLead:
                mkto_sfdc_id = str(newLead['sfdcLeadId'])  # check if there is a corresponding lead from SFDC
            created_date = _date_from_str(newLead['createdAt'])
            addThisList = True
            existingLeadSfdc = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(mkto_id=mkto_id)).first()
            
            if existingLead is not None and 'mkto' in existingLead.leads:  # we found this lead already in the DB
                existingLead.source_first_name = newLead['firstName']
                existingLead.source_last_name = newLead['lastName']
                existingLead.source_email = newLead['email']
                existingLead.source_company = newLead['company']
                existingLead.source_created_date = created_date
                existingLead.source_status = newLead['leadStatus']
                existingLead.source_stage = newLead['leadRevenueStageId']
                existingLead.source_source = newLead['originalSourceInfo']
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
                if mkto_sfdc_id is not None:  # but has a SFDC lead id
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
            
            if existingLeadSfdc is None and existingLead is None:  # no matches found so save new record
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
                lead.source_source = newLead['originalSourceInfo']
                lead.sfdc_account_id =  newLead.get('sfdcAccountId', None)
                lead.leads["mkto"] = newLead
                lead.save()
#                 if newList is not None:
#                     currentLists = []
#                     currentLists.append(newList)
#                     lead.update(lists__mkto=currentLists)
                
    except Exception as e:
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
    if run_type == 'initial':
        leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    leadListTemp = list(leads)
    leadList = [i['source_record'] for i in leadListTemp]
    
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
                    existingLead.source_created_date = str(newLead['CreatedDate'])
                    existingLead.source_source = newLead['LeadSource']
                    existingLead.source_status = newLead['Status']
                    existingLead.sfdc_account_id = sfdc_account_id
                    existingLead.leads['sfdc'] = newLead
                    #print 'first save'
                    existingLead.save()
                    
                    #Lead.objects(Q(company_id=company_id) & Q(sfdc_id=sfdc_Id)).update(leads__sfdc=newLead)
                else:
                    existingLead.leads['sfdc'] = {}
                    existingLead.sfdc_account_id = sfdc_account_id
                    existingLead.leads['sfdc'] = newLead
                    #print '2nd save'
                    existingLead.save()
                    
            elif existingLead is None:  # this lead does not exist 
                existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcLeadId=sfdc_Id)).first()
                if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                    existingLeadMkto.sfdc_id = sfdc_Id
                    existingLeadMkto.sfdc_account_id = sfdc_account_id
                    existingLeadMkto.leads['sfdc'] = newLead
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
    #job_id = ObjectId("55cbb7a356ea0628f85c0075")
    job_id = ObjectId("55d0d4ac8afb000d3f0a6f45") #new job id on Prodn
    if run_type == 'initial':
        collection = TempData._get_collection()
        leads = collection.find({'company_id': int(company_id), 'record_type': 'lead', 'source_system': 'hspt', 'job_id': job_id}, projection={'source_record': True}, batch_size=1000)
        #leads = collection.find({"company_id" : company_id, "record_type": "lead", "source_system":"hspt", "job_id": job_id}, projection={"source_record": True}, batch_size=100)
        #leads = TempData.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
    else:
        leads = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='lead') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record').order_by('-updated_date')
    
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
            hspt_created_date = str(newLead['properties'].get('createdate', None))
            if hspt_created_date is None:
                hspt_created_date = str(newLead['properties'].get('hs_analytics_first_timestamp', None))
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
    
    if run_type == 'initial':
        traffic = TempData.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record')
    else:
        traffic = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='traffic') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record')
    
    system_type_query = 'system_type'
    company_query = 'company_id'
    chart_name_query = 'chart_name'
    date_query = 'date'
    chart_name = 'website_traffic'
        
    trafficList = list(traffic)
    trafficList = [i['source_record'] for i in trafficList]
    
    try:
        for traffic in trafficList:
            date = traffic['date']
            trafficData = traffic['data']
            
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
            
            for record in trafficData:
                source = record['breakdown']
                analyticsData.results[source] = {}
                for datapoint in record:
                    if datapoint != 'breakdown':
                        analyticsData.results[source][datapoint] = record[datapoint]
             
            AnalyticsData.objects(id=analyticsData.id).update(results = analyticsData.results)
                        
    except Exception as e:
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