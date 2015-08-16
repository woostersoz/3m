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
from company.models import TempData, TempDataDelta
from accounts.models import Account

from hubspot.contacts._schemas.contacts import CONTACT_SCHEMA

from mongoengine.queryset.visitor import Q
from mmm.views import _str_from_date, saveTempData, saveTempDataDelta

@app.task
def retrieveMktoContacts(user_id=None, company_id=None):
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
def retrieveSfdcAccounts(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        if sinceDateTime is None:
            sinceDateTime = (datetime.now() - timedelta(days=1)).date()
        sfdc = Salesforce()
        accountList = sfdc.get_accounts(user_id, company_id) #, _str_from_date(sinceDateTime))
        print 'got back accounts ' + str(len(accountList['records']))
        saveSfdcAccounts(user_id=user_id, company_id=company_id, accountList=accountList, job_id=job_id, run_type=run_type)
        try:
            message = 'Accounts retrieved from Salesforce'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Accounts'
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
        return accountList
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))  
        
@app.task    
def retrieveSfdcContactsDaily(user_id=None, company_id=None):
    try:
      pass
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))      
        
@app.task
def retrieveHsptContacts(user_id=None, company_id=None):
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


def saveMktoContacts(user_id=None, company_id=None, leadList=None, newList=None):    
    
    try: 
        pass
                
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))         
    
def saveSfdcAccounts(user_id=None, company_id=None, accountList=None, job_id=None, run_type=None):
    if run_type == 'initial':
        for account in accountList['records']:
            saveTempData(company_id=company_id, record_type="account", source_system="sfdc", source_record=account, job_id=job_id)
    else:
        for account in accountList['records']:
            saveTempDataDelta(company_id=company_id, record_type="account", source_system="sfdc", source_record=account, job_id=job_id)
    
    
def saveSfdcAccountsToMaster(user_id=None, company_id=None, job_id=None, run_type=None):    
    if run_type == 'initial':
        accounts = TempData.objects(Q(company_id=company_id) & Q(record_type='account') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        accounts = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='account') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    
    accountListTemp = list(accounts)
    accountList = [i['source_record'] for i in accountListTemp]
    
    try: 
        for newAccount in accountList:
            sfdc_id = str(newAccount['Id']) 
            #find all leads that have this account ID 
            relatedLeadList = None
            relatedLeads = Lead.objects(Q(company_id=company_id) & Q(sfdc_account_id=sfdc_id))
            if relatedLeads is not None:
                relatedLeadList = list(relatedLeads)
#             if relatedLeads is not None:
#                 #leadListTemp = list(relatedLeads)
#                 #relatedLeadList = [i.id for i in leadListTemp]
#                 for lead in relatedLeads:
#                     relatedLeadList.append(lead)
                
            print 'account id is ' + sfdc_id
            # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
            existingAccount = None
            existingAccount = Account.objects(Q(company_id=company_id) & Q(sfdc_id=sfdc_id)).first()
            
            if existingAccount is not None:  # we found this contact already in the DB
                if 'sfdc' in existingAccount.accounts:
                    existingAccount.source_name = newAccount['Name']
                    existingAccount.source_source = newAccount['AccountSource']
                    existingAccount.source_industry = newAccount['Industry']
                    existingAccount.source_created_date = newAccount['CreatedDate']
                    existingAccount.accounts["sfdc"] = newAccount
                    if relatedLeadList is not None:
                        existingAccount.leads = relatedLeadList
                    existingAccount.save()
                    #Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_Id)).update(contacts__sfdc=newContact)
                else:
                    existingAccount.accounts['sfdc'] = {}
                    existingAccount.accounts['sfdc'] = newAccount
                    if relatedLeadList is not None:
                        existingAccount.leads = relatedLeadList
                    existingAccount.save()
            elif existingAccount is None:  # this lead does not exist     
                account = Account()
                account.sfdc_id = sfdc_id
                account.source_name = newAccount['Name']
                account.source_source = newAccount['AccountSource']
                account.source_industry = newAccount['Industry']
                account.source_created_date = newAccount['CreatedDate']
                account.accounts = {}
                account.accounts["sfdc"] = newAccount
                if relatedLeadList is not None:
                    account.leads = relatedLeadList
                account.company_id = company_id
                account.save()
    except Exception as e:
        print 'exception while saving accounts ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))         


def saveHsptContacts(user_id=None, company_id=None, leadList=None): 
    try: 
        for newLead in leadList: 
            
            newLead = vars(newLead)['_field_values']
            hspt_id = str(newLead['vid']) 
            #print 'gs id is ' + str(hspt_id)
            #hspt_sfdc_id = str(newLead['sfdcLeadId'])  # check if there is a corresponding lead from SFDC
            hspt_sfdc_id = None
            if 'salesforceleadid' in newLead['properties']:
                hspt_sfdc_id = str(newLead['properties']['salesforceleadid']) # temp fix by satya till SFDC ID field in Hubspot is discovered
                
            #addThisList = True
            existingLeadSfdc = None
            existingLead = None
            existingLead = Lead.objects(Q(company_id=company_id) & Q(hspt_id=hspt_id)).first()
            
            if existingLead is not None and 'hspt' in existingLead.leads:  # we found this lead already in the DB
                Lead.objects(Q(company_id=company_id) & Q(hspt_id=hspt_id)).update(leads__hspt=newLead)
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
                    print 'found lead with SFDC ID ' + str(hspt_sfdc_id)
                    existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(leads__sfdc__Id=hspt_sfdc_id)).first()
                    if existingLeadSfdc is not None:  # we found a SFDC lead record which is matched to this new Mkto lead
                        existingLeadSfdc.hspt_id = hspt_id
                        existingLeadSfdc.leads['hspt'] = newLead
                        existingLeadSfdc.save()
#                         currentLists = []
#                         currentLists.append(newList)
#                         existingLeadSfdc.update(lists__mkto=currentLists)
            
            if existingLeadSfdc is None and existingLead is None:  # no matches found so save new record
                lead = Lead()
                lead.hspt_id = hspt_id
                lead.company_id = company_id
                lead.leads["hspt"] = newLead
                lead.save()
#                 currentLists = []
#                 currentLists.append(newList)
#                 lead.update(lists__mkto=currentLists)
                
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))   