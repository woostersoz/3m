import requests, json, time, datetime
from datetime import timedelta
from dateutil import relativedelta

from rest_framework_mongoengine import generics as drfme_generics
from rest_framework.response import Response

from authentication.models import CustomUser, Company
from django.contrib.auth import authenticate, login, logout
from superadmin.models import SuperIntegration
from superadmin.serializers import SuperIntegrationSerializer
from company.models import CompanyIntegration

# from leads.tasks import retrieveMktoLeadsDaily
# from contacts.tasks import retrieveSfdcContactsDaily
from integrations.views import get_metadata
from company.tasks import companyDataExtract, _get_superadmin, companyWeeklyEmail
from mmm.views import _str_from_date

from django.db.models import Q
from mmm.celery import app
from celery import task
from django.core.mail import send_mail, mail_admins
from django.conf import settings
#from analytics.serializers import date


@app.task
def dailyCronJob_Deprecated():
    try:
        logs = [] #holds all error messages for the job
        # first get the superadmin user and the companies
        user = _get_superadmin()
        if user is None:
            mail_admins('Could not find super admin!', 'Check settings')
            return # no superadmin found
        # remotely login the user
        host = settings.BASE_URL
        url = host + '/api/v1/auth/login/'
        creds = {'email': 'super@claritix.io', 'password':'sudha123'}
        s = requests.Session()
        resp = s.post(url, data=json.dumps(creds))
        if not resp.status_code == 200:
            mail_admins('Could not login super admin!', 'Check credentials')
            logs.append('Could not login super admin!')
            return
        else:
            logs.append('Superadmin logged in')
            
        cookies = dict(sessionid = resp.cookies['sessionid'])
        url = host + '/api/v1/users/'
        resp = s.get(url, cookies=cookies)
    
        companies = Company.objects.filter(~Q(company_id=0))
        
        #now loop through each company find which systems are connected 
        for company in companies:
            company_id = company.company_id
            company_name = company.name
            existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
            if existingIntegration is None: # no integration found so move to next company
                continue
            
            #loop through the different source systems and call their respective tasks
            for source in existingIntegration.integrations.keys():
                if source == 'mkto':
                    #start by calling Mkto Lead Daily Retrieval (it calls Mkto Activity Daily Retrieval so no need to call Activity again)
                    # get meta data for activities 
                    url = host + '/api/v1/company/' + str(company_id) + '/integrations/metadata/'
                    params = {'code': source, 'object': 'activity'}
                    resp = s.get(url, params=params) # get metadata about activities
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve metadata about activities from Marketo for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved metadata about activities from Marketo for company ' + str(company_name))
                    # get meta data for leads 
                    params = {'code': source, 'object': 'lead'}
                    resp = s.get(url, params=params) # get metadata about leads
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve metadata about leads from Marketo for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved metadata about leads from Marketo for company ' + str(company_name))
                    # get activities and leads
                    url = host + '/api/v1/company/' + str(company_id) + '/leads/retrieve/daily/'
                    params = {'code': source}
                    resp = s.get(url, params=params) # get leads and activities
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve activities and leads from Marketo for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved activities and leads from Marketo for company ' + str(company_name))
                #if integrated to Salesforce    
                if source == 'sfdc':
                    #get metadata about contact
                    url = host + '/api/v1/company/' + str(company_id) + '/integrations/metadata/'
                    params = {'code': source, 'object': 'contact'}
                    resp = s.get(url, params=params) # get metadata
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve contact metadata from SFDC for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved metadata about contacts from SFDC for company ' + str(company_name))
                    #get contacts
                    url = host + '/api/v1/company/' + str(company_id) + '/contacts/retrieve/daily/'
                    params = {'code': source}
                    resp = s.get(url, params=params) # get metadata
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve contacts from SFDC for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved contacts from SFDC for company ' + str(company_name))
                    #get metadata about campaign
                    url = host + '/api/v1/company/' + str(company_id) + '/integrations/metadata/'
                    params = {'code': source, 'object': 'campaign'}
                    resp = s.get(url, params=params) # get metadata
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve campaign metadata from SFDC for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved metadata about campaigns from SFDC for company ' + str(company_name))
                    #get contacts
                    url = host + '/api/v1/company/' + str(company_id) + '/campaigns/retrieve/daily/'
                    params = {'code': source}
                    resp = s.get(url, params=params) # get metadata
                    if not resp.status_code == 200:
                        logs.append('Could not retrieve campaigns from SFDC for company ' + str(company_name))
                        continue
                    else:
                        logs.append('Retrieved campaigns from SFDC for company ' + str(company_name))
                    
            # run the daily analytics extract jobs
            # timeline chart
            url = host + '/api/v1/company/' + str(company_id) + '/analytics/calculate/'
            chart_title = 'Timeline'
            params = {'chart_name': 'sources_bar', 'system_type': 'MA', 'chart_title':chart_title, 'mode': 'Daily'}
            resp = s.get(url, params=params)
            if not resp.status_code == 200:
                logs.append('Could not retrieve data for ' + chart_title + ' for company ' + str(company_name))
                continue
            else:
                logs.append('Retrieved data for ' + chart_title + ' for company ' + str(company_name))    
            # pipeline duration chart
            chart_title = 'Pipeline Duration'
            params = {'chart_name': 'pipeline_duration', 'system_type': 'MA', 'chart_title':chart_title, 'mode': 'Daily'}
            resp = s.get(url, params=params)
            if not resp.status_code == 200:
                logs.append('Could not retrieve data for ' + chart_title + ' for company ' + str(company_name))
                continue
            else:
                logs.append('Retrieved data for ' + chart_title + ' for company ' + str(company_name))
            # contacts distribution chart
            chart_title = 'Contacts Distribution'
            params = {'chart_name': 'contacts_distr', 'system_type': 'MA', 'chart_title':chart_title, 'mode': 'Daily'}
            resp = s.get(url, params=params)
            if not resp.status_code == 200:
                logs.append('Could not retrieve data for ' + chart_title + ' for company ' + str(company_name))
                continue
            else:
                logs.append('Retrieved data for ' + chart_title + ' for company ' + str(company_name))
            # source pie chart
            chart_title = 'Source Breakdown'
            params = {'chart_name': 'source_pie', 'system_type': 'MA', 'chart_title':chart_title, 'mode': 'Daily'}
            resp = s.get(url, params=params)
            if not resp.status_code == 200:
                logs.append('Could not retrieve data for ' + chart_title + ' for company ' + str(company_name))
                continue
            else:
                logs.append('Retrieved data for ' + chart_title + ' for company ' + str(company_name))
            # revenue source pie chart
            chart_title = 'Revenue by Source'
            params = {'chart_name': 'revenue_source_pie', 'system_type': 'MA', 'chart_title':chart_title, 'mode': 'Daily'}
            resp = s.get(url, params=params)
            if not resp.status_code == 200:
                logs.append('Could not retrieve data for ' + chart_title + ' for company ' + str(company_name))
                continue
            else:
                logs.append('Retrieved data for ' + chart_title + ' for company ' + str(company_name))
        
        mail_admins('Daily extract job completed', '\n'.join(str(elem) for elem in logs))
        print 'Daily extract job completed'       
    
    except Exception as e:
        logs.append(str(e))
        #mail_admins('Exception occurred!', str(e))
        
