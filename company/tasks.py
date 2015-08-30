from __future__ import absolute_import
from datetime import timedelta, datetime
import os
import requests, json


from celery import shared_task
from mmm.celery import app

from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from rest_framework import status, views, permissions, viewsets
from mongoengine.queryset.visitor import Q

from django.core.mail import send_mail, mail_admins
from django.conf import settings
from celery import task

from authentication.models import CustomUser, Company
from leads.models import Lead
from campaigns.models import Campaign
from analytics.models import AnalyticsData, AnalyticsIds
from company.models import CompanyIntegration, TempData
from accounts.models import Account
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from collab.signals import send_notification
from collab.models import Notification 
from mmm.views import _str_from_date

from leads.tasks import retrieveMktoLeads, retrieveHsptLeads, retrieveSfdcLeads, saveMktoLeadsToMaster, saveSfdcLeadsToMaster, saveHsptLeadsToMaster, tempDataCleanup
from contacts.tasks import retrieveSfdcContacts, saveSfdcContactsToMaster
from activities.tasks import retrieveMktoActivities, retrieveSfdcActivities, saveMktoActivitiesToMaster
from opportunities.tasks import retrieveMktoOpportunities, retrieveSfdcOpportunities, saveSfdcOpportunitiesToMaster, retrieveHsptOpportunities, saveHsptOpportunitiesToMaster
from campaigns.tasks import retrieveHsptCampaigns, retrieveMktoCampaigns, saveMktoCampaignsToMaster, retrieveSfdcCampaigns, saveSfdcCampaignsToMaster
from accounts.tasks import retrieveSfdcAccounts, saveSfdcAccountsToMaster
from social.tasks import retrieveBufrTwInteractions, saveBufrTwInteractionsToMaster, retrieveFbokAdStats, saveFbokAdStatsToMaster, retrieveFbokPageStats, saveFbokPageStatsToMaster, retrieveFbokPostStats, saveFbokPostStatsToMaster
from websites.tasks import retrieveHsptWebsiteTraffic, saveHsptWebsiteTrafficToMaster, retrieveGoogWebsiteTraffic, saveGoogleWebsiteTrafficToMaster
#from superadmin.tasks import _get_superadmin
from superadmin.models import SuperJobMonitor

def _superJobMonitorEnd(record, existingIntegration, run_type, status, comments):
    record.comments = comments
    record.ended_date = datetime.utcnow()
    record.status = status
    record.save()
    if run_type == 'initial':
        existingIntegration['initial_run_in_process'] = False #unset the flag
        existingIntegration['initial_run_done'] = False
        existingIntegration['initial_run_last_date'] = None
        if status != 'Failed':
            existingIntegration['initial_run_last_date'] = datetime.utcnow()
            existingIntegration['initial_run_done'] = True
    else:
        existingIntegration['delta_run_in_process'] = False #unset the flag
        existingIntegration['delta_run_done'] = False
        existingIntegration['delta_run_last_date'] = None
        if status != 'Failed':
            existingIntegration['delta_run_last_date'] = datetime.utcnow()
            existingIntegration['delta_run_done'] = True
    
    existingIntegration.save()
    mail_admins(str(run_type) + ' extract job completed with status ' + str(status) , 'Check details in log')
    
def _superJobMonitorAddTask(record, system, task_name):
    currentTasks = record.tasks
    newTask = {}
    newTask['system'] = system
    newTask['task_name'] = task_name 
    newTask['date'] = datetime.utcnow()
    currentTasks.append(newTask)
    record.tasks = currentTasks
    record.save()
    
def _get_superadmin():
    try:
        result = None
        company = Company.objects(company_id=0).first()
        user = CustomUser.objects(company=company.id).first()
        if user is not None and user.is_superadmin == True:
            result = user
        return result
    except Exception as e:
        print 'exception ' + str(e)
        return str(e)
    
