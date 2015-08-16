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
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from analytics.serializers import SnapshotSerializer, BinderTemplateSerializer, BinderSerializer
from company.models import CompanyIntegration
from analytics.models import Snapshot, AnalyticsData, BinderTemplate, Binder

from superadmin.models import SuperIntegration, SuperAnalytics
from superadmin.serializers import SuperAnalyticsSerializer

from authentication.models import Company, CustomUser

from analytics.tasks import calculateHsptAnalytics, calculateMktoAnalytics, calculateSfdcAnalytics, calculateBufrAnalytics, calculateGoogAnalytics

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
    method_map = { "funnel" : hspt_funnel}
    result = method_map[dashboard_name](user_id, company_id, start_date, end_date, dashboard_name)
    return result



# start of HSPT
# first dashboard - 'Funnel"
def hspt_funnel(user_id, company_id, start_date, end_date, dashboard_name): 
    try:
        original_start_date = start_date
        original_end_date = end_date
        start_date = datetime.fromtimestamp(float(start_date))
        end_date = datetime.fromtimestamp(float(end_date))#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        subscriber_values_temp_array = {}
        subscriber_values_array = []
        lead_values_temp_array = {}
        lead_values_array = []
        mql_values_temp_array = {}
        mql_values_array = []
        sql_values_temp_array = {}
        sql_values_array = []
        opp_values_temp_array = {}
        opp_values_array = []
        customer_values_temp_array = {}
        customer_values_array = []
        all_dates = []
        delta = timedelta(days=1)
        e = local_end_date
        #print 'local end date is ' + str(local_end_date)
     
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        results = {}
        
        #get all leads which were created before the start of the period by source
        hspt_id_qry = 'hspt_id__exists'
        created_date_end_qry = 'source_created_date__lte'
        created_date_start_qry = 'source_created_date__gte'
        
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_end_qry: local_start_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_existed_source = Lead.objects(**querydict).item_frequencies('source_source')
        leads_existed_stage = Lead.objects(**querydict).item_frequencies('source_stage')
        existed_count = Lead.objects(**querydict).count()
        #get all leads that were created in this time period by source
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_created_source = Lead.objects(**querydict).item_frequencies('source_source')
        leads_created_stage = Lead.objects(**querydict).item_frequencies('source_stage')
        created_count = Lead.objects(**querydict).count()
        if existed_count > 0:
            percentage_increase = float( created_count / existed_count ) * 100
        else:
            percentage_increase = 0
        #get all leads that were created in this time period and still exist as subscribers
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_subscriber_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_subscriber_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_subscribers = Lead.objects(**querydict).count()
        #find average duration they have been subscribers
        leads_avg_subscriber_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_subscriber_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_subscribers' : { '$avg' : '$diff'}}})
        leads_avg_subscriber_duration = list(leads_avg_subscriber_duration)[0]['averageDuration_subscribers']
        leads_avg_subscriber_duration = abs(round(float(leads_avg_subscriber_duration / 1000 / 60 / 60 / 24 ), 0))
        #get all leads that were created in this time period and are now Leads
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_lead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_lead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_leads = Lead.objects(**querydict).count()
        #find average duration they have been leads
        leads_avg_lead_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_lead_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_leads' : { '$avg' : '$diff'}}})
        leads_avg_lead_duration = list(leads_avg_lead_duration)[0]['averageDuration_leads']
        leads_avg_lead_duration = abs(round(float(leads_avg_lead_duration / 1000 / 60 / 60 / 24 ), 0))
        
        #get all leads that were created in this time period and are now MQLS
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_marketingqualifiedlead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_marketingqualifiedlead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_mqls = Lead.objects(**querydict).count()
        #find average duration they have been MQLs
        leads_avg_mql_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_mql_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_mqls' : { '$avg' : '$diff'}}})
        leads_avg_mql_duration = list(leads_avg_mql_duration)[0]['averageDuration_mqls']
        leads_avg_mql_duration = abs(round(float(leads_avg_mql_duration / 1000 / 60 / 60 / 24 ), 0))
        
        #get all leads that were created in this time period and are now SQLS
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_salesqualifiedlead_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_salesqualifiedlead_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_sqls = Lead.objects(**querydict).count()
        #find average duration they have been SQLs
        leads_avg_sql_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_sql_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_sqls' : { '$avg' : '$diff'}}})
        leads_avg_sql_duration = list(leads_avg_sql_duration)[0]['averageDuration_sqls']
        leads_avg_sql_duration = abs(round(float(leads_avg_sql_duration / 1000 / 60 / 60 / 24 ), 0))
        
        #get all leads that were created in this time period and are now Opps
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_lifecyclestage_opportunity_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_opportunity_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_opps = Lead.objects(**querydict).count()
        #find average duration they have been Opps
        leads_avg_opp_duration = Lead.objects(**querydict).aggregate({ '$project': { 'diff': { '$subtract': ['$hspt_opp_date', local_end_date] } } }, {'$group': {'_id' : None, 'averageDuration_opps' : { '$avg' : '$diff'}}})
        leads_avg_opp_duration = list(leads_avg_opp_duration)[0]['averageDuration_opps']
        leads_avg_opp_duration = abs(round(float(leads_avg_opp_duration / 1000 / 60 / 60 / 24 ), 0))
        
        #get all leads that were created in this time period and are now Opps
        querydict = {company_field_qry: company_id, hspt_id_qry: True, created_date_start_qry: local_start_date, created_date_end_qry: local_end_date, 'leads__hspt__properties__hs_customer_customer_date__gte': local_start_date, 'leads__hspt__properties__hs_lifecyclestage_customer_date__lte': local_end_date} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        leads_customers = Lead.objects(**querydict).count()
        #get all deals closed in this time period
        hspt_opp_qry = 'opportunities__hspt__properties__dealstage__value'
        hspt_opp_close_date_start_qry = 'opportunities__hspt__properties__closedate__value__gte'
        hspt_opp_close_date_end_qry = 'opportunities__hspt__properties__closedate__value__lte'
        #print 'original start date is ' + str(int(original_start_date) * 1000)
        querydict = {company_field_qry: company_id, hspt_opp_qry: 'closedwon', hspt_opp_close_date_start_qry: str(int(original_start_date) * 1000), hspt_opp_close_date_end_qry: str(int(original_end_date) * 1000)} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        deals_total_value = Lead.objects(**querydict).aggregate({'$unwind': '$opportunities.hspt'}, {'$group': {'_id' : '$_id', 'totalDealValue' : { '$max' : '$opportunities.hspt.properties.amount.value'}}})
        closed_deal_value = 0
        max_deal_value = 0
        for deal in list(deals_total_value):
            closed_deal_value += int(deal['totalDealValue'])
            if int(deal['totalDealValue']) > max_deal_value:
                max_deal_value = int(deal['totalDealValue'])
        #print 'deal val is ' + str(closed_deal_value)
        #put all the results together
        results = {'start_date' : local_start_date.strftime('%Y-%m-%d'), 'end_date' : local_end_date.strftime('%Y-%m-%d'), 'existed_count': existed_count, 'created_count': created_count, 'existed_source' : leads_existed_source, 'created_source' : leads_created_source, 'existed_stage' : leads_existed_stage, 'created_stage' : leads_created_stage, 'percentage_increase' : percentage_increase, 'leads_subscribers': leads_subscribers, 'leads_leads': leads_leads, 'leads_mqls': leads_mqls, 'leads_sqls': leads_sqls, 'leads_opps': leads_opps, 'leads_customers': leads_customers, 'leads_avg_subscriber_duration': leads_avg_subscriber_duration, 'leads_avg_lead_duration': leads_avg_lead_duration, 'leads_avg_mql_duration': leads_avg_mql_duration, 'leads_avg_sql_duration': leads_avg_sql_duration, 'leads_avg_opp_duration': leads_avg_opp_duration, 'closed_deal_value' : closed_deal_value, 'max_deal_value': max_deal_value}
        return results
        
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