@app.task
def dailyCronJob():
    print 'in cron'
    try:
        logs = [] #holds all error messages for the job
        # first get the superadmin user and the companies
        user = _get_superadmin()
        if user is None:
            mail_admins('Could not find super admin!', 'Check settings')
            return # no superadmin found
        # remotely login the user
        host = settings.BASE_URL
        url = host + '/api/v1/auth/login/'
        creds = {'email': 'super@claritix.io', 'password':'sudha123'}
        s = requests.Session()
        resp = s.post(url, data=json.dumps(creds))
        print 'resp is ' + str(resp.status_code)
        if not resp.status_code == 200:
            mail_admins('Could not login super admin!', 'Check credentials')
            logs.append('Could not login super admin!')
            return
        else:
            logs.append('Superadmin logged in')
        
        cookies = dict(sessionid = resp.cookies['sessionid'])
        url = host + '/api/v1/users/'
        resp = s.get(url, cookies=cookies)
        print 'resp2 is ' + str(resp.status_code)
            
        print str(logs)
        
        querydict = {'company_id__ne' : 0}
        companies = Company.objects(**querydict)
        print 'found companies ' + str(len(companies))
        #now loop through each company find which systems are connected 
        for company in companies:
            company_id = company.company_id
            company_name = company.name
            print 'in company ' + company.name 
        
            existingIntegration = CompanyIntegration.objects(company_id = company_id).first()
            if existingIntegration is None: # no integration found so move to next company
                logs.append('No integration record for company ' + str(company_name))
                continue
            else: #skip this company if initial or delta run are in progress
                if 'initial_run_in_process' in existingIntegration and existingIntegration['initial_run_in_process'] == True:
                    logs.append('Initial run in process for company ' + str(company_name))
                    continue
                if 'delta_run_in_process' in existingIntegration and existingIntegration['delta_run_in_process'] == True:
                    logs.append('Delta run in process for company ' + str(company_name))
                    continue
                # look for either the last delta run date or the last initial run date
                sinceDateTime = None
                if 'delta_run_done' in existingIntegration:
                    if 'delta_run_last_date' in existingIntegration:
                        sinceDateTime = existingIntegration['delta_run_last_date']
                if sinceDateTime is None:
                    if 'initial_run_done' in existingIntegration:
                        if 'initial_run_last_date' in existingIntegration:
                            sinceDateTime = existingIntegration['initial_run_last_date']
                   
                if sinceDateTime is None:
                    logs.append('No start date for delta run for company ' + str(company_name))
                    continue
    
                sinceDateTime = int(time.mktime(time.strptime(_str_from_date(sinceDateTime), '%Y-%m-%dT%H:%M:%SZ')))
                sinceDateTime -= int(12*60*60) #move back 12 hours as a safety measure
                sinceDateTime = sinceDateTime * 1000
                print 'calling extract with ' + str(sinceDateTime)
                companyDataExtract(user_id=None, company_id=company_id, run_type='delta', sinceDateTime=sinceDateTime)
                
    except Exception as e:
        logs.append(str(e))
        print 'exception is ' + str(e)
        
