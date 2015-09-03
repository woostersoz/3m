import datetime, json, time
from datetime import timedelta, date, datetime
import pytz
import os
from collections import OrderedDict
from operator import itemgetter

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from mongoengine.queryset.visitor import Q
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

from leads.models import Lead
from leads.serializers import LeadSerializer
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from analytics.serializers import SnapshotSerializer, BinderTemplateSerializer, BinderSerializer
from company.models import CompanyIntegration
from analytics.models import Snapshot, AnalyticsData, AnalyticsIds, BinderTemplate, Binder

from superadmin.models import SuperIntegration, SuperAnalytics
from superadmin.serializers import SuperAnalyticsSerializer

from authentication.models import Company, CustomUser

from analytics.tasks import calculateHsptAnalytics, calculateMktoAnalytics, calculateSfdcAnalytics, calculateBufrAnalytics, calculateGoogAnalytics,\
    mkto_waterfall

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")


@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def calculateAnalytics(request, company_id): #,  
    chart_name = request.GET.get('chart_name')
    chart_title = request.GET.get('chart_title')
    system_type = request.GET.get('system_type')
    mode = request.GET.get('mode')
    start_date = request.GET.get('start_date')
    
    user_id = request.user.id
    #company_id = request.user.company_id
    
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system_type = SuperIntegration.objects(Q(code = source) & Q(system_type = system_type)).first()
                if defined_system_type is not None:
                    code = source
            #print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'mkto':
            result = calculateMktoAnalytics(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title, mode=mode, start_date=start_date)
        elif code == 'sfdc': 
            result = calculateSfdcAnalytics(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title, mode=mode, start_date=start_date)
        elif code == 'hspt': 
            result = calculateHsptAnalytics(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title, mode=mode, start_date=start_date)
        elif code == 'bufr': 
            result = calculateBufrAnalytics(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title, mode=mode, start_date=start_date)
        elif code == 'goog': 
            result = calculateGoogAnalytics(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title, mode=mode, start_date=start_date)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        print 'exception is ' + str(e)
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveDashboards(request, company_id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    dashboard_name = request.GET.get('dashboard_name')
    system_type = request.GET.get('system_type')
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system_type = SuperIntegration.objects(Q(code = source) & Q(system_type = system_type)).first()
                if defined_system_type is not None:
                    code = source
            #print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'hspt': 
            result = retrieveHsptDashboards(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, dashboard_name=dashboard_name)
        elif code == 'mkto': 
            result = retrieveMktoDashboards(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, dashboard_name=dashboard_name)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getDashboards(request, company_id):
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        charts_temp = []
        charts = []
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system = SuperIntegration.objects(code = source).first()
                if defined_system is not None:
                    charts_temp = SuperAnalytics.objects(system_type = defined_system.system_type).all()
                    for chart_temp in list(charts_temp):
                        serializer = SuperAnalyticsSerializer(chart_temp, many=False) 
                        charts.append(serializer.data)
        
        return JsonResponse({"results": charts}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

#@app.task
def retrieveHsptDashboards(user_id=None, company_id=None, dashboard_name=None, start_date=None, end_date=None):
    method_map = { "funnel" : hspt_funnel, "social" : hspt_social_roi, "waterfall" : None}
    result = method_map[dashboard_name](user_id, company_id, start_date, end_date, dashboard_name)
    return result

def retrieveMktoDashboards(user_id=None, company_id=None, dashboard_name=None, start_date=None, end_date=None):
    method_map = { "waterfall" : mkto_waterfall}
    result = method_map[dashboard_name](user_id, company_id, start_date, end_date, dashboard_name)
    return result

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def drilldownDashboards(request, company_id):
    
    system_type = request.GET.get('system_type')
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system_type = SuperIntegration.objects(Q(code = source) & Q(system_type = system_type)).first()
                if defined_system_type is not None:
                    code = source
                    client_secret = existingIntegration['integrations'][code]['client_secret']
            #print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'hspt': 
            result = drilldownHsptDashboards(request=request, company_id=company_id)
            result['portal_id'] = client_secret
        elif code == 'mkto': 
            result = drilldownMktoDashboards(request=request, company_id=company_id)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})