@app.task
def companyDataExtract(user_id=None, company_id=None, run_type=None, sinceDateTime=None):
    superJobMonitor = None
    existingIntegration = None
    
    if run_type is None or company_id is None or sinceDateTime is None:
        return
    try:
        sinceDateTime = datetime.fromtimestamp(float(sinceDateTime) / 1000)
        #sinceDateTime = datetime.now() - timedelta(days=30)
        print 'start date is ' + str(sinceDateTime)
        print 'run type is ' + run_type

        #create an entry in the Job Monitor
        superJobMonitor = SuperJobMonitor(company_id=company_id, type=run_type, started_date=datetime.utcnow())
        superJobMonitor.save()
        
        #do pre-check
        _superJobMonitorAddTask(superJobMonitor, "Claritix", "Pre-check started") 
        # get the integration record
        existingIntegration = CompanyIntegration.objects(company_id=company_id).first() 
        if existingIntegration is None:
            _superJobMonitorEnd(superJobMonitor, None, 'Failed', 'No integration record found') 
            mail_admins('Could not find integration record for company ' + company_id , 'Check settings')
            return False 
        if run_type == 'initial':   
            existingIntegration['initial_run_in_process'] = True #set the flag
        else: #delta
            existingIntegration['delta_run_in_process'] = True #set the flag
        existingIntegration.save() # save the flag   
        
        # set up the Request and Cookie
        user = _get_superadmin()
        if user is None:
            _superJobMonitorEnd(superJobMonitor, existingIntegration, 'Failed', 'No super admin found') 
            mail_admins('Could not find super admin!', 'Check settings')
            return False
            
        # remotely login the user
        host = settings.BASE_URL
        url = host + '/api/v1/auth/login/'
        creds = {'email': 'super@claritix.io', 'password':'sudha123'}
        s = requests.Session()
        resp = s.post(url, data=json.dumps(creds))
        if not resp.status_code == 200:
            _superJobMonitorEnd(superJobMonitor, existingIntegration, 'Failed', 'Could not login super admin!') 
            mail_admins('Could not login super admin!', 'Check credentials')
            return False
            
        #do cookie thing - refer to SuperAdmin Cron Job Task for details
        cookies = dict(sessionid = resp.cookies['sessionid'])
        url = host + '/api/v1/users/'
        resp = s.get(url, cookies=cookies)
        _superJobMonitorAddTask(superJobMonitor, "Claritix", "Pre-check completed") 

#         #delete data in Lead Master
#         if run_type == 'initial':
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", "Deletion of Leads, Contacts, Opportunities and Activities started") 
#             count = Lead.objects(company_id=company_id).count()
#             Lead.objects(company_id=company_id).delete()
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", str(count) + " Leads, Contacts, Opportunities and Activities deleted")
#                       
#         #delete data in Campaign Master
#         if run_type == 'initial':
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", "Deletion of Campaigns started") 
#             count = Campaign.objects(company_id=company_id).count()
#             Campaign.objects(company_id=company_id).delete()
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", str(count) + " Campaigns deleted")
#                
#         #delete data in Account Master
#         if run_type == 'initial':
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", "Deletion of Accounts started") 
#             count = Account.objects(company_id=company_id).count()
#             Account.objects(company_id=company_id).delete()
#             _superJobMonitorAddTask(superJobMonitor, "Claritix", str(count) + " Accounts deleted")
#                             
        # find out which systems are integrated and therefore which  tasks should be run
        task_map = {#"mkto" : [retrieveMktoActivities, retrieveMktoLeads,  retrieveMktoCampaigns], \
#                    "hspt" : [retrieveHsptLeads, retrieveHsptOpportunities, retrieveHsptWebsiteTraffic], # , ],
#                     "sfdc" : [retrieveSfdcLeads, retrieveSfdcContacts, retrieveSfdcOpportunities, retrieveSfdcCampaigns, retrieveSfdcAccounts],  \
#                     "bufr" : [retrieveBufrTwInteractions], \
#                     "goog" : [retrieveGoogWebsiteTraffic], \
#                      "fbok" : [retrieveFbokPageStats, retrieveFbokAdStats]#, retrieveFbokPostStats] # , ]
                    }
