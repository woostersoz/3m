from __future__ import absolute_import
import os
import datetime
from datetime import timedelta, datetime
from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response

from integrations.views import Marketo, Salesforce, Hubspot  # , get_sfdc_test
from leads.models import Lead
from collab.signals import send_notification
from collab.models import Notification 

from hubspot.contacts._schemas.contacts import CONTACT_SCHEMA

from mongoengine.queryset.visitor import Q
from mmm.views import _str_from_date
from mmm.views import saveTempData, saveTempDataDelta
from company.models import TempData, TempDataDelta

@app.task
def retrieveMktoContacts(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    pass
#    try:
#         leadList = []
#         mkto = Marketo(company_id)
#         # leadList = mkto.get_leads()
#         listList = mkto.get_lists(id=None , name=None, programName=None, workspaceName=None, batchSize=None)
#         #print "got back lists:" + str(len(listList))
#         if listList:
#             for i in range(len(listList)):
#                 results = mkto.get_leads_by_listId(listId=listList[i]['id'])
#                 #print "got back leads from Mkto list: " + str(listList[i]['name']) + " :" + str(len(results))
#                 leadList.extend(results)
#                 saveMktoContacts(user_id=user_id, company_id=company_id, leadList=leadList, newList=listList[i])
#         try:
#             message = 'Leads retrieved from Marketo'
#             notification = Notification()
#             notification.company_id = company_id
#             notification.owner_id = user_id
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
#         return listList
#     except Exception as e:
#         send_notification(dict(type='error', success=False, message=str(e)))         

@app.task    
def retrieveSfdcContacts(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        sdfc = Salesforce()
        if sinceDateTime is None:
            sinceDateTime = datetime.now() - timedelta(days=30) #change to 365
        contactList = sdfc.get_contacts(user_id, company_id) #, _str_from_date(sinceDateTime))
        print 'got back contacts ' + str(len(contactList['records']))
        saveSfdcContacts(user_id=user_id, company_id=company_id, contactList=contactList, job_id=job_id, run_type=run_type)
        try:
            message = 'Contacts retrieved from Salesforce'
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
        send_notification(dict(type='error', success=False, message=str(e)))  
        
# @app.task    
# def retrieveSfdcContactsDaily(user_id=None, company_id=None, job_id=None):
#     try:
#         sdfc = Salesforce()
#         sinceDateTime = (datetime.now() - timedelta(days=1)).date()
#         print 'date is ' + str(sinceDateTime)
#         contactList = sdfc.get_contacts_daily(user_id, company_id, _str_from_date(sinceDateTime))
#         print 'got back contacts ' + str(contactList)
#         saveSfdcContacts(user_id=user_id, company_id=company_id, contactList=contactList, job_id=job_id)
#         try:
#             message = 'Daily contacts retrieved from Salesforce'
#             notification = Notification()
#             #notification.company_id = company_id
#             notification.owner = user_id
#             notification.module = 'Contacts'
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
#         return contactList
#     except Exception as e:
#         send_notification(dict(type='error', success=False, message=str(e)))      
        
@app.task
def retrieveHsptContacts(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    pass
#     try:
#         leadList = []
#         hspt = Hubspot(company_id)
#         # leadList = mkto.get_leads()
#         leadList = hspt.get_all_contacts()
#         #print 'Leads got: ' + str(len(leadList))
#         
#         saveHsptContacts(user_id=user_id, company_id=company_id, leadList=leadList)
#         try:
#             message = 'Leads retrieved from Hubspot'
#             notification = Notification()
#             notification.company_id = company_id
#             notification.owner_id = user_id
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


def saveMktoContacts(user_id=None, company_id=None, leadList=None, newList=None, job_id=None, run_type=None):    
    pass       

#save the data in the temp table
def saveSfdcContacts(user_id=None, company_id=None, contactList=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        for contact in contactList['records']:
            saveTempData(company_id=company_id, record_type="contact", source_system="sfdc", source_record=contact, job_id=job_id)
    else:
        for contact in contactList['records']:
            saveTempDataDelta(company_id=company_id, record_type="contact", source_system="sfdc", source_record=contact, job_id=job_id)
           
def saveSfdcContactsToMaster(user_id=None, company_id=None, job_id=None, run_type=None): 
    if run_type == 'initial':
        contacts = TempData.objects(Q(company_id=company_id) & Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        contacts = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    print 'co id is '+ str(company_id)   
    contactListTemp = list(contacts)
    contactList = [i['source_record'] for i in contactListTemp]   
    #print 'saving sfdc contacts'
    try: 
        for newContact in contactList: #['records']:

            # company_id = request.user.company_id
            sfdc_contact_Id = str(newContact['Id']) 
            print 'contact id is ' + sfdc_contact_Id
            # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
            existingLeadMkto = None
            existingLeadSfdc = None
            existingLeadHspt = None
            existingContact = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_Id)).first()
            
            if existingContact is not None:  # we found this contact already in the DB
                print 'found contact match for ' + str(sfdc_contact_Id)
                if 'sfdc' in existingContact.contacts:
                    existingContact.source_first_name = newContact['FirstName']
                    existingContact.source_last_name = newContact['LastName']
                    existingContact.source_email = newContact['Email']
                    existingContact.source_created_date = str(newContact['CreatedDate'])
                    existingContact.source_source = newContact['LeadSource']
                    existingContact.contacts["sfdc"] = newContact
                    existingContact.save()
                    #Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_Id)).update(contacts__sfdc=newContact)
                else:
                    existingContact.contacts['sfdc'] = {}
                    existingContact.contacts['sfdc'] = newContact
                    existingContact.save()
            elif existingContact is None:  # this lead does not exist 
                existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(leads__sfdc__ConvertedContactId=sfdc_contact_Id)).first()
                if existingLeadSfdc is not None:
                    print 'found match for sfdc lead for contact ' + str(sfdc_contact_Id)
                    existingLeadSfdc.sfdc_contact_id = sfdc_contact_Id
                    existingLeadSfdc.contacts = {}
                    existingLeadSfdc.contacts['sfdc'] = newContact
                    existingLeadSfdc.save()
                    #remove below comments after figuring out how Mkto stored SFDC contact ID
                existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcContactId=sfdc_contact_Id)).first()
                if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                    print 'found mkto lead' + existingLeadMkto.mkto_id
                    existingLeadMkto.sfdc_contact_id = sfdc_contact_Id
                    #existingLeadMkto.contacts = {}
                    existingLeadMkto.contacts['sfdc'] = newContact
                    existingLeadMkto.save()
                existingLeadHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforcecontactid=sfdc_contact_Id)).first()
                if existingLeadHspt is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                    existingLeadHspt.sfdc_contact_id = sfdc_contact_Id
                    existingLeadHspt.contacts = {}
                    existingLeadHspt.contacts['sfdc'] = newContact
                    existingLeadHspt.save()
            if existingLeadSfdc is None and existingLeadMkto is None and existingLeadHspt is None and existingContact is None:  # no matches found so save new record
                lead = Lead()
                lead.sfdc_contact_id = sfdc_contact_Id
                lead.company_id = company_id
                lead.source_first_name = newContact['FirstName']
                lead.source_last_name = newContact['LastName']
                lead.source_email = newContact['Email']
                lead.source_created_date = str(newContact['CreatedDate'])
                lead.source_source = newContact['LeadSource']
                lead.contacts = {}
                lead.contacts["sfdc"] = newContact
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
        print 'exception while saving SFDC contact ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         

#save the data in the temp table
def saveHsptContacts(user_id=None, company_id=None, leadList=None, job_id=None): 
    pass

def saveHsptContactsToMaster(user_id=None, company_id=None, leadList=None): 
    pass