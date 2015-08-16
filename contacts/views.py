import datetime, json
from datetime import timedelta, date, datetime
import pytz

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from django.core import serializers
#from django.contrib.auth.decorators import login_required

from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer

from rest_framework_mongoengine import generics as drfme_generics

from celery import task
from pickle import NONE
from mongoengine.django.shortcuts import get_document_or_404
from mongoengine.queryset.visitor import Q

from integrations.views import Marketo, Salesforce #, get_sfdc_test
from leads.serializers import LeadSerializer
from leads.models import Lead
from contacts.tasks import retrieveMktoContacts, retrieveSfdcContacts, retrieveHsptContacts
# get leads 

#@api_view(['GET'])
class LeadsViewSet(drfme_generics.ListCreateAPIView): #deprecated
    
    serializer_class = LeadSerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            #print 'no code'
            company_id = self.request.user.company_id
            page_number = self.request.GET.get('page_number')
            items_per_page = 10
            offset = (page_number - 1) * items_per_page
            total = Lead.objects.filter(company_id=company_id).count()
            
            queryset = Lead.objects.filter(company_id=company_id).skip(offset).limit(items_per_page)
            
        return queryset
    
#     def list(self, request, account_username=None):
#         account = Account.objects.filter(username=account_username)
#         try:
#             if 0 < len(account):
#                 #serializedList = LeadSerializer(Lead.objects(), many=True)
#                 #return Response(serializedList.data)
#                 
#                 result = saveMktoLeads(request)
#                 return Response(result)
#             else:
#                 return Response("User " + account_username + " does not exist")
#         except Exception as e:
#             return Response(str(e))

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAllLeads(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        total = Lead.objects.filter(company_id=company_id).count()
        
        queryset = Lead.objects.filter(company_id=company_id).skip(offset).limit(items_per_page)
        
        serializer = LeadSerializer(queryset, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeads(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    lead_type = request.GET.get('lead_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
     
    try:
        leads = []
        
        if lead_type is not None:
            date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' }
            start_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__gte'
            end_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__lte'
            if query_type == "strict": # for the Contacts Distribution chart
                stage_field_map = { "Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer' }
                stage_field_qry = 'leads__hspt__properties__lifecyclestage'
        else:
            start_date_field_qry = 'leads__hspt__properties__createdate__gte'
            end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        if query_type == "strict":
            querydict = {company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[lead_type]} #end_date_field_qry : local_end_date, 
            #print 'qmap is ' + str(querydict)
        else:
            querydict = {company_field_qry: company_id, end_date_field_qry : local_start_date} #, end_date_field_qry : local_end_date
        
        #print 'qd is ' + str(querydict)
        
        if query_type == "strict": #we are done
            total = Lead.objects(**querydict).count()
            leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        else: #not done. need to loop through leads to find which leads truly meet the criteria
            leads_temp = Lead.objects(**querydict)
            for lead in leads_temp:
                include_this_lead = True
                properties = lead.leads['hspt']['properties']
                
                if lead_type == 'Subscribers':
                    if "hs_lifecyclestage_lead_date" in properties:
                        current_stage = "Leads"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_marketingqualifiedlead_date" in properties:
                        current_stage = "MQLs"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_salesqualifiedlead_date" in properties:
                        current_stage = "SQLs"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_opportunity_date" in properties:
                        current_stage = "Opportunities"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_customer_date" in properties:
                        current_stage = "Customers"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                
                if lead_type == 'Leads':
                    if include_this_lead == True and "hs_lifecyclestage_marketingqualifiedlead_date" in properties:
                        current_stage = "MQLs"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_salesqualifiedlead_date" in properties:
                        current_stage = "SQLs"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_opportunity_date" in properties:
                        current_stage = "Opportunities"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_customer_date" in properties:
                        current_stage = "Customers"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                            
                if lead_type == 'MQLs':
                    if include_this_lead == True and "hs_lifecyclestage_salesqualifiedlead_date" in properties:
                        current_stage = "SQLs"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_opportunity_date" in properties:
                        current_stage = "Opportunities"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_customer_date" in properties:
                        current_stage = "Customers"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                            
                if lead_type == 'SQLs':
                    if include_this_lead == True and "hs_lifecyclestage_opportunity_date" in properties:
                        current_stage = "Opportunities"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                    if include_this_lead == True and "hs_lifecyclestage_customer_date" in properties:
                        current_stage = "Customers"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                            
                if lead_type == 'Opportunities':
                    if include_this_lead == True and "hs_lifecyclestage_customer_date" in properties:
                        current_stage = "Customers"
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= local_start_date:
                            include_this_lead = False
                
                if include_this_lead == True:
                    leads.append(lead)
            
            total = len(leads)
            leads = leads[offset:offset + items_per_page]
            
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
    

#filter leads for Pipeline Duration chart
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsByDuration(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    lead_type = request.GET.get('lead_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
     
    try:
        
        leads = []
        new_leads = []
        lead_type_temp = ""
        
        if lead_type is not None:
            
            date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' }
            company_field_qry = 'company_id'
             # for the Contacts Distribution chart
            stage_field_map = { "Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer' }
            stage_field_qry = 'leads__hspt__properties__lifecyclestage'
            if lead_type != "All":
                start_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__gte'
                end_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__lte'
                querydict = {company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[lead_type]}
                total = Lead.objects(**querydict).count()
                leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
            else:
                lead_type_temp = "All"
                #start_date_field_qry = 'leads__hspt__properties__createdate__gte'
                #end_date_field_qry = 'leads__hspt__properties__createdate__lte'
                #querydict = {company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
                querydict = {company_field_qry: company_id}
                leads_temp = Lead.objects(**querydict)#.skip(offset).limit(items_per_page)
                
                for lead_temp in leads_temp:
                    this_lead_stage_temp = lead_temp['leads']['hspt']['properties']['lifecyclestage']
                    for k, v in stage_field_map.items():
                        if v == this_lead_stage_temp:
                            this_lead_stage = k
                            print 'this lead str is ' + str(this_lead_stage) + 'and id is ' + lead_temp['hspt_id']
                            break
                    started_this_stage_date = lead_temp['leads']['hspt']['properties'][date_field_map[this_lead_stage]]
                    #print 'dates ' + str(local_start_date_naive) + ' XX ' + str(started_this_stage_date) + ' XX ' + str(local_end_date_naive)
                    if local_start_date_naive <= started_this_stage_date and started_this_stage_date <= local_end_date_naive:
                        leads.append(lead_temp)
                #we have all the leads for All so now apply offset and items per page
                total = len(leads)
                #print 'total for All is ' + str(total)
                leads = leads[offset:offset + items_per_page]
            #print 'qmap is ' + str(querydict)
            print 'qd2 is ' + str(querydict)
            #print 'in there ' + str(len(leads)) 
            for lead in leads: # iterate over each lead
                #print ' lead id is ' + lead['hspt_id']
                lead_props = lead['leads']['hspt']['properties']
                if  lead_type_temp == "All": # if it is all, find the lead stsage from lead record
                    this_lead_stage = lead_props['lifecyclestage']
                    for stage, stagename in stage_field_map.iteritems():
                        if stagename == this_lead_stage:
                            lead_type = stage 
                #print 'lead type is ' + lead_type
                #handle average days in current stage 
                if date_field_map[lead_type] not in lead['leads']['hspt']['properties']:
                    raise ValueError("This is not possible")
                
                started_this_stage_date = lead_props[date_field_map[lead_type]]
                days_in_this_stage = (utc_current_date - started_this_stage_date).total_seconds() #remove conversion to seconds if you want dates; use .days then - no ()
                lead['leads']['hspt']['properties']['days_in_this_stage'] = days_in_this_stage
                if (query_type != "strict"): #only get days in current stage so ignore the below
                #handle transition days
                    if lead_type == "Customers":
                        stage_date1 = lead_props.get('hs_lifecyclestage_opportunity_date')
                        stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date1 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date1).total_seconds() # change for number of days
                            lead['leads']['hspt']['properties']["last_stage"] = "Opportunity"
                        elif stage_date1 is  None:
                            if stage_date2 is not None:
                                lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date2).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "SQL"
                            else: 
                                if stage_date3 is not None:
                                    lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date3).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                                else:
                                    if stage_date4 is not None:
                                        lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date4).total_seconds()
                                        lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                                    else:
                                        if stage_date5 is not None:
                                            lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date5).total_seconds()
                                            lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                        
                        if last_stage == "Opportunity":                    
                            if stage_date2 is not None and stage_date1 is not None:
                                lead['leads']['hspt']['properties']["SO"] = (stage_date1 - stage_date2).total_seconds()
                                last_stage = "SQL"
                            elif stage_date2 is None: 
                                if stage_date3 is not None:
                                    lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date3).total_seconds()
                                    last_stage = "MQL"
                                else:
                                    if stage_date4 is not None:
                                        lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date4).total_seconds()
                                        last_stage = "Lead"
                                    else:
                                        if stage_date5 is not None:
                                            lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date5).total_seconds()
                                            last_stage = "Subscriber"
                        
                        if last_stage == "SQL":     
                            if stage_date3 is not None and stage_date2 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (stage_date2 - stage_date3).total_seconds()
                                last_stage = "MQL"
                            elif stage_date3 is None:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                    last_stage = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                             
                        if last_stage == "MQL":    
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                         
                        if last_stage == "Lead":                
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                        
                    elif lead_type == "Opportunities":
                        stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date2 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date2).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "SQL"
                        elif stage_date2 is None: 
                            if stage_date3 is not None:
                                lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date3).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                            else:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date4).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date5).total_seconds()
                                        lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                         
                        if last_stage == "SQL":   
                            if stage_date3 is not None and stage_date2 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (stage_date2 - stage_date3).total_seconds()
                                last_stage = "MQL"
                            elif stage_date3 is None:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                    last_stage = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                             
                        if last_stage == "MQL": 
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                        
                        if last_stage == "Lead":              
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                                
                    elif lead_type == "SQLs":
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date3 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date3).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                        elif stage_date3 is None:
                            if stage_date4 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                            else:
                                if stage_date5 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                         
                        if last_stage == "MQL": 
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                                      
                        if last_stage == "Lead":
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                            
                    elif lead_type == "MQLs":
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date4 is not None and started_this_stage_date is not None: 
                            lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date4).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                        elif stage_date4 is None:
                                if stage_date5 is not None:
                                    lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                        
                        if last_stage == "Lead":          
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                                
                    elif lead_type == "Leads":
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        if stage_date5 is not None and started_this_stage_date is not None: 
                            lead['leads']['hspt']['properties']["SL"] = (started_this_stage_date - stage_date5).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                            
                new_leads.append(lead)
            #print 'lead props are' + '\n'.join(str(p) for p in new_leads[0].leads["hspt"]["properties"])
            #print 'old lead props are' + '\n'.join(str(p) for p in lead)
            serializer = LeadSerializer(new_leads, many=True)   
            return JsonResponse({'count' : total, 'results': serializer.data})    
        else: #lead_type is None - not allowed here
            return JsonResponse({'Error' : 'Lead Type cannot be empty'})    
                
    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