# start of HSPT
# dashboard - 'Funnel"
def hspt_funnel(user_id, company_id, start_date, end_date, dashboard_name):
    try:
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        days_list = []
        delta = local_end_date - local_start_date
        for i in range(delta.days + 1):
            days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
        
        #query parameters
        company_id_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date__in'
        chart_name = 'funnel'
        
        #other variables
        existed_count = 0
        created_count = 0
        leads_created_stage = {}
        leads_created_source = {}
        leads_inflow_count = {}
        leads_outflow_count = {}
        leads_outflow_duration = {}
        percentage_increase = 0
        closed_deal_value = 0
        max_deal_value = 0
        
        querydict = {company_id_qry: company_id, chart_name_qry: chart_name, date_qry: days_list}
        days = AnalyticsData.objects(**querydict)
        
        first_record_done = False
        
        for day in days:
            day = day['results']
            if first_record_done != True:
                existed_count = day['existed_count']
                first_record_done = True
            
            #increment all  variables
            for item, value in day['created_stage'].items():
                if item not in leads_created_stage:
                    leads_created_stage[item] = 0
                leads_created_stage[item] += value
                
            for item, value in day['created_source'].items():
                if item not in leads_created_source:
                    leads_created_source[item] = 0
                leads_created_source[item] += value  
                
            for item, value in day['inflow_count'].items():
                if item not in leads_inflow_count:
                    leads_inflow_count[item] = 0
                leads_inflow_count[item] += value 
                
            for item, value in day['outflow_count'].items():
                if item not in leads_outflow_count:
                    leads_outflow_count[item] = 0
                if value != 'N/A':
                    leads_outflow_count[item] += value  
                    
            for item, value in day['outflow_duration'].items():
                if item not in leads_outflow_duration:
                    leads_outflow_duration[item] = 0
                if value != 'N/A':
                    leads_outflow_duration[item] += value 
                
            created_count += day['created_count']
            closed_deal_value += day['closed_deal_value']
            if day['max_deal_value'] > max_deal_value:
                max_deal_value = day['max_deal_value']
         
        # do post-processing
        # get the average of the average outflow durations by dividing by the duration of the report
        for item, value in leads_outflow_duration.items():   
            leads_outflow_duration[item] = value / len(days_list)
            
        #get the percentage increase in number of contacts
        if int(existed_count) > 0:
            percentage_increase = (float(created_count) / existed_count) * 100
        else:
            percentage_increase = 0
        
        results = {'start_date' : local_start_date.strftime('%Y-%m-%d'), 'end_date' : local_end_date.strftime('%Y-%m-%d'), 'existed_count': existed_count, 'created_count': created_count,  'created_source' : leads_created_source,  'created_stage' : leads_created_stage, 'leads_inflow_count': leads_inflow_count, 'leads_outflow_count': leads_outflow_count, 'leads_outflow_duration': leads_outflow_duration, 'percentage_increase' : percentage_increase, 'closed_deal_value' : closed_deal_value, 'max_deal_value': max_deal_value}
        return results 
         
