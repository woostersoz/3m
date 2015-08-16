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
from integrations.views import Marketo, Salesforce, Hubspot #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from mmm.views import _str_from_date
from mmm.views import saveTempData, saveTempDataDelta

@app.task
def retrieveMktoOpportunities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    pass

@app.task
def retrieveHsptOpportunities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):
    try:
        print 'retrieveing Hspt deals'
        hspt = Hubspot(company_id)
        oppList = hspt.get_deals()
        print 'got opps ' + str(len(oppList['results']))
        saveHsptOpportunities(user_id=user_id, company_id=company_id, oppList=oppList, job_id=job_id, run_type=run_type)
        try:
            message = 'Opportunities retrieved from Hubspot'
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
        return oppList
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))      


@app.task    
def retrieveSfdcOpportunities(user_id=None, company_id=None, job_id=None, run_type=None, sinceDateTime=None):  
    try:
        #company_id = request.user.company_id
        existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
# code commented out since we are no longer getting only Mkto related opportunities into Cx
#         if existingIntegration is not None and 'mkto' in existingIntegration['integrations']: # if this system is connected to Marketo
#             company_qry = 'company_id'
#             type_field_qry = 'leads__mkto__exists'
#             sfdc_account_field_qry = 'leads__mkto__sfdcAccountId__ne'
#             querydict = {company_qry: company_id, type_field_qry: True, sfdc_account_field_qry: None}
#             leads_with_sfdc_opps = Lead.objects(**querydict).only('mkto_id').only('leads__mkto__sfdcAccountId')
#             
        sfdc = Salesforce()
# code commented out since we are no longer getting only Mkto related opportunities into Cx
#         account_list = '('
#         for lead in leads_with_sfdc_opps:
#             account_list += '\'' + lead['leads']['mkto']['sfdcAccountId'] + '\'' + ', '
#         account_list = account_list[:-2]
#         account_list += ')'
    
        if sinceDateTime is None:
            sinceDateTime = (datetime.now() - timedelta(days=30)).date()
        oppList = sfdc.get_opportunities_delta(user_id, company_id, _str_from_date(sinceDateTime))
        print 'got opps ' + str(len(oppList))
        contactList = sfdc.get_contacts_for_opportunities(user_id, company_id) # needed because SFDC does not have the Contact ID within the Opp record
        print 'got contacts for opps ' + str(len(contactList))
        saveSfdcOpportunities(user_id=user_id, company_id=company_id, oppList=oppList, contactList=contactList, job_id=job_id, run_type=run_type)
        try:
            message = 'Opportunities retrieved from Salesforce'
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
        return oppList
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))      

# @app.task    
# def retrieveSfdcOpportunitiesDaily(user_id=None, company_id=None, job_id=None): #for cron job
#     try:
#         #company_id = request.user.company_id
#         existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
# # code commented out since we are no longer getting only Mkto related opportunities into Cx        
# #         if existingIntegration is not None and 'mkto' in existingIntegration['integrations']: # if this system is connected to Marketo
# #             company_qry = 'company_id'
# #             type_field_qry = 'leads__mkto__exists'
# #             sfdc_account_field_qry = 'leads__mkto__sfdcAccountId__ne'
# #             querydict = {company_qry: company_id, type_field_qry: True, sfdc_account_field_qry: None}
# #             leads_with_sfdc_opps = Lead.objects(**querydict).only('mkto_id').only('leads__mkto__sfdcAccountId')
# #             
#         sfdc = Salesforce()
#         sinceDateTime = (datetime.now() - timedelta(days=1)).date()
# # code commented out since we are no longer getting only Mkto related opportunities into Cx
# #         account_list = '('
# #         for lead in leads_with_sfdc_opps:
# #             account_list += '\'' + lead['leads']['mkto']['sfdcAccountId'] + '\'' + ', '
# #         account_list = account_list[:-2]
# #         account_list += ')'
#     
#         oppList = sfdc.get_opportunities_daily(user_id, company_id, _str_from_date(sinceDateTime))
#         print 'got opps ' + str(oppList)
#         contactList = sfdc.get_contacts_for_opportunities(user_id, company_id) # needed because SFDC does not have the Contact ID within the Opp record
#         saveSfdcOpportunities(user_id=user_id, company_id=company_id, oppList=oppList, contactList=contactList, job_id=job_id)
#         
#         try:
#             message = 'Daily opportunities retrieved from Salesforce'
#             notification = Notification()
#             #notification.company_id = company_id
#             notification.owner = user_id
#             notification.module = 'Opportunities'
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
#         return oppList
#     except Exception as e:
#         send_notification(dict(type='error', success=False, message=str(e)))      