#second chart - "Contacts  Distribution"   
def hspt_contacts_distr_chart(user_id, company_id, start_date, end_date, chart_name): 
    #print 'orig start' + str(start_date)
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        
        e = local_end_date
        s = local_start_date - timedelta(days=1)
        end_key = e.strftime('%Y-%m-%d')
         
        all_values = {}
        all_dates = []
        all_totals = {}
        all_inflows = {}
        all_outflows = {}
        delta = timedelta(days=1)
        result = []
       
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_query = 'date'
           
        while s < (e - delta):
            s += delta #increment the day counter
            start_key = s.strftime('%Y-%m-%d')
            
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: start_key} 
            
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            if existingData is None: #  no results found for day so move to next day
                continue
            data = existingData['results']
                        
            for key in data.keys():
                if key == 'Unassigned' or key == 'Open':
                    continue
                if  s == local_start_date:
                    all_totals[key]= data[key]['total']   
                print 's is ' + str(s) + ' and e is ' + str(e - delta)     
                if start_key == end_key:
                    print 'last date'
                    if  key not in all_totals:
                        all_totals[key]= data[key]['total'] 
                        #raise ValueError('This should never happen'
                    else:
                        all_totals[key] -= data[key]['total'] 
                if  key not in all_inflows:
                    all_inflows[key]= data[key]['inflows']  
                else:
                    all_inflows[key] += data[key]['inflows']  
                if  key not in all_outflows:
                    all_outflows[key]= data[key]['outflows'] 
                else:
                    all_outflows[key] += data[key]['outflows'] 
            
                
        #print 'all vals is ' + str(all_values)
        values = []    
        for stage in all_totals.keys():
            values.append({'label' : stage, 'value' : all_totals[stage]})
        result.append({'key' : 'Total', 'values': values })                   
        
        values = []    
        for stage in all_inflows.keys():
            values.append({'label' : stage, 'value' : all_inflows[stage]})
        result.append({'key' : 'Inflow', 'values': values, 'color': '#bedb39' }) 
        
        values = []    
        for stage in all_outflows.keys():
            values.append({'label' : stage, 'value' : all_outflows[stage]})
        result.append({'key' : 'Outflow', 'values': values, 'color': '#fd7400' }) 
        #print str(result)
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)}) 
#         start_key = local_start_date.strftime('%Y-%m-%d')
#         end_key = local_end_date.strftime('%Y-%m-%d')
#         date_range = start_key + ' - ' + end_key
#         print 'date range is ' + date_range
#         company_field_qry = 'company_id'
#         chart_name_qry = 'chart_name'
#         date_range_qry = 'date_range'
#         
#         querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_range_qry: date_range} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
#         existingData = AnalyticsData.objects(**querydict).only('results').first()
#         result = []
#         
#         if existingData is None:
#             return result
#         else:
#             existingData = existingData['results']     
# 
#         
#         subscriber_object = {'label' : 'Subscribers', 'value': existingData['Subscribers']}
#         lead_object = {'label' : 'Leads', 'value': existingData['Leads']}
#         mql_object = {'label' : 'MQLs', 'value': existingData['MQLs']}
#         sql_object = {'label' : 'SQLs', 'value': existingData['SQLs']}
#         opp_object = {'label' : 'Opportunities', 'value': existingData['Opportunities']}
#         customer_object = {'label' : 'Customers', 'value': existingData['Customers']}
#         
#         result.append(subscriber_object)
#         result.append(lead_object)
#         result.append(mql_object)
#         result.append(sql_object)
#         result.append(opp_object)
#         result.append(customer_object)
#         
#         result_final = {}
#         result_final["key"] = "Contacts Distribution"
#         result_final["values"] = result
#         
#         result_final_array = []
#         result_final_array.append(result_final)
#         #print str(result)
#         return result_final_array
#     except Exception as e:
#         print 'exception is ' + str(e) 
#         return JsonResponse({'Error' : str(e)})       
  
  
def hspt_contacts_pipeline_duration(user_id, company_id, start_date, end_date, chart_name):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        start_key = local_start_date.strftime('%m-%d-%Y')
        end_key = local_end_date.strftime('%m-%d-%Y')
        date_range = start_key + ' - ' + end_key
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_range_qry = 'date_range'
        
        querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_range_qry: date_range} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
        existingData = AnalyticsData.objects(**querydict).only('results').first()
        result = [] 
        
        if existingData is None:
            return result
        else:
            existingData = existingData['results']    
        
          
        for key in existingData.keys():
            color='#bedb39' if key == 'Days in current status' else None
            area=True if key == 'Days in current status' else False
            color='#004358' if key =='All' else None
            result.append({'values': existingData[key], 'key': key, 'color': color, 'area': area})

        return result
        
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
       