#     try:
#         original_start_date = start_date
#         original_end_date = end_date
#         start_date = datetime.fromtimestamp(float(start_date))
#         end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
#         
#         local_start_date = get_current_timezone().localize(start_date, is_dst=None)
#         local_end_date = get_current_timezone().localize(end_date, is_dst=None)
#     
#         subscriber_values_temp_array = {}
#         subscriber_values_array = []
#         lead_values_temp_array = {}
#         lead_values_array = []
#         mql_values_temp_array = {}
#         mql_values_array = []
#         sql_values_temp_array = {}
#         sql_values_array = []
#         opp_values_temp_array = {}
#         opp_values_array = []
#         customer_values_temp_array = {}
#         customer_values_array = []
#         all_dates = []
#         delta = timedelta(days=1)
#         e = local_end_date
#         #print 'local end date is ' + str(local_end_date)
#      
#         company_field_qry = 'company_id'
#         chart_name_qry = 'chart_name'
#         date_qry = 'date'
#         results = {}
#         
#         #get all leads which were created before the start of the period by source
#         hspt_id_qry = 'hspt_id__exists'
#         created_date_end_qry = 'source_created_date__lte'
#         created_date_start_qry = 'source_created_date__gte'
#         
#         querydict = {company_field_qry: company_id, created_date_end_qry: local_start_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_existed_source = Lead.objects(**querydict).item_frequencies('source_source')
#         leads_existed_stage = Lead.objects(**querydict).item_frequencies('source_stage')
#         existed_count = Lead.objects(**querydict).count()
#         #get all leads that were created in this time period by source
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_created_source = Lead.objects(**querydict).item_frequencies('source_source')
#         leads_created_stage = Lead.objects(**querydict).item_frequencies('source_stage')
#         created_count = Lead.objects(**querydict).count()
#         if existed_count > 0:
#             percentage_increase = float( created_count / existed_count ) * 100
#         else:
#             percentage_increase = 0
#         #get all leads that were created in this time period and still exist as subscribers
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_subscriber_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_subscriber_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_subscribers = Lead.objects(**querydict).count()
#         #find average duration they have been subscribers
#         leads_avg_subscriber_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_subscriber_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_subscribers' : { '$avg' : '$diff'}}})
#         listx = list(leads_avg_subscriber_duration)
#         if len(listx) > 0:
#             leads_avg_subscriber_duration = listx[0]['averageDuration_subscribers']
#             leads_avg_subscriber_duration = abs(round(float(leads_avg_subscriber_duration / 1000 / 60 / 60 / 24 ), 0))
#         else:
#             leads_avg_subscriber_duration = 'N/A'
#         #get all leads that were created in this time period and are now Leads
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_lead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_lead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_leads = Lead.objects(**querydict).count()
#         #find average duration they have been leads
#         listx = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_lead_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_leads' : { '$avg' : '$diff'}}})
#         listx = list(listx)
#         if len(listx) > 0:
#             leads_avg_lead_duration = listx[0]['averageDuration_leads']
#             leads_avg_lead_duration = abs(round(float(leads_avg_lead_duration / 1000 / 60 / 60 / 24 ), 0))
#         else:
#             leads_avg_lead_duration = 'N/A'
#         #get all leads that were created in this time period and are now MQLS
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_marketingqualifiedlead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_marketingqualifiedlead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_mqls = Lead.objects(**querydict).count()
#         #find average duration they have been MQLs
#         listy = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_mql_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_mqls' : { '$avg' : '$diff'}}})
#         listz = list(listy)
#         if len(listz) > 0:
#             leads_avg_mql_duration = listz[0]['averageDuration_mqls']
#             leads_avg_mql_duration = abs(round(float(leads_avg_mql_duration / 1000 / 60 / 60 / 24 ), 0))
#         else:
#             leads_avg_mql_duration = 'N/A'
#         #get all leads that were created in this time period and are now SQLS
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_salesqualifiedlead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_salesqualifiedlead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_sqls = Lead.objects(**querydict).count()
#         #find average duration they have been SQLs
#         lista = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_sql_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_sqls' : { '$avg' : '$diff'}}})
#         listb = list(lista) 
#         if len(listb) > 0:
#             leads_avg_sql_duration = listb[0].get('averageDuration_sqls', None)
#             leads_avg_sql_duration = abs(round(float(leads_avg_sql_duration / 1000 / 60 / 60 / 24 ), 0))
#         else:
#             leads_avg_sql_duration = 'N/A'
#         #get all leads that were created in this time period and are now Opps
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_opportunity_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_opportunity_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_opps = Lead.objects(**querydict).count()
#         #find average duration they have been Opps
#         listc = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_opp_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_opps' : { '$avg' : '$diff'}}})
#         listd = list(listc)
#         if len(listd) > 0:
#             leads_avg_opp_duration = listd[0]['averageDuration_opps']
#             leads_avg_opp_duration = abs(round(float(leads_avg_opp_duration / 1000 / 60 / 60 / 24 ), 0))
#         else:
#             leads_avg_opp_duration = 'N/A'
#         #get all leads that were created in this time period and are now Opps
#         querydict = {company_field_qry: company_id, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_customer_customer_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_customer_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         leads_customers = Lead.objects(**querydict).count()
#         #get all deals closed in this time period
#         hspt_opp_qry = 'opportunities__hspt__properties__dealstage__value'
#         hspt_opp_close_date_start_qry = 'opportunities__hspt__properties__closedate__value__gte'
#         hspt_opp_close_date_end_qry = 'opportunities__hspt__properties__closedate__value__lte'
#         #print 'original start date is ' + str(int(original_start_date) * 1000)
#         querydict = {company_field_qry: company_id, hspt_opp_close_date_start_qry: str(int(original_start_date) * 1000), hspt_opp_close_date_end_qry: str(int(original_end_date) * 1000)} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         deals_total_value = Lead.objects(**querydict).aggregate({'$unwind': '$opportunities.hspt'}, {'$group': {'_id' : '$_id', 'totalDealValue' : { '$max' : '$opportunities.hspt.properties.amount.value'}}})
#         closed_deal_value = 0
#         max_deal_value = 0
#         for deal in list(deals_total_value):
#             print 'total deal val is ' + deal['totalDealValue']
#             if not deal['totalDealValue']:
#                 continue
#             closed_deal_value += float(deal['totalDealValue'])
#             if float(deal['totalDealValue']) > max_deal_value:
#                 max_deal_value = float(deal['totalDealValue'])
#         #print 'deal val is ' + str(closed_deal_value)
#         #put all the results together
#         results = {'start_date' : local_start_date.strftime('%Y-%m-%d'), 'end_date' : local_end_date.strftime('%Y-%m-%d'), 'existed_count': existed_count, 'created_count': created_count, 'existed_source' : leads_existed_source, 'created_source' : leads_created_source, 'existed_stage' : leads_existed_stage, 'created_stage' : leads_created_stage, 'percentage_increase' : percentage_increase, 'leads_subscribers': leads_subscribers, 'leads_leads': leads_leads, 'leads_mqls': leads_mqls, 'leads_sqls': leads_sqls, 'leads_opps': leads_opps, 'leads_customers': leads_customers, 'leads_avg_subscriber_duration': leads_avg_subscriber_duration, 'leads_avg_lead_duration': leads_avg_lead_duration, 'leads_avg_mql_duration': leads_avg_mql_duration, 'leads_avg_sql_duration': leads_avg_sql_duration, 'leads_avg_opp_duration': leads_avg_opp_duration, 'closed_deal_value' : closed_deal_value, 'max_deal_value': max_deal_value}
#         return results
        