@app.task
def weeklyEmailCronJob():
    print 'in email cron'
    try:
        logs = [] #holds all error messages for the job
        # first get the superadmin user and the companies
        user = _get_superadmin()
        if user is None:
            mail_admins('Could not find super admin!', 'Check settings')
            return # no superadmin found
        # remotely login the user
        host = settings.BASE_URL
        url = host + '/api/v1/auth/login/'
        creds = {'email': 'super@claritix.io', 'password':'sudha123'}
        s = requests.Session()
        resp = s.post(url, data=json.dumps(creds))
        print 'resp is ' + str(resp.status_code)
        if not resp.status_code == 200:
            mail_admins('Could not login super admin!', 'Check credentials')
            logs.append('Could not login super admin!')
            return
        else:
            logs.append('Superadmin logged in')
        
        cookies = dict(sessionid = resp.cookies['sessionid'])
        url = host + '/api/v1/users/'
        resp = s.get(url, cookies=cookies)
        #print 'resp2 is ' + str(resp.status_code)
            
        #print str(logs)
        
        querydict = {'company_id__ne' : 0}
        companies = Company.objects(**querydict)
        print 'found companies ' + str(len(companies))
        #now loop through each company find which systems are connected 
        for company in companies:
            if not company.weekly_email:
                continue
            company_id = company.company_id
            company_name = company.name
            print 'in company ' + company.name 
        
            # get dates from last Sunday to this Saturday
            today = datetime.datetime.now()
            start = today - datetime.timedelta((today.weekday() + 1) % 7) #this will give Mon = 0 all the way to Sat = 6
            sat = start + relativedelta.relativedelta(weekday=relativedelta.SA(-1))
            sun = sat + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
            
            #convert date strings to timestamps
            start_date = time.mktime(sun.timetuple()) * 1000
            end_date = time.mktime(sat.timetuple()) * 1000
            print 'start date ' + str(start_date)
            print 'end date ' + str(end_date)
            companyWeeklyEmail(company_id=company_id, start_date=start_date, end_date=end_date)
                
    except Exception as e:
        logs.append(str(e))
        print 'exception during weekly cron job is ' + str(e)