def hspt_contacts_sources_pie(user_id, company_id, start_date, end_date, chart_name):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #utc_current_date = datetime.utcnow()   
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
       
        result = [] 
        source_distr = {}
        delta = timedelta(days=1)
        e = local_end_date
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + str(date)
            querydict = {date_qry: date, chart_name_qry: chart_name, company_field_qry: company_id} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            existingData = AnalyticsData.objects(**querydict).first()
            if existingData is None:
                continue
            
            for key in existingData['results']:
                decoded_key = decodeKey(key)
                if decoded_key in source_distr.keys():
                    source_distr[decoded_key] += existingData['results'][key]
                else:
                    source_distr[decoded_key] = existingData['results'][key]
                              
       
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})

def hspt_contacts_revenue_sources_pie(user_id, company_id, start_date, end_date, chart_name):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #utc_current_date = datetime.utcnow()   
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
       
        result = [] 
        source_distr = {}
        delta = timedelta(days=1)
        e = local_end_date
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%Y-%m-%d')
            print 'date is ' + str(date)
            querydict = {date_qry: date, chart_name_qry: chart_name, company_field_qry: company_id} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            existingData = AnalyticsData.objects(**querydict).first()
            if existingData is None:
                continue
            
            for key in existingData['results']:
                print 'found value ' + str(existingData['results'][key]['closed'])
                decoded_key = decodeKey(key)
                if decoded_key in source_distr.keys():
                    source_distr[decoded_key] += existingData['results'][key]['closed']
                else:
                    source_distr[decoded_key] = existingData['results'][key]['closed']
                              
        print 'r is ' + str(source_distr)
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# For chart - 'Website Traffic"
def hspt_website_traffic_bar(user_id, company_id, start_date, end_date, chart_name): 
    #print 'orig start' + str(start_date)
    try:
     
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        e = local_end_date
        s = local_start_date - timedelta(days=1)
         
        all_values = {}
        all_dates = []
        delta = timedelta(days=1)
        result = []
         
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_query = 'date'
        data = None
        channels = {'email': 0, 'direct': 0, 'social': 0, 'paid': 0, 'other': 0} 
           
        while s < (e - delta):
            s += delta #increment the day counter
            array_key = s.strftime('%Y-%m-%d')
            print 'date key is ' + array_key
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: array_key} 
            
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            if existingData is None: #  no results found for day so move to next day
                continue
            data = existingData['results']
        
            for key in channels.keys():
                if  key not in all_values: #and key != 'offline'
                    all_values[key]= {} 
                if key in data.keys(): 
                    if 'visits' in data[key]:
                        all_values[key][array_key] = data[key]['visits']
                    else:    
                        all_values[key][array_key] = 0
                else:    
                        all_values[key][array_key] = 0
                
        #print 'all vals is ' + str(all_values)
        if data is None:
            return []
           
        for stage in channels.keys():
            obj_array = []
            for key in all_values[stage].keys():
                obj = {'x' : key, 'y': all_values[stage][key]}
                obj_array.append(obj)  
            result.append({'key' : stage, 'values': obj_array })                   
        #print str(result)
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})        