def saveMktoOpportunities(user_id=None, company_id=None, activityList=None, activityTypeArray=None, job_id=None, run_type=None):    
    pass
  
#save the data in the temp table
def saveSfdcOpportunities(user_id=None, company_id=None, oppList=None, contactList=None, job_id=None, run_type=None):
    if run_type == 'initial':
        for opp in oppList['records']:
            saveTempData(company_id=company_id, record_type="opportunity", source_system="sfdc", source_record=opp, job_id=job_id)
        for contact in contactList['records']:
            saveTempData(company_id=company_id, record_type="contact", source_system="sfdc", source_record=contact, job_id=job_id)
    else:
        for opp in oppList['records']:
            saveTempDataDelta(company_id=company_id, record_type="opportunity", source_system="sfdc", source_record=opp, job_id=job_id)
        for contact in contactList['records']:
            saveTempDataDelta(company_id=company_id, record_type="contact", source_system="sfdc", source_record=contact, job_id=job_id)

def saveSfdcOpportunitiesToMaster(user_id=None, company_id=None, job_id=None, run_type=None):  
    if run_type == 'initial':
        opps = TempData.objects(Q(company_id=company_id) & Q(record_type='opportunity') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
        contacts = TempData.objects(Q(company_id=company_id) & Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        opps = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='opportunity') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
        contacts = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='contact') & Q(source_system='sfdc') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
  
    oppListTemp = list(opps)
    oppList = [i['source_record'] for i in oppListTemp]
    
    contactListTemp = list(contacts)
    contactList = [i['source_record'] for i in contactListTemp]
     
    try:
        allOpps = oppList #['records']
        # below code copied from contacts.tasks
        for newContact in contactList: #['records']:
            if newContact['OpportunityContactRoles'] is None: # if this contact has no opportunities
                continue # move to next contact
            # company_id = request.user.company_id
            sfdc_account_id = None
            thisLeadsOppsIds = newContact['OpportunityContactRoles']['records']
            thisLeadsOpps = []
            for opp in thisLeadsOppsIds: #loop through all the Opp records in the Contact record
                print 'trying for opp with id ' + str(opp['OpportunityId'])
                thisOpp = next((x for x in allOpps if x['Id'] == opp['OpportunityId']), None) # if this opp is found in the list of opps retrieved separately
                if thisOpp is not None: # if found
                    print 'found this opp'
                    sfdc_account_id = thisOpp['AccountId']
                    thisLeadsOpps.append(thisOpp) #add it
            
            sfdc_contact_Id = str(newContact['Id']) 
            print 'contact id is ' + sfdc_contact_Id
            # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
            existingLeadMkto = None
            existingLeadSfdc = None
            existingLeadHspt = None
            existingContact = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_Id)).first()
            
            if existingContact is not None:  # we found this contact already in the DB
                print ' eC is not none'        
                if 'sfdc' not in existingContact.opportunities:
                    opportunities = {}
                    opportunities['sfdc'] = []
                    opportunities['sfdc'].extend(thisLeadsOpps)  
                    existingContact.update(opportunities__sfdc = opportunities['sfdc'])
                    existingContact.update(sfdc_account_id = sfdc_account_id)
                    print 'just updated acct id 1'
                else:
                    for newOpp in thisLeadsOpps:
                        print ' nefre get' 
                        if not any (e.get('Id', None) == newOpp['Id'] for e in existingContact.opportunities['sfdc']): # does an opportunity with this Id already exist
                            opportunities = existingContact.opportunities['sfdc']
                            opportunities.append(newOpp)
                            existingContact.sfdc_account_id = sfdc_account_id
                            # save this opportunity        
                            existingContact.update(opportunities__sfdc = opportunities)
                            existingContact.update(sfdc_account_id = sfdc_account_id)
                            print 'just updated acct id 2'
                        else: #this opp already exists
                            for i in range(len(existingContact.opportunities['sfdc'])):
                                if existingContact.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
                                    existingContact.opportunities['sfdc'][i] = newOpp
                                    existingContact.sfdc_account_id = sfdc_account_id
                                    existingContact.save()
                                    print 'just updated acct id 3'
            elif existingContact is None:  # this lead does not exist 
                print ' eC is much none' 
                existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(leads__sfdc__ConvertedContactId=sfdc_contact_Id)).first()
                if existingLeadSfdc is not None:
                    
                    if 'sfdc' not in existingLeadSfdc.opportunities:
                        opportunities = {}
                        opportunities['sfdc'] = []
                        opportunities['sfdc'].extend(thisLeadsOpps)  
                        existingLeadSfdc.update(opportunities__sfdc = opportunities['sfdc'])
                        existingLeadSfdc.update(sfdc_account_id = sfdc_account_id)
                        print 'just updated acct id 4'
                    else:
                        for newOpp in thisLeadsOpps:
                            if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadSfdc.opportunities['sfdc']): # does an opportunity with this Id already exist
                                opportunities = existingLeadSfdc.opportunities['sfdc']
                                opportunities.append(newOpp)
                                # save this opportunity        
                                existingLeadSfdc.update(opportunities__sfdc = opportunities)
                                existingLeadSfdc.update(sfdc_account_id = sfdc_account_id)
                                print 'just updated acct id 5'
                            else: #this opp already exists
                                for i in range(len(existingLeadSfdc.opportunities['sfdc'])):
                                    if existingLeadSfdc.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
                                        existingLeadSfdc.opportunities['sfdc'][i] = newOpp
                                        existingLeadSfdc.sfdc_account_id = sfdc_account_id
                                        existingLeadSfdc.save()
                                        print 'just updated acct id 6'
                else:
                    existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcContactId=sfdc_contact_Id)).first()
                    if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
                        
                        if 'sfdc' not in existingLeadMkto.opportunities:
                            opportunities = {}
                            opportunities['sfdc'] = []
                            opportunities['sfdc'].extend(thisLeadsOpps)  
                            existingLeadMkto.update(opportunities__sfdc = opportunities['sfdc'])
                            existingLeadMkto.update(sfdc_account_id = sfdc_account_id)
                        else:
                            for newOpp in thisLeadsOpps:
                                if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadMkto.opportunities['sfdc']): # does an opportunity with this Id already exist
                                    opportunities = existingLeadMkto.opportunities['sfdc']
                                    opportunities.append(newOpp)
                                    # save this opportunity        
                                    existingLeadMkto.update(opportunities__sfdc = opportunities)
                                    existingLeadMkto.update(sfdc_account_id = sfdc_account_id)
                                else: #this opp already exists
                                    for i in range(len(existingLeadMkto.opportunities['sfdc'])):
                                        if existingLeadMkto.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
                                            existingLeadMkto.opportunities['sfdc'][i] = newOpp
                                            existingLeadMkto.sfdc_account_id = sfdc_account_id
                                            existingLeadMkto.save()
                        
                    existingLeadHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforcecontactid=sfdc_contact_Id)).first()
                    if existingLeadHspt is not None:  # we found a Hspt lead record which is matched to this new Sfdc lead
                        
                        if 'sfdc' not in existingLeadHspt.opportunities:
                            opportunities = {}
                            opportunities['sfdc'] = []
                            opportunities['sfdc'].extend(thisLeadsOpps)  
                            existingLeadHspt.update(opportunities__sfdc = opportunities['sfdc'])
                            existingLeadHspt.update(sfdc_account_id = sfdc_account_id)
                        else:
                            for newOpp in thisLeadsOpps:
                                if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadHspt.opportunities['sfdc']): # does an opportunity with this Id already exist
                                    opportunities = existingLeadHspt.opportunities['sfdc']
                                    opportunities.append(newOpp)
                                    # save this opportunity        
                                    existingLeadHspt.update(opportunities__sfdc = opportunities)
                                    existingLeadHspt.update(sfdc_account_id = sfdc_account_id)
                                else: #this opp already exists
                                    for i in range(len(existingLeadHspt.opportunities['sfdc'])):
                                        if existingLeadHspt.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
                                            existingLeadHspt.opportunities['sfdc'][i] = newOpp
                                            existingLeadHspt.sfdc_account_id = sfdc_account_id
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
                lead.sfdc_account_id = sfdc_account_id
                lead.save()
                contacts = {}
                contacts['sfdc'] = newContact
                #lead.contacts["sfdc"] = newContact
                lead.update(contacts__sfdc = contacts['sfdc'])
                print 'just updated acct id 7'
                opportunities = {}
                opportunities['sfdc'] = []
                opportunities['sfdc'].extend(thisLeadsOpps)  
                lead.update(opportunities__sfdc = opportunities['sfdc'])
        
