import datetime, json
from datetime import timedelta, date, datetime
import pytz
import os
from collections import OrderedDict

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

from authentication.models import Account
from authentication.serializers import AccountSerializer

from celery import task
from pickle import NONE
from mongoengine.django.shortcuts import get_document_or_404

from leads.models import Lead
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from analytics.serializers import SnapshotSerializer
from activities.models import Activity
from company.models import CompanyIntegration
from analytics.models import Snapshot

from superadmin.models import SuperIntegration, SuperAnalytics
from superadmin.serializers import SuperAnalyticsSerializer

from analytics.tasks import calculateHsptAnalytics, calculateMktoAnalytics, calculateSfdcAnalytics
# get leads 


@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def calculateAnalytics(request, id): #currently unused
    chart_name = request.GET.get('chart_name')
    chart_title = request.GET.get('chart_title')
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
        elif code == 'mkto':
            result = calculateMktoAnalytics.delay(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title)
        elif code == 'sfdc': 
            result = calculateSfdcAnalytics.delay(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title)
        elif code == 'hspt': 
            result = calculateHsptAnalytics.delay(user_id=user_id, company_id=company_id, chart_name=chart_name, chart_title=chart_title)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveAnalytics(request, id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    chart_name = request.GET.get('chart_name')
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
        elif code == 'mkto':
            result = retrieveMktoAnalytics(user_id=user_id, company_id=company_id)
        elif code == 'sfdc': 
            result = retrieveSfdcAnalytics(user_id=user_id, company_id=company_id)
        elif code == 'hspt': 
            result = retrieveHsptAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getCharts(request, id):
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        charts_temp = []
        charts = []
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system = SuperIntegration.objects(code = source).first()
                #print 'ssys tupe ' + str(defined_system)
                if defined_system is not None:
                    charts_temp = SuperAnalytics.objects(system_type = defined_system.system_type).all()
                    if charts_temp is not None:
                        serializer = SuperAnalyticsSerializer(charts_temp, many=True) 
                        charts.append(serializer.data)
        
        return JsonResponse({"results": charts}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
        
@api_view(['POST'])
@renderer_classes((JSONRenderer,))    
def saveSnapshot(request, id):
    
    try:
        post_data = json.loads(request.body)
        snapshot_html = post_data['snapshotHtml']
        chart_name = post_data['chartName']
        #print 'htl is ' + str(snapshotHtml)
        user_id = request.user.id
        company_id = request.user.company_id
        
        snapshot = Snapshot(owner_id=user_id, company_id=company_id, snapshot_html=snapshot_html, chart_name=chart_name)
        snapshot.save()
        serializer = SnapshotSerializer(snapshot, many=False) 
        return JsonResponse({"message": "Snapshot saved", "snapshot": serializer.data},  safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getSnapshots(request, id):
    #print 'in there'
    try:
        user_id = request.user.id
        company_id = request.user.company_id
        
        snapshots = Snapshot.objects(owner_id=user_id).exclude('snapshot_html')
        serializer = SnapshotSerializer(snapshots, many=True) 
        return Response(serializer.data)  
    except Exception as e:
        return JsonResponse({'Error' : str(e)})    
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getSnapshot(request, id):
    print 'in there' + str(id)
    try:
        snapshot = Snapshot.objects(id=id).first()
        serializer = SnapshotSerializer(snapshot, many=False) 
        return Response(serializer.data)  
    except Exception as e:
        return JsonResponse({'Error' : str(e)})    


#@app.task
def retrieveMktoAnalytics(user_id=None, company_id=None):
    pass

#@app.task
def retrieveSfdcAnalytics(user_id=None, company_id=None):
    pass

#@app.task
def retrieveHsptAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None):
    method_map = { "sources_bar" : hspt_sources_bar_chart, "contacts_distr" : hspt_contacts_distr_chart, "pipeline_duration" : hspt_contacts_pipeline_duration, "source_pie" : hspt_contacts_sources_pie, "revenue_source_pie" : hspt_contacts_revenue_sources_pie,}
    result = method_map[chart_name](user_id, company_id, start_date, end_date)
    return result

# first chart - 'Timeline"
def hspt_sources_bar_chart(user_id, company_id, start_date, end_date): 
    #print 'orig start' + str(start_date)
    try:
        #start_date = #'2015-05-11'
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        #naive = datetime.strptime(start_date, '%Y-%m-%d')
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        #print 'start is ' + str(local_start_date)
        #utc_start_date = local_date.astimezone(pytz.utc)
        
        #naive = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #print 'end is ' + str(local_end_date)
        #utc_end_date = local_date.astimezone(pytz.utc)
        
        #print 'utc start is ' + str(utc_start_date)
        #print 'utc end is ' + str(utc_end_date)
        print 'diff is ' + str((local_end_date - local_start_date).days)
        subscriber_dict = {}
        subscriber_values_temp_array = {}
        subscriber_values_array = []
        lead_dict = {}
        lead_values_temp_array = {}
        lead_values_array = []
        mql_dict = {}
        mql_values_temp_array = {}
        mql_values_array = []
        sql_dict = {}
        sql_values_temp_array = {}
        sql_values_array = []
        opp_dict = {}
        opp_values_temp_array = {}
        opp_values_array = []
        customer_dict = {}
        customer_values_temp_array = {}
        customer_values_array = []
        all_dates = []
        
        #existingLeads = Lead.objects(company_id = company_id ).all()
        #end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
        system_field_qry = 'leads__hspt__exists'
        
        querydict = {system_field_qry: True, company_field_qry: company_id} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            
        #querydict = {company_field_qry: company_id} #, end_date_field_qry : local_start_date}
        #print 'qd is ' + str(querydict)
        existingLeads = Lead.objects(**querydict)
        delta = timedelta(days=1)
        e = local_end_date
        date_field_map = { "subscriber" : 'hs_lifecyclestage_subscriber_date', "lead" : 'hs_lifecyclestage_lead_date', "marketingqualifiedlead" : 'hs_lifecyclestage_marketingqualifiedlead_date', "salesqualifiedlead" : 'hs_lifecyclestage_salesqualifiedlead_date', "opportunity" : 'hs_lifecyclestage_opportunity_date', "customer" : 'hs_lifecyclestage_customer_date' } 
        this_lead_done_for_day = False
        
        for lead in existingLeads:
            s = local_start_date - timedelta(days=1)
            properties = lead.leads['hspt']['properties']
            
            
            while s < (e - delta):
                s += delta #increment the day counter
                this_lead_done_for_day = False
                current_stage = properties['lifecyclestage']
                #print 'enter date loop with start ' + str(s) + ' and end ' + str(e)
                current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                current_stage_date = current_stage_date.astimezone(get_current_timezone())
                array_key = s.strftime('%m-%d-%Y')
                if array_key not in all_dates:
                    all_dates.append(array_key)
                            
                if current_stage == 'customer':
                    if current_stage_date <= s: #and current_stage_date <= local_end_date:
                        if array_key in customer_values_temp_array:
                            customer_values_temp_array[array_key] += 1
                        else:
                            customer_values_temp_array[array_key] = 1
                        this_lead_done_for_day = True
                        continue  
                    if this_lead_done_for_day == False:
                        current_stage = 'opportunity'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in opp_values_temp_array:
                                    opp_values_temp_array[array_key] += 1
                                else:
                                    opp_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'opportunity':
                    #current_stage = 'opportunity'
                    if date_field_map[current_stage] in properties:
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in opp_values_temp_array:
                                opp_values_temp_array[array_key] += 1
                            else:
                                opp_values_temp_array[array_key] = 1
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'salesqualifiedlead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in sql_values_temp_array:
                                    sql_values_temp_array[array_key] += 1
                                else:
                                    sql_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True  
                                continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'salesqualifiedlead':
                    #current_stage = 'salesqualifiedlead'
                    if date_field_map[current_stage] in properties:
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in sql_values_temp_array:
                                sql_values_temp_array[array_key] += 1
                            else:
                                sql_values_temp_array[array_key] = 1
                            this_lead_done_for_day = True  
                            continue
                    if this_lead_done_for_day == False:   
                        current_stage = 'marketingqualifiedlead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in mql_values_temp_array:
                                    mql_values_temp_array[array_key] += 1
                                else:
                                    mql_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                 
                elif current_stage == 'marketingqualifiedlead':
                    if date_field_map[current_stage] in properties:
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in mql_values_temp_array:
                                mql_values_temp_array[array_key] += 1
                            else:
                                mql_values_temp_array[array_key] = 1
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False: 
                        current_stage = 'lead'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in lead_values_temp_array:
                                    lead_values_temp_array[array_key] += 1
                                else:
                                    lead_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                
                elif current_stage == 'lead':
                    if date_field_map[current_stage] in properties:
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in lead_values_temp_array:
                                lead_values_temp_array[array_key] += 1
                            else:
                                lead_values_temp_array[array_key] = 1
                            this_lead_done_for_day = True 
                            continue
                    if this_lead_done_for_day == False:                 
                        current_stage = 'subscriber'
                        if date_field_map[current_stage] in properties:
                            current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                            current_stage_date = current_stage_date.astimezone(get_current_timezone())
                            if current_stage_date <= s:
                                if array_key in subscriber_values_temp_array:
                                    subscriber_values_temp_array[array_key] += 1
                                else:
                                    subscriber_values_temp_array[array_key] = 1
                                this_lead_done_for_day = True 
                                continue
                                    
                elif current_stage == 'subscriber':
                    if date_field_map[current_stage] in properties:
                        current_stage_date = pytz.utc.localize(properties[date_field_map[current_stage]], is_dst=None)
                        current_stage_date = current_stage_date.astimezone(get_current_timezone())
                        if current_stage_date <= s:
                            if array_key in subscriber_values_temp_array:
                                subscriber_values_temp_array[array_key] += 1
                            else:
                                subscriber_values_temp_array[array_key] = 1
                            this_lead_done_for_day = True 
                            continue
            
               
  
        for key in subscriber_values_temp_array.keys():
            if subscriber_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': subscriber_values_temp_array[key]}
                subscriber_values_array.append(obj)
        for date in all_dates:
            if date not in subscriber_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                subscriber_values_array.append(obj)
                
        for key in lead_values_temp_array.keys():
            if lead_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': lead_values_temp_array[key]}
                lead_values_array.append(obj)
        for date in all_dates:
            if date not in lead_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                lead_values_array.append(obj)
            
        for key in mql_values_temp_array.keys():
            if mql_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': mql_values_temp_array[key]}
                mql_values_array.append(obj)
        for date in all_dates:
            if date not in mql_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                mql_values_array.append(obj)
            
        for key in sql_values_temp_array.keys():
            if sql_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': sql_values_temp_array[key]}
                sql_values_array.append(obj)
        for date in all_dates:
            if date not in sql_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                sql_values_array.append(obj)
            
        for key in opp_values_temp_array.keys():
            if opp_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': opp_values_temp_array[key]}
                opp_values_array.append(obj)
        for date in all_dates:
            if date not in opp_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                opp_values_array.append(obj)
                   
        for key in customer_values_temp_array.keys():
            if customer_values_temp_array[key] > 0:
                obj = {'x' : key, 'y': customer_values_temp_array[key]}
                customer_values_array.append(obj)
        for date in all_dates:
            if date not in customer_values_temp_array.keys():
                obj = {'x' : date, 'y': 0}
                customer_values_array.append(obj)

        result = []
        subscriber_object = {'key' : 'Subscribers', 'values': subscriber_values_array}
        lead_object = {'key' : 'Leads', 'values': lead_values_array}
        mql_object = {'key' : 'MQLs', 'values': mql_values_array}
        sql_object = {'key' : 'SQLs', 'values': sql_values_array}
        opp_object = {'key' : 'Opportunities', 'values': opp_values_array}
        customer_object = {'key' : 'Customers', 'values': customer_values_array}
        
        result.append(subscriber_object)
        result.append(lead_object)
        result.append(mql_object)
        result.append(sql_object)
        result.append(opp_object)
        result.append(customer_object)
        
        #print str(result)
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})        