def hspt_contacts_sources_pie_deprecated(user_id, company_id, start_date, end_date, chart_name):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #utc_current_date = datetime.utcnow()   
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
       
        result = [] 
        source_distr = {}
        delta = timedelta(days=1)
        e = local_end_date
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%m-%d-%Y')
            print 'date is ' + str(date)
            querydict = {date_qry: date, chart_name_qry: chart_name, company_field_qry: company_id} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            existingData = AnalyticsData.objects(**querydict).first()
            if existingData is None:
                continue
            
            for key in existingData['results']:
                if key in source_distr.keys():
                    source_distr[key] += existingData['results'][key]
                else:
                    source_distr[key] = existingData['results'][key]
                              
       
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
    

#get revenue (from HSPT) by source (from HSPT); needs the HSPT lead record to exist
def hspt_contacts_revenue_sources_pie_deprecated(user_id, company_id, start_date, end_date, chart_name):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #utc_current_date = datetime.utcnow()   
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        
        result = [] 
        source_distr = {}
        delta = timedelta(days=1)
        e = local_end_date
        
        s = local_start_date - timedelta(days=1)
        while s < (e - delta):
            s += delta #increment the day counter
            date = s.strftime('%m-%d-%Y')
            print 'date is ' + str(date)
            querydict = {date_qry: date, chart_name_qry: chart_name, company_field_qry: company_id} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            existingData = AnalyticsData.objects(**querydict).first()
            
            for key in existingData['results']:
                if key in source_distr.keys():
                    source_distr[key] += existingData['results'][key]
                else:
                    source_distr[key] = existingData['results'][key]
                              
       
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
# start of BUFR
# first chart - 'Tw Performance"
def tw_performance_bar_chart(user_id, company_id, start_date, end_date, chart_name):
    try:
     
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        e = local_end_date
        s = local_start_date - timedelta(days=1)
         
        all_values = {}
        all_dates = []
        delta = timedelta(days=1)
        result = []
         
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_query = 'date'
        data = None
           
        while s < (e - delta):
            s += delta #increment the day counter
            array_key = s.strftime('%Y-%m-%d')
             
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: array_key} 
            
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            if existingData is None: #  no results found for day so move to next day
                continue
            data = existingData['results']
                        
            for key in data.keys():
                if  key not in all_values:
                        all_values[key]= {}    
                all_values[key][array_key] = data[key]
                
        #print 'all vals is ' + str(all_values)
        if data is None:
            return []
           
        for stage in data.keys():
            obj_array = []
            for key in all_values[stage].keys():
                obj = {'x' : key, 'y': all_values[stage][key]}
                obj_array.append(obj)  
            result.append({'key' : stage, 'values': obj_array })                   
        #print str(result)
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})  