#         # for future use - retrieveMktoContacts, retrieveMktoOpportunities, retrieveSfdcActivities, 
        final_task_map = {#"mkto" : [saveMktoLeadsToMaster, saveMktoCampaignsToMaster, saveMktoActivitiesToMaster], \
#                    "hspt" : [saveHsptLeadsToMaster, saveHsptOpportunitiesToMaster, saveHsptWebsiteTrafficToMaster], # , ], 
#                     "sfdc" : [saveSfdcLeadsToMaster, saveSfdcContactsToMaster, saveSfdcOpportunitiesToMaster, saveSfdcCampaignsToMaster, saveSfdcAccountsToMaster],  \
#                     "bufr" : [saveBufrTwInteractionsToMaster], \
#                     "goog": [saveGoogleWebsiteTrafficToMaster], \
#                      "fbok": [saveFbokPageStatsToMaster, saveFbokAdStatsToMaster]#, saveFbokPostStatsToMaster] #
                    }
#         #
# #         #saveSfdcLeadsToMaster, saveSfdcContactsToMaster, saveSfdcOpportunitiesToMaster, saveSfdcCampaignsToMaster, 
# #         # saveSfdcLeadsToMaster, saveSfdcContactsToMaster, saveSfdcOpportunitiesToMaster, saveSfdcCampaignsToMaster, saveSfdcAccountsToMaster
# #         #collect all relevant tasks in one list and retrieve metadata as well
        for source in existingIntegration.integrations.keys():
            #change metadata depending on source system
            if source == 'sfdc':
                metadata_objects = [] # ['lead', 'contact', 'campaign', 'opportunity', 'task', 'account'] #[] #objects for which metadata should be collected
            elif source == 'mkto':
                metadata_objects = [] #['lead', 'activity', 'campaign'] #[] #objects for which metadata should be collected
            elif source == 'hspt':
                metadata_objects = ['lead'] #objects for which metadata should be collected
            else:
                metadata_objects = [] #objects for which metadata should be collected
            # if sfdc, explicitly refresh the access token
            if source == 'sfdc':
                sfdc = Salesforce()
                sfdc.refresh_token(company_id)
            #collect meta data
            url = host + '/api/v1/company/' + str(company_id) + '/integrations/metadata/'
            for object in metadata_objects:
                _superJobMonitorAddTask(superJobMonitor, source, "Retrieval of metadata for " + object + " started")
                params = {'code': source, 'object': object}
                resp = s.get(url, params=params) # get metadata about activities
                if not resp.status_code == 200:
                    _superJobMonitorAddTask(superJobMonitor, source, "Retrieval of metadata for " + object + " failed")
                    continue
                else:
                    _superJobMonitorAddTask(superJobMonitor, source, "Retrieval of metadata for " + object + " completed")
                   
            #collect retrieval tasks
            print 'starting retrieval tasks'
            tasks = []
            if source in task_map:
                tasks.extend(task_map[source])
            #now run the tasks
            for task in tasks:
                _superJobMonitorAddTask(superJobMonitor, source, task.__name__ + " started to store temp data")
                print 'starting task ' + str(task)
                task(user_id=user_id, company_id=company_id, job_id=superJobMonitor.id, run_type=run_type, sinceDateTime=sinceDateTime)
                _superJobMonitorAddTask(superJobMonitor, source, task.__name__ + " completed")
                  
            print 'starting save tasks'    
            #collect save tasks
            tasks = []
            if source in final_task_map:
                tasks.extend(final_task_map[source])
            #now run the tasks
            for task in tasks:
                _superJobMonitorAddTask(superJobMonitor, source, task.__name__ + " started to save master data")
                print 'starting task ' + str(task)
                task(user_id=user_id, company_id=company_id, job_id=superJobMonitor.id, run_type=run_type)
                _superJobMonitorAddTask(superJobMonitor, source, task.__name__ + " completed")
             
        #return #REMOVE THIS IN PRODUCTION  
        #if initial run, delete all analytics data