# code commented out since we are no longer getting only Mkto related opportunities into Cx       
#         for newOpp in oppList['records']:
# 
#             # company_id = request.user.company_id
#             sfdc_account_id = str(newOpp['AccountId']) # find the account ID
#             print 'account id is ' + sfdc_account_id
#             # sfdc_mkto_id = str(newLead['sfdcLeadId']) #check if there is a corresponding lead from MKTO
#             existingLeadMkto = None
#             existingLeadSfdc = None
#             existingLeadHspt = None
#             #existingContact = Lead.objects(Q(company_id=company_id) & Q(sfdc_contact_id=sfdc_contact_Id)).first()
#             existingLeadSfdc = Lead.objects(Q(company_id=company_id) & Q(leads__sfdc__ConvertedAccountId=sfdc_account_id)).first()
#             if existingLeadSfdc is not None:
#                 if 'sfdc' not in existingLeadSfdc.opportunities:
#                     opportunities = {}
#                     opportunities['sfdc'] = []
#                     opportunities['sfdc'].append(newOpp) # add this opp to the new array
#                     existingLeadSfdc.update(opportunities__sfdc = opportunities)
#                 else:
#                     if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadSfdc.opportunities['sfdc']): # does an opportunity with this Id already exist
#                         opportunities = existingLeadSfdc.opportunities['sfdc']
#                         opportunities.append(newOpp)
#                         # save this opportunity        
#                         existingLeadSfdc.update(opportunities__sfdc = opportunities)
#                     else: #this opp already exists
#                         for i in range(len(existingLeadSfdc.opportunities['sfdc'])):
#                             if existingLeadSfdc.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
#                                 existingLeadSfdc.opportunities['sfdc'][i] = newOpp
#                                 existingLeadSfdc.save()
#                 
#                 # and move to the next opportunity in the loop
#                 continue
#             else: #this opp does not exist within an SFDC lead
#                 # check if it is a Marketo lead   
#                 existingLeadMkto = Lead.objects(Q(company_id=company_id) & Q(leads__mkto__sfdcAccountId=sfdc_account_id)).first()
#                 if existingLeadMkto is not None:  # we found a MKto lead record which is matched to this opp
#                     print 'found mkto lead' + existingLeadMkto.mkto_id
#                     if 'sfdc' not in existingLeadMkto.opportunities:
#                         opportunities = []
#                         opportunities.append(newOpp) # add this opp to the new array
#                         existingLeadMkto.update(opportunities__sfdc = opportunities)
#                         print 'saved opps'
#                     else: # if ['opportunities']['sfdc'] already exists
#                         print 'opp exist'
#                         if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadMkto.opportunities['sfdc']): # does an opportunity with this Id already exist
#                             opportunities = existingLeadMkto.opportunities['sfdc']
#                             opportunities.append(newOpp)
#                             # save this opportunity        
#                             existingLeadMkto.update(opportunities__sfdc = opportunities)
#                             print 'saved sfdc'
#                         else: #this opp already exists
#                             print 'opp does not exist'
#                             for i in range(len(existingLeadMkto.opportunities['sfdc'])):
#                                 if existingLeadMkto.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
#                                     existingLeadMkto.opportunities['sfdc'][i] = newOpp
#                                     existingLeadMkto.save()
#                                     print 'saved update'
#                     #move on to the next opp
#                     continue
#                 existingLeadHspt = Lead.objects(Q(company_id=company_id) & Q(leads__hspt__properties__salesforceaccountid=sfdc_account_id)).first()
#                 if existingLeadHspt is not None:  # we found a MKto lead record which is matched to this new Sfdc lead
#                     if 'sfdc' not in existingLeadHspt.opportunities:
#                         opportunities = {}
#                         opportunities['sfdc'] = []
#                         opportunities['sfdc'].append(newOpp) # add this opp to the new array
#                         existingLeadHspt.update(opportunities__sfdc = opportunities)
#                     else:
#                         if not any (e.get('Id', None) == newOpp['Id'] for e in existingLeadHspt.opportunities['sfdc']): # does an opportunity with this Id already exist
#                             opportunities = existingLeadHspt.opportunities['sfdc']
#                             opportunities.append(newOpp)
#                             # save this opportunity        
#                             existingLeadHspt.update(opportunities__sfdc = opportunities)
#                         else: #this opp already exists
#                             for i in range(len(existingLeadHspt.opportunities['sfdc'])):
#                                 if existingLeadHspt.opportunities['sfdc'][i]['Id'] == newOpp['Id']:
#                                     existingLeadHspt.opportunities['sfdc'][i] = newOpp
#                                     existingLeadHspt.save()
#                     # move onto the next opp
#                     continue
#                 
#             if existingLeadSfdc is None and existingLeadMkto is None and existingLeadHspt is None:  # no matches found so throw error i,e, not possible
#                 #raise ValueError('Opportunity found without lead or contact')
#                 lead = Lead()
#                 lead.sfdc_id = sfdc_Id
#                 lead.company_id = company_id
#                 lead.source_first_name = newLead['FirstName']
#                 lead.source_last_name = newLead['LastName']
#                 lead.source_email = newLead['Email']
#                 lead.source_created_date = str(newLead['CreatedDate'])
#                 lead.source_source = newLead['LeadSource']
#                 lead.source_status = newLead['Status']
#                 lead.leads["sfdc"] = newLead
#                 print '5th save'
#                 lead.save()
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))         
 
    
    