#Google charts    
# For chart - 'Website Traffic"
def google_analytics_bar_chart(user_id, company_id, start_date, end_date, chart_name): 
    #print 'orig start' + str(start_date)
    try:
     
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        e = local_end_date
        s = local_start_date - timedelta(days=1)
         
        all_values = {}
        all_dates = []
        delta = timedelta(days=1)
        result = []
         
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_query = 'date'
        data = None
        userTypes = {'New': 0, 'Returning': 0} 
           
        while s < (e - delta):
            s += delta #increment the day counter
            array_key = s.strftime('%Y-%m-%d')
            print 'date key is ' + array_key
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: array_key} 
            
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            if existingData is None: #  no results found for day so move to next day
                data = {'New' : 0, 'Returning' : 0}
            else:
                data = existingData['results']
        
            for key in userTypes.keys():
                if  key not in all_values: #and key != 'offline'
                    all_values[key]= {} 
                if key in data.keys(): 
                    all_values[key][array_key] = data[key]
                else:    
                    all_values[key][array_key] = 0
                
        #print 'all vals is ' + str(all_values)
        if data is None:
            return []
           
        for type in userTypes.keys():
            obj_array = []
            for key in all_values[type].keys():
                obj = {'x' : key, 'y': all_values[type][key]}
                obj_array.append(obj)  
            result.append({'key' : type, 'values': obj_array })                   
        #print str(result)
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})        