#second chart - "Contacts  Distribution"   
def hspt_contacts_distr_chart(user_id, company_id, start_date, end_date): 
    #print 'orig start' + str(start_date)
    try:
        #start_date = #'2015-05-11'
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        #naive = datetime.strptime(start_date, '%Y-%m-%d')
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        #print 'start is ' + str(local_start_date)
        #utc_start_date = local_date.astimezone(pytz.utc)
        
        #naive = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        #print 'end is ' + str(local_end_date)
        #utc_end_date = local_date.astimezone(pytz.utc)
        
        #print 'utc start is ' + str(utc_start_date)
        #print 'utc end is ' + str(utc_end_date)
        
       
        subscriber_values_array = []
        subscriber_values_array.append(0)
        lead_values_array = []
        lead_values_array.append(0)
        mql_values_array = []
        mql_values_array.append(0)
        sql_values_array = []
        sql_values_array.append(0)
        opp_values_array = []
        opp_values_array.append(0)
        customer_values_array = []
        customer_values_array.append(0)
        all_dates = []
        
        start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__hspt__exists'
            
        querydict = {company_field_qry: company_id, system_field_qry: True} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            
        
        existingLeads = Lead.objects(**querydict)
        for lead in existingLeads:
            properties = lead.leads['hspt']['properties']
            if 'hs_lifecyclestage_customer_date' in properties:
                local_customer_date = pytz.utc.localize(properties['hs_lifecyclestage_customer_date'], is_dst=None)
                local_customer_date = local_customer_date.astimezone(get_current_timezone())
                if local_customer_date >= local_start_date and local_customer_date <= local_end_date:
                    customer_values_array[0] += 1
                    
            elif 'hs_lifecyclestage_opportunity_date' in properties:
                local_opp_date = pytz.utc.localize(properties['hs_lifecyclestage_opportunity_date'], is_dst=None)
                local_opp_date = local_opp_date.astimezone(get_current_timezone())
                if local_opp_date >= local_start_date and local_opp_date <= local_end_date:
                    opp_values_array[0] += 1
                    
            elif 'hs_lifecyclestage_salesqualifiedlead_date' in properties:
                local_sql_date = pytz.utc.localize(properties['hs_lifecyclestage_salesqualifiedlead_date'], is_dst=None)
                local_sql_date = local_sql_date.astimezone(get_current_timezone())
                if local_sql_date >= local_start_date and local_sql_date <= local_end_date:
                    sql_values_array[0] += 1

            elif 'hs_lifecyclestage_marketingqualifiedlead_date' in properties:
                local_mql_date = pytz.utc.localize(properties['hs_lifecyclestage_marketingqualifiedlead_date'], is_dst=None)
                local_mql_date = local_mql_date.astimezone(get_current_timezone())
                if local_mql_date >= local_start_date and local_mql_date <= local_end_date:
                    mql_values_array[0] += 1
                    
            elif 'hs_lifecyclestage_lead_date' in properties:
                local_lead_date = pytz.utc.localize(properties['hs_lifecyclestage_lead_date'], is_dst=None)
                local_lead_date = local_lead_date.astimezone(get_current_timezone())
                if local_lead_date >= local_start_date and local_lead_date <= local_end_date:
                    lead_values_array[0] += 1
             
            elif 'hs_lifecyclestage_subscriber_date' in properties:
                local_subscriber_date = pytz.utc.localize(properties['hs_lifecyclestage_subscriber_date'], is_dst=None)
                local_subscriber_date = local_subscriber_date.astimezone(get_current_timezone())
                if local_subscriber_date >= local_start_date and local_subscriber_date <= local_end_date:
                    subscriber_values_array[0] += 1
                    

        result = []
        subscriber_object = {'label' : 'Subscribers', 'value': subscriber_values_array[0]}
        lead_object = {'label' : 'Leads', 'value': lead_values_array[0]}
        mql_object = {'label' : 'MQLs', 'value': mql_values_array[0]}
        sql_object = {'label' : 'SQLs', 'value': sql_values_array[0]}
        opp_object = {'label' : 'Opportunities', 'value': opp_values_array[0]}
        customer_object = {'label' : 'Customers', 'value': customer_values_array[0]}
        
        result.append(subscriber_object)
        result.append(lead_object)
        result.append(mql_object)
        result.append(sql_object)
        result.append(opp_object)
        result.append(customer_object)
        
        result_final = {}
        result_final["key"] = "Contacts Distribution"
        result_final["values"] = result
        
        result_final_array = []
        result_final_array.append(result_final)
        #print str(result)
        return result_final_array
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})       
  
  
def hspt_contacts_pipeline_duration(user_id, company_id, start_date, end_date):
    
    try:
        #start_date = #'2015-05-11'
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        #naive = datetime.strptime(start_date, '%Y-%m-%d')
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        #print 'start is ' + str(local_start_date)
        #utc_start_date = local_date.astimezone(pytz.utc)
        
        #naive = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        utc_current_date = datetime.utcnow()
        #print 'local time is ' + str(utc_current_date)
        #local_current_date =  get_current_timezone().localize(utc_current_date, is_dst=None)
        
        date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' } 
        #stage_field_map = ) #
        stage_field_map = OrderedDict() #{"Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer'})
        stage_field_map["Subscribers"] = 'subscriber'
        stage_field_map["Leads"] = 'lead'
        stage_field_map["MQLs"] = 'marketingqualifiedlead'
        stage_field_map["SQLs"] = 'salesqualifiedlead'
        stage_field_map["Opportunities"] = 'opportunity'
        stage_field_map["Customers"] = 'customer' 
        #average_days_in_this_stage_list = OrderedDict()
        average_days_in_this_stage_list = OrderedDict() #{ "Subscribers" : 0, "Leads" : 0, "MQLs" : 0, "SQLs" : 0, "Opportunities" : 0, "Customers" : 0}
        average_days_in_this_stage_list["Subscribers"] = 0
        average_days_in_this_stage_list["Leads"] = 0
        average_days_in_this_stage_list["MQLs"] = 0
        average_days_in_this_stage_list["SQLs"] = 0
        average_days_in_this_stage_list["Opportunities"] = 0
        average_days_in_this_stage_list["Customers"] = 0
        
        transition_field_map = {"S->L":0, "L->M":0, "M->S":0, "S->O":0, "O->C":0 }
        transitions_days = OrderedDict() #{ "Subscribers" : 0, "Leads" : 0, "MQLs" : 0, "SQLs" : 0, "Opportunities" : 0, "Customers" : 0}
        for stage in stage_field_map:
            transitions_days[stage] = OrderedDict()
            transitions_days["all"] = OrderedDict()
            if stage != "Subscribers":
                transitions_days[stage]["S->L"] = 0 #, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
                transitions_days["all"]["S->L"] = 0 
                if stage != "Leads":
                    transitions_days[stage]["L->M"] = 0
                    transitions_days["all"]["L->M"] = 0
                    if stage != "MQLs":
                        transitions_days[stage]["M->S"] = 0
                        transitions_days["all"]["M->S"] = 0
                        if stage != "SQLs":
                            transitions_days[stage]["S->O"] = 0
                            transitions_days["all"]["S->O"] = 0
                            if stage != "Opportunities":
                                transitions_days[stage]["O->C"] = 0  
                                transitions_days["all"]["O->C"] = 0 
            #transitions_days[stage] = {"S->L":0, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
        #print 'tran is ' + str(transitions_days["Customers"]["S->L"])