#save the data in the temp table
def saveHsptOpportunities(user_id=None, company_id=None, oppList=None, job_id=None, run_type=None):
    print 'saving hspt opps'
    if run_type == 'initial':
        for opp in oppList['results']:
            saveTempData(company_id=company_id, record_type="opportunity", source_system="hspt", source_record=opp, job_id=job_id)
    else:
        for opp in oppList['results']:
            saveTempDataDelta(company_id=company_id, record_type="opportunity", source_system="hspt", source_record=opp, job_id=job_id)
       
#saves Hspt Deals to Lead collection
def saveHsptOpportunitiesToMaster(user_id=None, company_id=None, job_id=None, run_type=None):  
    print 'saving hspt opps to master'
    if run_type == 'initial':
        opps = TempData.objects(Q(company_id=company_id) & Q(record_type='opportunity') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
    else:
        opps = TempDataDelta.objects(Q(company_id=company_id) & Q(record_type='opportunity') & Q(source_system='hspt') & Q(job_id=job_id) ).only('source_record') #& Q(job_id=job_id) 
        
    oppListTemp = list(opps)
    oppList = [i['source_record'] for i in oppListTemp]
    
    try:
        for opp in oppList:
            associations = opp.get('associations', None)
            if associations is not None:
                #print 'found assoc'
                related_leads_list = associations.get('associatedVids', None)
                #print 'releated leads list is ' + str(len(related_leads_list))
                for i in range(len(related_leads_list)):
                    lead_id = related_leads_list[i]
                    #print 'lead id is ' + str(lead_id)
                    existingLead = Lead.objects(Q(company_id=company_id) & Q(hspt_id=str(lead_id))).first()
                    #we found an existing lead with the same VID (hspt_id) as the deal
                    if existingLead is not None:
                        #print 'found existing lead'
                        if 'hspt' not in existingLead.opportunities:
                            #print 'hspt not in opps'
                            opportunities = {}
                            opportunities['hspt'] = []
                            opportunities['hspt'].append(opp)  
                            existingLead.update(opportunities__hspt = opportunities['hspt'])
                        else:
                            if not any (e.get('dealId', None) == opp['dealId'] for e in existingLead.opportunities['hspt']): # does an opportunity with this Id already exist
                                opportunities = existingLead.opportunities['hspt']
                                opportunities.append(opp)
                                # save this opportunity        
                                existingLead.update(opportunities__hspt = opportunities)
                            else: #this opp already exists
                                for i in range(len(existingLead.opportunities['hspt'])):
                                    if existingLead.opportunities['hspt'][i]['dealId'] == opp['dealId']:
                                        existingLead.opportunities['hspt'][i] = opp
                                        existingLead.save()
                    #if no matching lead found, continue to next opportunity
                    
    except Exception as e:
        send_notification(dict(type='error', success=False, message=str(e)))                 
     