#         s = local_start_date - timedelta(days=1)
#         
#            
#         while s < (e - delta):
#             s += delta #increment the day counter
#             array_key = s.strftime('%Y-%m-%d')
#             
#             querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_qry: array_key} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#             existingData = AnalyticsData.objects(**querydict).only('results').first()
#             if existingData is None:
#                 continue
#             data = existingData['results']
#               
#             if 'Subscribers' in data:    
#                 subscriber_values_temp_array[array_key] = data['Subscribers']
#             else:
#                 subscriber_values_temp_array[array_key] = 0
#             if 'Leads' in data:    
#                 lead_values_temp_array[array_key] = data['Leads']
#             else:
#                 lead_values_temp_array[array_key] = 0
#             if 'MQLs' in data: 
#                 mql_values_temp_array[array_key] = data['MQLs']
#             else:
#                 mql_values_temp_array[array_key] = 0
#             if 'SQLs' in data: 
#                 sql_values_temp_array[array_key] = data['SQLs']
#             else:
#                 sql_values_temp_array[array_key] = 0
#             if 'Opportunities' in data: 
#                 opp_values_temp_array[array_key] = data['Opportunities']
#             else:
#                 opp_values_temp_array[array_key] = 0
#             if 'Customers' in data: 
#                 customer_values_temp_array[array_key] = data['Customers']
#             else:
#                 customer_values_temp_array[array_key] = 0
#                         
#         for key in subscriber_values_temp_array.keys():  
#             obj = {'x' : key, 'y': subscriber_values_temp_array[key]}
#             subscriber_values_array.append(obj)
#             
#         for key in lead_values_temp_array.keys():
#             obj = {'x' : key, 'y': lead_values_temp_array[key]}
#             lead_values_array.append(obj)
#             
#         for key in mql_values_temp_array.keys():
#             obj = {'x' : key, 'y': mql_values_temp_array[key]}
#             mql_values_array.append(obj)
#             
#         for key in sql_values_temp_array.keys():
#             obj = {'x' : key, 'y': sql_values_temp_array[key]}
#             sql_values_array.append(obj)
# 
#         for key in opp_values_temp_array.keys():
#             obj = {'x' : key, 'y': opp_values_temp_array[key]}
#             opp_values_array.append(obj)
# 
#         for key in customer_values_temp_array.keys():
#             obj = {'x' : key, 'y': customer_values_temp_array[key]}
#             customer_values_array.append(obj)
# 
#         result = []
#         subscriber_object = {'key' : 'Subscribers', 'values': subscriber_values_array}
#         lead_object = {'key' : 'Leads', 'values': lead_values_array}
#         mql_object = {'key' : 'MQLs', 'values': mql_values_array}
#         sql_object = {'key' : 'SQLs', 'values': sql_values_array}
#         opp_object = {'key' : 'Opportunities', 'values': opp_values_array}
#         customer_object = {'key' : 'Customers', 'values': customer_values_array}
#         
#         result.append(subscriber_object)
#         result.append(lead_object)
#         result.append(mql_object)
#         result.append(sql_object)
#         result.append(opp_object)
#         result.append(customer_object)
#         
#         #print str(result)
#         return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})        

      
# dashboard - 'Social"
def hspt_social_roi(user_id, company_id, start_date, end_date, dashboard_name): 
    try:
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        days_list = []
        delta = local_end_date - local_start_date
        for i in range(delta.days + 1):
            days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
        
        #query parameters
        company_id_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date__in'
        chart_name = 'social_roi'
        
        #all return variables
        social= {}
        social['Facebook'] = {}
        social['Facebook']['Organic'] = {'Likes': 0, 'Clicks': 0, 'Impressions': 0, 'Comments': 0, 'Shares': 0}
        social['Facebook']['Paid'] = {'Likes': 0, 'Clicks': 0, 'Impressions': 0, 'Comments': 0, 'Shares': 0}
        website = {}
        website['Facebook'] = {}
        website['Facebook']['Organic'] = {'Deals' : 0, 'Visits': 0, 'Contacts': 0, 'Leads': 0, 'Customers': 0}
        website['Facebook']['Paid']= {'Deals' : 0, 'Visits': 0, 'Contacts': 0, 'Leads': 0, 'Customers': 0}
        roi = {}
        roi['Facebook'] = {}
        roi['Facebook']['Organic']=  {'Spend': 0, 'Revenue': 0}
        roi['Facebook']['Paid']= {'Spend': 0, 'Revenue': 0}
        
        querydict = {company_id_qry: company_id, chart_name_qry: chart_name, date_qry: days_list}
        days = AnalyticsData.objects(**querydict)
        
        for day in days:
            data = day['results']
            social_data = data.get('Social', None)
            website_data = data.get('Website', None)
            fb_data = social_data.get('Facebook', None)
            
            if fb_data is not None:
                fb_organic_data = fb_data.get('Organic', None)
                if fb_organic_data is not None:
                    for record in fb_organic_data:
                        for key, value in record.items():
                            social['Facebook']['Organic']['Likes'] += value.get('like', 0)
                            social['Facebook']['Organic']['Clicks'] += value.get('link clicks', 0) + value.get('other clicks', 0)
                            social['Facebook']['Organic']['Impressions'] += value.get('page_impressions', 0)
                            social['Facebook']['Organic']['Comments'] += value.get('comment', 0)
                            social['Facebook']['Organic']['Shares'] += value.get('link', 0)
                fb_paid_data = fb_data.get('Paid', None)
                if fb_paid_data is not None:
                    for record in fb_paid_data:
                        for key, value in record.items():
                            social['Facebook']['Paid']['Likes'] += value.get('like', 0) + value.get('post_like', 0)
                            social['Facebook']['Paid']['Clicks'] += value.get('website_clicks', 0) 
                            social['Facebook']['Paid']['Impressions'] += int(value.get('impressions', 0))
                            social['Facebook']['Paid']['Comments'] += value.get('comment', 0)
                            social['Facebook']['Paid']['Shares'] += value.get('link', 0)
                            roi['Facebook']['Paid']['Spend'] += float(value.get('spend', 0))
            
            if website_data is not None:
                hspt = website_data.get('Hubspot', None)
                if hspt is not None:
                    social_data = hspt.get('social', None)
                    if social_data is not None:
                        fb_data = social_data.get('Facebook', None)
                        if fb_data is not None:
                            sections = {'Organic', 'Paid'}
                            for section in sections:
                                fb_section_data = fb_data.get(section, None)
                                if fb_section_data is not None:
                                    website['Facebook'][section]['Visits'] += fb_section_data['Total Visits']
                                    website['Facebook'][section]['Deals'] += len(fb_section_data['Deals'])
                                    roi['Facebook'][section]['Revenue'] += fb_section_data['Revenue']
                                    leads = fb_section_data.get('Leads', None)
                                    if leads is not None:
                                        website['Facebook'][section]['Leads'] += leads['Total']
                                    contacts = fb_section_data.get('Contacts', None)
                                    if contacts is not None:
                                        website['Facebook'][section]['Contacts'] += contacts['Total']
                                    customers = fb_section_data.get('Customers', None)
                                    if customers is not None:
                                        website['Facebook'][section]['Customers'] += customers['Total']
                        
        results = {'start_date' : local_start_date.strftime('%Y-%m-%d'), 'end_date' : local_end_date.strftime('%Y-%m-%d'), 'social' : social, 'website' : website, 'roi' : roi}
        return results
        
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})   
      