#         transitions_days["Customers"]["S->L"] = 0
#         transitions_days["Customers"]["L->M"] = 0
#         transitions_days["Customers"]["M->S"] = 0
#         transitions_days["Customers"]["S->O"] = 0
#         transitions_days["Customers"]["O->C"] = 0
#         transitions_days["Opportunities"]["S->L"] = 0
#         transitions_days["Opportunities"]["L->M"] = 0
#         transitions_days["Opportunities"]["M->S"] = 0
#         transitions_days["Opportunities"]["S->O"] = 0
#         transitions_days["SQLs"]["S->L"] = 0
#         transitions_days["SQLs"]["L->M"] = 0
#         transitions_days["SQLs"]["M->S"] = 0
#         transitions_days["MQLs"]["S->L"] = 0
#         transitions_days["MQLs"]["L->M"] = 0
#         transitions_days["Leads"]["S->L"] = 0
        transitions_leads = OrderedDict() #{ "Subscribers" : 0, "Leads" : 0, "MQLs" : 0, "SQLs" : 0, "Opportunities" : 0, "Customers" : 0}
        for stage in stage_field_map:
            transitions_leads[stage] = OrderedDict()
            transitions_leads["all"] = OrderedDict()
            if stage != "Subscribers":
                transitions_leads[stage]["S->L"] = 0 #, "L->M":0, "M->S":0, "S->O":0, "O->C":0 } 
                transitions_leads["all"]["S->L"] = 0
                if stage != "Leads":
                    transitions_leads[stage]["L->M"] = 0
                    transitions_leads["all"]["L->M"] = 0
                    if stage != "MQLs":
                        transitions_leads[stage]["M->S"] = 0
                        transitions_leads["all"]["M->S"] = 0
                        if stage != "SQLs":
                            transitions_leads[stage]["S->O"] = 0
                            transitions_leads["all"]["S->O"] = 0
                            if stage != "Opportunities":
                                transitions_leads[stage]["O->C"] = 0  
                                transitions_leads["all"]["O->C"] = 0   