#filter leads for Source Breakdown chart
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsBySource(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    source = request.GET.get('source')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
     
    try:
        
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        source_field_qry = 'leads__hspt__properties__hs_analytics_source'
        company_field_qry = 'company_id'
        
        querydict = {company_field_qry: company_id, source_field_qry: source, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
        total = Lead.objects(**querydict).count()
        leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})  
        
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
                       
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveContacts(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    company_id = request.user.company_id
    try:
        if code == 'mkto':
            result = retrieveMktoContacts.delay(user_id=user_id, company_id=company_id)
        elif code == 'sfdc': 
            result = retrieveSfdcContacts.delay(user_id=user_id, company_id=company_id)
        elif code == 'hspt': 
            result = retrieveHsptContacts.delay(user_id=user_id, company_id=company_id)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveContactsDaily(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    #company_id = request.user.company_id
    company_id = id
    try:
#         if code == 'mkto':
#             #result = retrieveMktoContacts.delay(user_id=user_id, company_id=company_id)
#             pass
#         elif code == 'sfdc': 
#             result = retrieveSfdcContactsDaily.delay(user_id=user_id, company_id=company_id)
#         elif code == 'hspt': 
#             pass
#             #result = retrieveHsptContacts.delay(user_id=user_id, company_id=company_id)
#         else:
#             result =  'Nothing to report'
        result = None
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