#end of analytics
    
class SingleBinderTemplate(viewsets.ModelViewSet):  
    
    serializer_class = BinderTemplateSerializer
        
    def create(self, request, company_id=None):
        try:
            company = Company.objects.filter(company_id=company_id).first()
            
            data = json.loads(request.body)
            binder = data.get('binderTemplate', None)
            print 'binder is ' + str(binder)
            binderTemplate = BinderTemplate(owner=request.user.id, company=company) #
            binderTemplate.name = binder['name']
            binderTemplate.pages = binder['pages']
            binderTemplate.orientation = binder['orientation']
            binderTemplate.frequency = binder['frequency']
            binderTemplate.frequency_day = binder.get('frequency_day', None)
            binderTemplate.binder_count = 0;
            binderTemplate.save()
            if binderTemplate.frequency == 'One Time':
                print 'saving binder instance'
                singleBinder = SingleBinder()
                singleBinder.create(request, company_id, binderTemplate.id)
                if binderTemplate.binder_count is None:
                    binderTemplate.binder_count = 0;
                binderTemplate.binder_count += 1; #increment the count of binders for this template
                binderTemplate.save()
            binderTemplates = BinderTemplates() # get all binder templates
            return BinderTemplates.list(binderTemplates, request, company_id)
        except Exception as e:
            return Response(str(e))
            
            
class BinderTemplates(viewsets.ModelViewSet):  
    
    serializer_class = BinderTemplateSerializer
        
    def list(self, request, company_id=None):
        try:
            company = Company.objects.filter(company_id=company_id).first()    
            results = BinderTemplate.objects(company=company).all()
            serializedList = BinderTemplateSerializer(results, many=True)
            totalCount = BinderTemplate.objects(company=company.id).count()
            return JsonResponse({'results' : serializedList.data, 'count': totalCount})
        except Exception as e:
                return Response(str(e))    
            
            
class SingleBinder(viewsets.ModelViewSet):  
    serializer_class = BinderSerializer
          
    def create(self, request, company_id=None, binder_template_id=None):
        try:
            if binder_template_id is None: # this should never happen
                return JsonResponse({'message' : 'Cannot create binder without template ID'})
            company = Company.objects.filter(company_id=company_id).first()
            
            data = json.loads(request.body)
            binder = data.get('binder', None)
            if binder is None: # this will happen, for e.g., when the binder is being created auto from a One Time binder template 
                binder = Binder(owner=request.user.id, company=company) #
                binderTemplate = BinderTemplate.objects(id=binder_template_id).first()
                if binderTemplate is None:
                    return JsonResponse({'message' : 'Cannot create binder without template'})
                binder.name = binderTemplate.name
                binder.pages = binderTemplate.pages
                binder.binder_template = binderTemplate
                binder.save()
                results = BinderSerializer(binder, many=False)
                return JsonResponse({'results' : results})
        except Exception as e:
            return Response(str(e))
            
 
class Binders(viewsets.ModelViewSet):  
    
    serializer_class = BinderSerializer
        
    def list(self, request, company_id=None, binder_template_id=None):
        try:
            company = Company.objects.filter(company_id=company_id).first()    
            results = Binder.objects(Q(company=company) & Q(binder_template=binder_template_id))
            serializedList = BinderSerializer(results, many=True)
            #totalCount = BinderTemplate.objects(company=company.id).count()
            return JsonResponse({'results' : serializedList.data})
        except Exception as e:
                return Response(str(e))       