#Waterfall dashboard
def mkto_waterfall(user_id, company_id, start_date, end_date, dashboard_name): 
    try:
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        days_list = []
        delta = local_end_date - local_start_date
        for i in range(delta.days + 1):
            days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
        
        #query parameters
        company_id_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date__in'
        chart_name = 'waterfall'
        
        #other variables
        results = {}
        
        querydict = {company_id_qry: company_id, chart_name_qry: chart_name, date_qry: days_list}
        days = AnalyticsData.objects(**querydict)
        
        for day in days:
            day_results = day['results']
            for key, value in day_results.items():
                if key not in results:
                    results[key] = 0
                results[key] += value
        results['start_date'] = local_start_date.strftime('%Y-%m-%d') 
        results['end_date'] = local_end_date.strftime('%Y-%m-%d')      
        return results
            
            
            
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 


def drilldownHsptDashboards(request, company_id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    object = request.GET.get('object').capitalize()
    section = request.GET.get('section').capitalize()
    channel = request.GET.get('channel').capitalize()
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    offset = (page_number - 1) * items_per_page
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    
    #query parameters
    company_id_qry = 'company_id'
    chart_name_qry = 'chart_name'
    date_qry = 'date__in'
    chart_name = 'social_roi'
    
    #variables
    people = []
    deals = []
        
    try:     
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        days_list = []
        delta = local_end_date - local_start_date
        for i in range(delta.days + 1):
            days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
            
        querydict = {company_id_qry: company_id, chart_name_qry: chart_name, date_qry: days_list}
        days = AnalyticsData.objects(**querydict)
        
        #Contacts, Leads and Customers
        if (object == 'Contacts' or object == 'Leads' or object == 'Customers'):
            for day in days:
                data = day['results']
                try: 
                    people.extend(data['Website']['Hubspot']['social'][channel][section][object]['People'])
                except Exception as e:
                    continue
            
             
            results = {'results': people[offset:offset + items_per_page], 'count' : len(people) }   
            return results
        #Deals
        elif (object == 'Deals'):
            for day in days:
                data = day['results']
                try: 
                    deals.extend(data['Website']['Hubspot']['social'][channel][section]['Deals'])
                except Exception as e:
                    continue
            
             
            results = {'results': deals[offset:offset + items_per_page], 'count' : len(deals) }   
            return results
        
        
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})  