#         if run_type == 'initial':
#             _superJobMonitorAddTask(superJobMonitor, 'Claritix', "Deletion of analytics data started")
#             count1 = AnalyticsData.objects(company_id=company_id).count() #ensure that website_traffic chart data is not deleted
#             AnalyticsData.objects(company_id=company_id).delete() #ensure that website_traffic chart data is not deleted
#             count2 = AnalyticsIds.objects(company_id=company_id).count()
#             AnalyticsIds.objects(company_id=company_id).delete()
#             _superJobMonitorAddTask(superJobMonitor, 'Claritix', str(count1 + count2) + " records deleted from analytics tables")
#                
        # call chart calculate tasks
        charts = [\
                     #{'chart_name': 'sources_bar', 'system_type': 'MA', 'chart_title':'Timeline', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'pipeline_duration', 'system_type': 'MA', 'chart_title':'Pipeline Duration', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'contacts_distr', 'system_type': 'MA', 'chart_title':'Contacts Distribution', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'source_pie', 'system_type': 'MA', 'chart_title':'Source Distribution', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'revenue_source_pie', 'system_type': 'MA', 'chart_title':'Revenue by Source', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'multichannel_leads', 'system_type': 'MA', 'chart_title':'Multichannel Leads', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'tw_performance', 'system_type': 'SO', 'chart_title':'Twitter Performance', 'mode': run_type, 'start_date': sinceDateTime}, \
                     #{'chart_name': 'google_analytics', 'system_type': 'AD', 'chart_title':'Google Analytics', 'mode': run_type, 'start_date': sinceDateTime}, \
                    #{'chart_name': 'social_roi', 'system_type': 'MA', 'chart_title':'Social Performance', 'mode': run_type, 'start_date': sinceDateTime}, \
                    {'chart_name': 'waterfall_chart', 'system_type': 'MA', 'chart_title':'Waterfall Chart', 'mode': run_type, 'start_date': sinceDateTime}, \
               
                ]
        
        url = host + '/api/v1/company/' + str(company_id) + '/analytics/calculate/'
        for chart in charts:
            print 'starting chart ' + str(chart['chart_title'])
            _superJobMonitorAddTask(superJobMonitor, 'Claritix', "Started calculating " + str(chart['chart_title']))
            resp = s.get(url, params=chart)
            if not resp.status_code == 200:
                print 'incorrect status code was ' + str(resp.status_code)
                _superJobMonitorAddTask(superJobMonitor, 'Claritix', 'Could not retrieve data for ' + chart['chart_title'])
                continue
            else:
                _superJobMonitorAddTask(superJobMonitor, 'Claritix', 'Retrieved data for ' + chart['chart_title'])    
        
        #delete all data from past successful initial runs in Temp Table
        if run_type == 'initial':
            _superJobMonitorAddTask(superJobMonitor, "Claritix", "Deletion of temp data table started") 
            successfulJobs = SuperJobMonitor.objects(Q(company_id=company_id) & Q(type='initial') & Q(status='Completed'))
            successfulJobsListTemp = list(successfulJobs)
            print 'found job ids ' + str(len(successfulJobsListTemp))
            successfulJobsList = [i.id for i in successfulJobsListTemp]
            count = TempData.objects(job_id__in=successfulJobsList).count()
            TempData.objects(job_id__in=successfulJobsList).delete()
            _superJobMonitorAddTask(superJobMonitor, "Claritix", str(count) + " records deleted from temp data table")
        #update last run date for initial run in Company Integration record
        
        _superJobMonitorEnd(superJobMonitor, existingIntegration, run_type, 'Completed', 'All tasks completed successfully') 
        return True

    except Exception as e:
        if superJobMonitor is not None and existingIntegration is not None:
            _superJobMonitorEnd(superJobMonitor, existingIntegration, run_type, 'Failed', str(e)) 
        print str(e)
        return False
        