#        for stage in stage_field_map:
#             transitions_leads.update(stage)
#         transitions_leads["Customers"]["S->L"] = 0
#         transitions_leads["Customers"]["L->M"] = 0
#         transitions_leads["Customers"]["M->S"] = 0
#         transitions_leads["Customers"]["S->O"] = 0
#         transitions_leads["Customers"]["O->C"] = 0
#         transitions_leads["Opportunities"]["S->L"] = 0
#         transitions_leads["Opportunities"]["L->M"] = 0
#         transitions_leads["Opportunities"]["M->S"] = 0
#         transitions_leads["Opportunities"]["S->O"] = 0
#         transitions_leads["SQLs"]["S->L"] = 0
#         transitions_leads["SQLs"]["L->M"] = 0
#         transitions_leads["SQLs"]["M->S"] = 0
#         transitions_leads["MQLs"]["S->L"] = 0
#         transitions_leads["MQLs"]["L->M"] = 0
#         transitions_leads["Leads"]["S->L"] = 0
    
        for stage in stage_field_map:
            #print 'stage is ' + str(stage)
            start_date_field_qry = 'leads__hspt__properties__' + date_field_map[stage] + '__gte'
            #start_date_field_qry = 'leads__hspt__properties__createdate__gte'
            end_date_field_qry = 'leads__hspt__properties__' + date_field_map[stage] + '__lte'
            #end_date_field_qry = 'leads__hspt__properties__createdate__lte'
            start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
            end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
            stage_field_qry = 'leads__hspt__properties__lifecyclestage'
            company_field_qry = 'company_id'
            system_field_qry = 'leads__hspt__exists'
            
            querydict = {system_field_qry: True, company_field_qry: company_id,start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[stage]} # start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date, 
            #print 'query dict is ' + str(querydict)
            leads = Lead.objects(**querydict) # now we have all leads in the given stage
            #print ' found leads: ' + str(len(leads))
            for lead in leads: # iterate over each lead
                #print ' lead id is ' + lead['hspt_id']
                lead_props = lead['leads']['hspt']['properties']
                #handle average days in current stage 
                if date_field_map[stage] not in lead['leads']['hspt']['properties']:
                    raise ValueError("This is not possible")
                started_this_stage_date = lead_props[date_field_map[stage]]
                days_in_this_stage = (utc_current_date - started_this_stage_date).total_seconds() #remove conversion to seconds if you want dates; use .days then - no ()
                average_days_in_this_stage_list[stage] += days_in_this_stage
                
                #handle transition days
                if stage == "Customers":
                    stage_date1 = lead_props.get('hs_lifecyclestage_opportunity_date')
                    if stage_date1 is not None and started_this_stage_date is not None:
                        transitions_days["Customers"]["O->C"] += (started_this_stage_date - stage_date1).total_seconds() # change for number of days
                        transitions_days["all"]["O->C"] += (started_this_stage_date - stage_date1).total_seconds()
                    transitions_leads["Customers"]["O->C"] += 1
                    transitions_leads["all"]["O->C"] += 1
                    stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                    if stage_date2 is not None and stage_date1 is not None:
                        transitions_days["Customers"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                        transitions_days["all"]["S->O"] += (stage_date1 - stage_date2).total_seconds()
                    transitions_leads["Customers"]["S->O"] +=1
                    transitions_leads["all"]["S->O"] +=1
                    stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                    if stage_date3 is not None and stage_date2 is not None:
                        transitions_days["Customers"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                        transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                    transitions_leads["Customers"]["M->S"] +=1
                    transitions_leads["all"]["M->S"] +=1
                    stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                    if stage_date4 is not None and stage_date3 is not None: 
                        transitions_days["Customers"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                        transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                    transitions_leads["Customers"]["L->M"] +=1
                    transitions_leads["all"]["L->M"] +=1
                    stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                    if stage_date5 is not None and stage_date4 is not None: 
                        transitions_days["Customers"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                        transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                    transitions_leads["Customers"]["S->L"] +=1
                    transitions_leads["all"]["S->L"] +=1
                
                elif stage == "Opportunities":
                    stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                    if stage_date2 is not None  and started_this_stage_date is not None:
                        transitions_days["Opportunities"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                        transitions_days["all"]["S->O"] += (started_this_stage_date - stage_date2).total_seconds()
                    transitions_leads["Opportunities"]["S->O"] +=1
                    transitions_leads["all"]["S->O"] +=1
                    stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                    if stage_date3 is not None and stage_date2 is not None:
                        transitions_days["Opportunities"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                        transitions_days["all"]["M->S"] += (stage_date2 - stage_date3).total_seconds()
                    transitions_leads["Opportunities"]["M->S"] +=1
                    transitions_leads["all"]["M->S"] +=1
                    stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                    if stage_date4 is not None and stage_date3 is not None: 
                        transitions_days["Opportunities"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                        transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                    transitions_leads["Opportunities"]["L->M"] +=1
                    transitions_leads["all"]["L->M"] +=1
                    stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                    if stage_date5 is not None and stage_date4 is not None: 
                        transitions_days["Opportunities"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                        transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                    transitions_leads["Opportunities"]["S->L"] +=1
                    transitions_leads["all"]["S->L"] +=1
                    
                elif stage == "SQLs":
                    stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                    if stage_date3 is not None  and started_this_stage_date is not None:
                        transitions_days["SQLs"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                        transitions_days["all"]["M->S"] += (started_this_stage_date - stage_date3).total_seconds()
                    transitions_leads["SQLs"]["M->S"] +=1
                    transitions_leads["all"]["M->S"] +=1
                    stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                    if stage_date4 is not None and stage_date3 is not None: 
                        transitions_days["SQLs"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                        transitions_days["all"]["L->M"] += (stage_date3 - stage_date4).total_seconds()
                    transitions_leads["SQLs"]["L->M"] +=1
                    transitions_leads["all"]["L->M"] +=1
                    stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                    if stage_date5 is not None and stage_date4 is not None: 
                        transitions_days["SQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                        transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                    transitions_leads["SQLs"]["S->L"] +=1
                    transitions_leads["all"]["S->L"] +=1
                    
                elif stage == "MQLs":
                    stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                    if stage_date4 is not None  and started_this_stage_date is not None:
                        transitions_days["MQLs"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                        transitions_days["all"]["L->M"] += (started_this_stage_date - stage_date4).total_seconds()
                    transitions_leads["MQLs"]["L->M"] +=1
                    transitions_leads["all"]["L->M"] +=1
                    stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                    if stage_date5 is not None and stage_date4 is not None: 
                        transitions_days["MQLs"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                        transitions_days["all"]["S->L"] += (stage_date4 - stage_date5).total_seconds()
                    transitions_leads["MQLs"]["S->L"] +=1
                    transitions_leads["all"]["S->L"] +=1
                    
                elif stage == "Leads":
                    stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                    if stage_date5 is not None and started_this_stage_date is not None: 
                        transitions_days["Leads"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                        transitions_days["all"]["S->L"] += (started_this_stage_date - stage_date5).total_seconds()
                    transitions_leads["Leads"]["S->L"] +=1
                    transitions_leads["all"]["S->L"] +=1
                    
            
            #now that we have gone through all leads in this stage, calculate the average days in the current stage
            if len(leads) > 0:
                average_days_in_this_stage_list[stage] = average_days_in_this_stage_list[stage] / len(leads)
         
                #if transitions_leads[stage] > 0:
                    #transitions_days[stage] = transitions_days[stage] / transitions_leads[stage]
        #print 'days avg is ' + str(average_days_in_this_stage_list)   
    
        #all stages are done so return data
        average_days = []
        result_set = {}
        result_set2 = {}
        result = []
        transition_label_map = {"S->L":1, "L->M":2, "M->S":3, "S->O":4, "O->C":5 } #{"S->L":"Leads", "L->M":"MQLs", "M->S":"SQLs", "S->O":"Opportunities", "O->C":"Customers" }
        stage_label_map = {"Subscribers":0, "Leads":1, "MQLs":2, "SQLs":3, "Opportunities":4, "Customers":5 }
        #now calculate the average number of days for each transition
        
        for stage in stage_field_map:
            #result_set['key'] = stage
            #print 'kead array is ' + stage + ' :' + str(transitions_leads[stage]) + ' mmm ' + str(transitions_days[stage])
            if stage == "Subscribers":
                total_days = [{'x': 0, 'y': 0}] #
            else:
                total_days = []
            for entry in  transitions_leads[stage]:
                #print 'emtru os ' + str(entry)
                if transitions_leads[stage][entry] > 0:
                    transitions_days[stage][entry] = transitions_days[stage][entry] / transitions_leads[stage][entry]
                total_days.append({'x' : transition_label_map[entry], 'y' : transitions_days[stage][entry]})
            result.append({'key' : stage, 'values': total_days}) #'type': 'line', 'yAxis': 1
            #print 'kead array 3 is ' + stage + ' :' + str(transitions_leads[stage]) + ' mmm ' + str(transitions_days[stage])
        
        total_days = []
        for entry in transitions_leads["all"]:
                #print 'emtru os ' + str(entry)
                if transitions_leads["all"][entry] > 0:
                    transitions_days["all"][entry] = transitions_days["all"][entry] / transitions_leads["all"][entry]
                total_days.append({'x' : transition_label_map[entry], 'y' : transitions_days["all"][entry]})
        result.append({'key' : "All", 'values': total_days, 'color' : '#004358'})
        
        for stage in stage_field_map:
            #print 'sat gis ' + stage
            #average_days_in_this_stage_list_final["x"] = stage
            #average_days_in_this_stage_list_final["y"]= average_days_in_this_stage_list[stage]
            average_days.append({'x' : stage_label_map[stage], 'y' : average_days_in_this_stage_list[stage]}) #, 'shape': 'square'
            #print 'appeneded ' + str(average_days_in_this_stage_list_final)
        #print 'final array is ' + str(average_days)
        
        result_set2['key'] = 'Days in current status'
        result_set2['values'] = average_days
        result_set2['area'] = True
        result_set2['color'] = '#bedb39'
        #result_set2['type'] = 'area'
        #result_set2['yAxis'] = 2
        
        result.append(result_set2)
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
       

def hspt_contacts_sources_pie(user_id, company_id, start_date, end_date):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        utc_current_date = datetime.utcnow()   
        
        source_distr = {}
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        analytics_field_qry = 'leads__hspt__properties__hs_analytics_source__exists'
        
        querydict = {analytics_field_qry: True, company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
        leads = Lead.objects(**querydict)
        
        for lead in leads:
            source = lead['leads']['hspt']['properties']['hs_analytics_source']
            if source in source_distr:
                source_distr[source] += 1
            else:
                source_distr[source] = 1
                
        result = []
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})
    
    

#get revenue (from HSPT) by source (from HSPT); needs the HSPT lead record to exist
def hspt_contacts_revenue_sources_pie(user_id, company_id, start_date, end_date):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
        utc_current_date = datetime.utcnow()   
        
        source_distr = {}
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        company_field_qry = 'company_id'
        revenue_field_qry = 'leads__hspt__properties__total_revenue__exists'
        
        querydict = {revenue_field_qry: True, company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
        leads = Lead.objects(**querydict)
        
        for lead in leads:
            source = lead['leads']['hspt']['properties']['hs_analytics_source']
            revenue = lead['leads']['hspt']['properties']['total_revenue']
            if source in source_distr:
                source_distr[source] += revenue
            else:
                source_distr[source] = revenue
                
        result = []
        for key in source_distr.keys():
            result.append({'x': key, 'y':source_distr[key]})
            
        return result
    
    except Exception as e:
        print 'exception is ' + str(e) + ' and type is ' + str(type(e))
        return JsonResponse({'Error' : str(e)})