#Marketo dashboard drilldown    
def drilldownMktoDashboards(request, company_id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    object = request.GET.get('object')
    section = request.GET.get('section')
    channel = request.GET.get('channel')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    offset = (page_number - 1) * items_per_page
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    
    #query parameters
    company_id_qry = 'company_id'
    chart_name_qry = 'chart_name'
    date_qry = 'date__in'
    chart_name = 'waterfall'
    
    #variables
    people = {}
    people['sales'] = []
    people['mktg'] = []
    deals = []
        
    try:     
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        days_list = []
        delta = local_end_date - local_start_date
        for i in range(delta.days + 1):
            days_list.append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
            
        querydict = {company_id_qry: company_id, chart_name_qry: chart_name, date_qry: days_list}
        days = AnalyticsIds.objects(**querydict)
        #print 'obj is ' + str(channel)
        #Contacts, Leads and Customers
        if object == 'leads':
            for day in days:
                data = day['results']
                if section == "all":
                    try: 
                        key = 'mktg_' + channel if channel != 'mql' else channel
                        people['mktg'].extend(data[key])
                        key = 'sales_' + channel if channel != 'mql' else channel
                        people['sales'].extend(data[key])
                    except Exception as e:
                        print 'exception is ' + str(e)
                        continue
                else:
                    try: 
                        key = section + '_' + channel if channel != 'mql' else channel
                        people[section].extend(data[key])
                    except Exception as e:
                        print 'exception is ' + str(e)
                        continue
            print 'got ids ' + str(time.time())
            if section == "all":        
                leads = Lead.objects(company_id=company_id, mkto_id__in=people['mktg'])
                leads_list = list(leads)
                leads = Lead.objects(company_id=company_id, sfdc_id__in=people['sales'])
                leads_list.extend(list(leads))
            elif section == 'mktg':
                leads = Lead.objects(company_id=company_id, mkto_id__in=people['mktg'])
                leads_list = list(leads)
            elif section == 'sales':
                leads = Lead.objects(company_id=company_id, sfdc_id__in=people['sales'])
                leads_list = list(leads)
            print 'got leads ' + str(time.time())
            serializer = LeadSerializer(leads_list[offset:offset + items_per_page], many=True) 
            print 'got results ' + str(time.time()) 
            results = {'results': serializer.data, 'count' : len(leads_list) }   
            return results
        #Deals
        elif (object == 'Deals'):
            for day in days:
                data = day['results']
                try: 
                    deals.extend(data['Website']['Hubspot']['social'][channel][section]['Deals'])
                except Exception as e:
                    continue
            
             
            results = {'results': deals[offset:offset + items_per_page], 'count' : len(deals) }   
            return results
        
        
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})    