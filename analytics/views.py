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
from integrations.views import Marketo, Salesforce, FacebookPage #, get_sfdc_test
from analytics.serializers import SnapshotSerializer, BinderTemplateSerializer, BinderSerializer
from company.models import CompanyIntegration
from analytics.models import Snapshot, AnalyticsData, BinderTemplate, Binder

from superadmin.models import SuperIntegration, SuperAnalytics, SuperDashboards
from superadmin.serializers import SuperAnalyticsSerializer, SuperDashboardsSerializer

from authentication.models import Company, CustomUser

from analytics.tasks import calculateHsptAnalytics, calculateMktoAnalytics, calculateSfdcAnalytics, calculateBufrAnalytics, calculateGoogAnalytics

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveFilters(request, company_id): #,  
    filter_name = request.GET.get('filter_name')
    try:
        if filter_name == 'google_profiles':
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            googIntegration = existingIntegration.integrations['goog']
            goog_accounts = googIntegration.get('accounts', None)
            result = {'results': goog_accounts}
            return JsonResponse(result, safe=False)
        
        elif filter_name == 'facebook_pages':
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            fbokIntegration = existingIntegration.integrations['fbok']
            fbok_pages = fbokIntegration.get('pages', None)
            fbok_access_token = fbokIntegration['access_token']
            
            if fbok_access_token is not None:
                fb = FacebookPage(fbok_access_token)
                fb_page_details = fb.get_pages()['data']
                print 'fb details ' + str(fb_page_details)
            
            results = []
            for fbok_page in fbok_pages:
                obj = {'id': fbok_page['id'], 'name' : ''}
                for fb_page_detail in fb_page_details:
                    if fb_page_detail['id'] == fbok_page['id']:
                        obj['name'] = fb_page_detail['name']
                results.append(obj)    
            if len(results) == 1: #if there's only one entry, set that as the default filter value
                default_page_id = results[0]['id']
            else:
                default_page_id = None
            result = {'results': results, 'defaultValue': default_page_id, 'defaultMetric': 'facebook_page'}
            return JsonResponse(result, safe=False)
        
        elif filter_name == 'facebook_accounts':
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            fbokIntegration = existingIntegration.integrations['fbok']
            fbok_acounts = fbokIntegration.get('accounts', None)
            
            if len(fbok_acounts) == 1: #if there's only one entry, set that as the default filter value
                default_account_id = fbok_acounts[0]['id']
            else:
                default_account_id = None
            result = {'results': fbok_acounts, 'defaultValue': default_account_id, 'defaultMetric': 'facebook_account'}
            return JsonResponse(result, safe=False)
        
        elif filter_name == 'comparison_periods':
            results = []
            results.append({'id': 1, 'name': 1})
            results.append({'id': 2, 'name': 2})
            results.append({'id': 3, 'name': 3})
            result = {'results': results, 'defaultValue': 1, 'defaultMetric': 'comparison_period'}
            return JsonResponse(result, safe=False)
        
        return JsonResponse(None, safe=False)
    except Exception as e:
        print 'exception is ' + str(e)
        return JsonResponse({'Error' : str(e)})
        

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
        
        print 'found code' + str(code)
                  
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
def retrieveAnalytics(request, company_id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    chart_name = request.GET.get('chart_name')
    system_type = request.GET.get('system_type')
    filters = request.GET.get('filters')
    
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
            result = retrieveMktoAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        elif code == 'sfdc': 
            result = retrieveSfdcAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        elif code == 'hspt': 
            result = retrieveHsptAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        elif code == 'bufr': 
            result = retrieveBufrAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        elif code == 'goog': 
            result = retrieveGoogAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        elif code == 'fbok': 
            result = retrieveFbokAnalytics(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, chart_name=chart_name, filters=filters)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getCharts(request, company_id):
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        charts_temp = []
        charts = []
        if existingIntegration is not None:
            sources = set()
            defined_system_types = set()
            for source in existingIntegration.integrations.keys():
                sources.add(source)
            for source in sources:
                #print 'source is ' + str(source)
                defined_system = SuperIntegration.objects(code = source).first()
                defined_system_types.add(defined_system.system_type)
            for defined_system_type in defined_system_types:
                #print 'def system is ' + str(defined_system.system_type)
                if defined_system_type is not None:
                    charts_temp = SuperAnalytics.objects(Q(system_type = defined_system_type) & Q(status__ne='Inactive')).all()
                    for chart_temp in list(charts_temp):
                        serializer = SuperAnalyticsSerializer(chart_temp, many=False) 
                        charts.append(serializer.data)
        
        return JsonResponse({"results": charts}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

@api_view(['POST'])
@renderer_classes((JSONRenderer,))    
def saveSnapshot(request, company_id):
    
    try:
        post_data = json.loads(request.body)
        snapshot_html = post_data['snapshotHtml']
        chart_name = post_data['chartName']
        #print 'htl is ' + str(snapshotHtml)
        user_id = request.user.id
        company_id = request.user.company_id
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
        
        snapshot = Snapshot(owner=user_id, company=company_id, snapshot_html=snapshot_html, chart_name=chart_name)
        snapshot.save()
        serializer = SnapshotSerializer(snapshot, many=False) 
        return JsonResponse({"message": "Snapshot saved", "snapshot": serializer.data},  safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getSnapshots(request, company_id):
    #print 'in there'
    try:
        user_id = request.user.id
        company_id = request.user.company_id
        
        snapshots = Snapshot.objects(owner=user_id).exclude('snapshot_html')
        serializer = SnapshotSerializer(snapshots, many=True) 
        return Response(serializer.data)  
    except Exception as e:
        return JsonResponse({'Error' : str(e)})    
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getSnapshot(request, id, company_id):
    print 'in there' + str(id)
    try:
        snapshot = Snapshot.objects(id=id).first()
        serializer = SnapshotSerializer(snapshot, many=False) 
        return Response(serializer.data)  
    except Exception as e:
        return JsonResponse({'Error' : str(e)})    


#@app.task
def retrieveMktoAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    method_map = { "sources_bar" : mkto_sources_bar_chart, "contacts_distr" : mkto_contacts_distr_chart, "source_pie" : mkto_contacts_sources_pie, "pipeline_duration" : mkto_contacts_pipeline_duration, "revenue_source_pie" : mkto_contacts_revenue_sources_pie, "website_traffic": hspt_website_traffic_bar}
    result = method_map[chart_name](user_id, company_id, start_date, end_date, chart_name, filters)
    return result

#@app.task
def retrieveSfdcAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    pass

#@app.task
def retrieveHsptAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    method_map = { "sources_bar" : hspt_sources_bar_chart, "contacts_distr" : hspt_contacts_distr_chart, "pipeline_duration" : hspt_contacts_pipeline_duration, "source_pie" : hspt_contacts_sources_pie, "revenue_source_pie" : hspt_contacts_revenue_sources_pie, "website_traffic": hspt_website_traffic_bar}
    result = method_map[chart_name](user_id, company_id, start_date, end_date, chart_name, filters)
    return result

#@app.task
def retrieveBufrAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    method_map = { "tw_performance" : tw_performance_bar_chart}
    result = method_map[chart_name](user_id, company_id, start_date, end_date, chart_name, filters)
    return result

def retrieveGoogAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    method_map = { "google_analytics" : google_analytics_bar_chart}
    result = method_map[chart_name](user_id, company_id, start_date, end_date, chart_name, filters)
    return result

def retrieveFbokAnalytics(user_id=None, company_id=None, chart_name=None, start_date=None, end_date=None, filters=None):
    method_map = { "facebook_organic_engagement" : facebook_engagement_bar_chart, "facebook_paid_engagement" : facebook_engagement_bar_chart}
    result = method_map[chart_name](user_id, company_id, start_date, end_date, chart_name, filters)
    return result


# start of MKTO
# first chart - 'Timeline"
def mkto_sources_bar_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
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

#  chart - 'Contacts Distribution"
def mkto_contacts_distr_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
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

#  chart - 'Pipeline Duration"
def mkto_contacts_pipeline_duration(user_id, company_id, start_date, end_date, chart_name, filters):
    
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        e = local_end_date
        s = local_start_date - timedelta(days=1)
        end_key = e.strftime('%Y-%m-%d')
         
        all_changes = {}
        all_dates = []
        all_totals = {}
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
            
            all_changes[start_key] = data
        
        # we have all the changes by day -> status change -> number & duration
        # create an array of unique statuses
        all_values = {}
        unique_statuses = []
        for date in all_changes.keys():
            for status_change in all_changes[date].keys():
                statuses = status_change.split('-')
                unique_statuses.extend(statuses)
         #make the statuses array unique
        unique_statuses = list(OrderedDict.fromkeys(unique_statuses))
        
        for date in all_changes.keys():
            for status_change in all_changes[date].keys():
                duration = all_changes[date][status_change]['durations'] if all_changes[date][status_change]['changes'] > 0 else 0.1
                changes = all_changes[date][status_change]['changes']
                if not status_change in all_values:
                    all_values[status_change] = {}
                    all_values[status_change]['size'] = duration
                    all_values[status_change]['changes'] = changes
                else:
                    all_values[status_change]['changes'] += changes
                    all_values[status_change]['size'] = (all_values[status_change]['size'] + duration) / all_values[status_change]['changes']
                    
                statuses = status_change.split('-')
                all_values[status_change]['x'] = unique_statuses.index(statuses[0])
                all_values[status_change]['y'] = unique_statuses.index(statuses[1])
                all_values[status_change]['series'] = 0
                all_values[status_change]['shape'] = 'circle'
       
        #return unique_statuses
        #return all_values
        values = []
        for key, value in all_values.iteritems():
            values.append(value)
        result_obj = {}
        result_obj['key'] = "Status changes"
        result_obj['values'] = values
        result_array = []
        result_array.append(result_obj)
        result = {}
        result['results'] = result_array
        result['statuses'] = unique_statuses
        return result
                
    
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})   

def mkto_contacts_sources_pie(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
    
def mkto_contacts_revenue_sources_pie(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
    

# start of HSPT
# first chart - 'Timeline"
def hspt_sources_bar_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
    #print 'orig start' + str(start_date)
    try:
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
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
     
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_qry = 'date'
        
        s = local_start_date - timedelta(days=1)
           
        while s < (e - delta):
            s += delta #increment the day counter
            array_key = s.strftime('%Y-%m-%d')
            
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_qry: array_key} #, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            if existingData is None:
                continue
            data = existingData['results']
              
            if 'Subscribers' in data:    
                subscriber_values_temp_array[array_key] = data['Subscribers']
            else:
                subscriber_values_temp_array[array_key] = 0
            if 'Leads' in data:    
                lead_values_temp_array[array_key] = data['Leads']
            else:
                lead_values_temp_array[array_key] = 0
            if 'MQLs' in data: 
                mql_values_temp_array[array_key] = data['MQLs']
            else:
                mql_values_temp_array[array_key] = 0
            if 'SQLs' in data: 
                sql_values_temp_array[array_key] = data['SQLs']
            else:
                sql_values_temp_array[array_key] = 0
            if 'Opportunities' in data: 
                opp_values_temp_array[array_key] = data['Opportunities']
            else:
                opp_values_temp_array[array_key] = 0
            if 'Customers' in data: 
                customer_values_temp_array[array_key] = data['Customers']
            else:
                customer_values_temp_array[array_key] = 0
                        
        for key in subscriber_values_temp_array.keys():  
            obj = {'x' : key, 'y': subscriber_values_temp_array[key]}
            subscriber_values_array.append(obj)
            
        for key in lead_values_temp_array.keys():
            obj = {'x' : key, 'y': lead_values_temp_array[key]}
            lead_values_array.append(obj)
            
        for key in mql_values_temp_array.keys():
            obj = {'x' : key, 'y': mql_values_temp_array[key]}
            mql_values_array.append(obj)
            
        for key in sql_values_temp_array.keys():
            obj = {'x' : key, 'y': sql_values_temp_array[key]}
            sql_values_array.append(obj)

        for key in opp_values_temp_array.keys():
            obj = {'x' : key, 'y': opp_values_temp_array[key]}
            opp_values_array.append(obj)

        for key in customer_values_temp_array.keys():
            obj = {'x' : key, 'y': customer_values_temp_array[key]}
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
def hspt_contacts_distr_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
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
  
  
def hspt_contacts_pipeline_duration(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
    
       
def hspt_contacts_sources_pie(user_id, company_id, start_date, end_date, chart_name, filters):
    
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

def hspt_contacts_revenue_sources_pie(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
def hspt_website_traffic_bar(user_id, company_id, start_date, end_date, chart_name, filters): 
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


def hspt_contacts_sources_pie_deprecated(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
def hspt_contacts_revenue_sources_pie_deprecated(user_id, company_id, start_date, end_date, chart_name, filters):
    
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
def tw_performance_bar_chart(user_id, company_id, start_date, end_date, chart_name, filters):
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


#Facebook charts    
# For chart - 'Website Traffic"
def facebook_engagement_bar_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
    #print 'orig start' + str(start_date)
    try:
        filterPage = json.loads(filters).get('facebook_page', None)
        filterAccount = json.loads(filters).get('facebook_account', None)
        comparisonPeriod = json.loads(filters).get('comparison_period', None)
        
        if chart_name == 'facebook_organic_engagement':
            if filterPage is None or comparisonPeriod is None:
                return []
            
        if chart_name == 'facebook_paid_engagement':
            if filterAccount is None or comparisonPeriod is None:
                return []
     
        comparisonPeriod = int(comparisonPeriod)
        
        start_date = datetime.fromtimestamp(float(start_date) / 1000)
        end_date = datetime.fromtimestamp(float(end_date) / 1000)#'2015-05-20' + ' 23:59:59'
        
        local_start_date = get_current_timezone().localize(start_date, is_dst=None)
        local_end_date = get_current_timezone().localize(end_date, is_dst=None)
    
        
        days_list = {}
        days_list['1'] = []
        if comparisonPeriod > 1:
            days_list['2'] = []
        if comparisonPeriod > 2:
            days_list['3'] = []
        
        delta = local_end_date - local_start_date
        
        second_end_date = local_start_date - timedelta(days=1)
        second_start_date = second_end_date - timedelta(days=delta.days)
        third_end_date = second_start_date - timedelta(days=1)
        third_start_date = third_end_date - timedelta(days=delta.days)
         
        for i in range(delta.days + 1):
            days_list['1'].append((local_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
            if comparisonPeriod > 1:
                days_list['2'].append((second_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
            if comparisonPeriod > 2:
                days_list['3'].append((third_start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
         
        
        first_end_date_string = local_end_date.strftime('%Y-%m-%d')
        first_start_date_string = local_start_date.strftime('%Y-%m-%d')
        if comparisonPeriod > 1:
            second_end_date_string = second_end_date.strftime('%Y-%m-%d')
            second_start_date_string = second_start_date.strftime('%Y-%m-%d')
        if comparisonPeriod > 2:
            third_end_date_string = third_end_date.strftime('%Y-%m-%d')
            third_start_date_string = third_start_date.strftime('%Y-%m-%d')
        
        keys = {}
        keys['1'] = first_start_date_string + ' - ' + first_end_date_string
        if comparisonPeriod > 1:
            keys['2'] = second_start_date_string + ' - ' + second_end_date_string
        if comparisonPeriod > 2:
            keys['3'] = third_start_date_string + ' - ' + third_end_date_string
        
        result = []
         
        #query variables
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
        date_query = 'date'
        data = {}
        
        #other variables
        chart_namex = 'social_roi'
        
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
        fbokIntegration = existingIntegration.integrations['fbok']
        
        if chart_name == 'facebook_organic_engagement':
            fbok_pages = fbokIntegration.get('pages', None)
            fbok_page_id = None
            if fbok_pages is None:
                return
            for fbok_page in fbok_pages:
                print 'fp is ' + str(filterPage)
                if filterPage is not None: 
                    if filterPage == fbok_page['id']:
                        fbok_page_id = filterPage
                else:
                    fbok_page_id = fbok_page['id'] #take the first FB Page ID available
                    break
            
            if fbok_page_id is None:
                return
            
        elif chart_name == 'facebook_paid_engagement':
            fbok_accounts = fbokIntegration.get('accounts', None)
            fbok_account_id = None
            if fbok_accounts is None:
                return
            for fbok_account in fbok_accounts:
                print 'fp is ' + str(filterAccount)
                if filterAccount is not None: 
                    if filterAccount == fbok_account['id']:
                        fbok_account_id = filterAccount
                else:
                    fbok_account_id = fbok_account['id'] #take the first FB Page ID available
                    break
            
            if fbok_account_id is None:
                return
            
        for keyx, valuex in days_list.items(): # loop through each of the three date sets
            array_key = keys[keyx] #keyx will be 1 or 2 or 3
            data[array_key] = {'Likes': 0, 'Clicks': 0, 'Comments': 0, 'Shares': 0}
            
            for day in days_list[keyx]:
                querydict = {chart_name_qry: chart_namex, company_field_qry: company_id, date_query: day} 
                existingData = AnalyticsData.objects(**querydict).only('results').first()
                if existingData is None:
                    continue
                try:
                    if chart_name == 'facebook_organic_engagement':
                        dataRecords = existingData['results']['Social']['Facebook']['Organic'] 
                        x = fbok_page_id
                    elif chart_name == 'facebook_paid_engagement':
                        dataRecords = existingData['results']['Social']['Facebook']['Paid'] #should be an array
                        x = fbok_account_id
                    for dataRecord in dataRecords:
                        for idx in dataRecord.keys():
                            if idx != x:
                                continue
                            for key, value in dataRecord.items():
                                if chart_name == 'facebook_organic_engagement':
                                    data[array_key]['Likes'] += value.get('like', 0)
                                    data[array_key]['Clicks'] += value.get('link clicks', 0) + value.get('other clicks', 0)
                                    #data[array_key]['Impressions'] += value.get('page_impressions', 0)
                                    data[array_key]['Comments'] += value.get('comment', 0)
                                    data[array_key]['Shares'] += value.get('link', 0)
                                elif chart_name == 'facebook_paid_engagement':
                                    data[array_key]['Likes'] += value.get('like', 0) + value.get('post_like', 0)
                                    data[array_key]['Clicks'] += value.get('website_clicks', 0) 
                                    #data[array_key]['Impressions'] += int(value.get('impressions', 0))
                                    data[array_key]['Comments'] += value.get('comment', 0)
                                    data[array_key]['Shares'] += value.get('link', 0)
                except Exception as e:
                    continue
                
        #at this point, the data object should have all the values needed
        for data_key, data_value in sorted(data.items()): 
            obj_array = []
            for key in data_value.keys():
                obj = {'x' : key, 'y': data[data_key][key]}
                obj_array.append(obj)  
            result.append({'key' : data_key, 'values': obj_array })                   
        return result
    except Exception as e:
        print 'exception is ' + str(e) 
        return JsonResponse({'Error' : str(e)})   

#Google charts    
# For chart - 'Website Traffic"
def google_analytics_bar_chart(user_id, company_id, start_date, end_date, chart_name, filters): 
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
        data = {}
        userTypes = {'New': 0, 'Returning': 0} #
        profiles = {}
        filterProfile = json.loads(filters).get('google_profile', None)
        
        print 'filters are ' + str()
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
        googIntegration = existingIntegration.integrations['goog']
        goog_accounts = googIntegration['accounts']
        for goog_account in goog_accounts:
            if filterProfile is not None: 
                if filterProfile == goog_account['profile_id']:
                    profiles[goog_account['profile_id']] = goog_account['account_name'] + '-' + goog_account['profile_name']
                    #userTypes[profiles[goog_account['profile_id']] + ': New'] = 0;
                    #userTypes[profiles[goog_account['profile_id']] + ': Returning'] = 0;
            else:
                profiles[goog_account['profile_id']] = goog_account['account_name'] + '-' + goog_account['profile_name']
                #userTypes[profiles[goog_account['profile_id']] + ': New'] = 0;
                #userTypes[profiles[goog_account['profile_id']] + ': Returning'] = 0;
            
    
        while s < (e - delta):
            s += delta #increment the day counter
            data = {}
            array_key = s.strftime('%Y-%m-%d')
            print 'date key is ' + array_key
            querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: array_key} 
            
            existingData = AnalyticsData.objects(**querydict).only('results').first()
            for profile_id in profiles.keys():
                if existingData is None: #  no results found for day so move to next day
                    data[profile_id] = {'New' : 0, 'Returning' : 0}
                else:
                    if profile_id in existingData['results']:
                        data[profile_id] = existingData['results'][profile_id]
                    else:
                        data[profile_id] = {'New' : 0, 'Returning' : 0}
        
                for key in userTypes.keys():
                    newKey = profiles[profile_id] +  ': ' + key
                    if  newKey not in all_values: #and key != 'offline'
                        all_values[newKey]= {} 
                    if profile_id in data:
                        all_values[newKey][array_key] = data[profile_id][key]
                    else:    
                        all_values[newKey][array_key] = 0
                
        #print 'all vals is ' + str(all_values)
        #if data == {}:
        #    return []
        for profile_id in profiles.keys():  
            for key in userTypes.keys():
                newKey = profiles[profile_id] +  ': ' + key
                obj_array = []
                for key in all_values[newKey].keys():
                    obj = {'x' : key, 'y': all_values[newKey][key]}
                    obj_array.append(obj)  
                result.append({'key' : newKey, 'values': obj_array })                   
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
            binderTemplate.orientation = binder.get('orientation', 'Portrait')
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
            templateCount = BinderTemplate.objects(company=company.id).count()
            binderCount = Binder.objects(company=company.id).count()
            templateLastCreated = BinderTemplate.objects(company=company.id).order_by('-updated_date')
            templateLastCreated = list(templateLastCreated)[0].updated_date
            binderLastCreated = Binder.objects(company=company.id).order_by('-updated_date')
            binderLastCreated = list(binderLastCreated)[0].updated_date
            return JsonResponse({'results' : serializedList.data, 'templateCount': templateCount, 'binderCount': binderCount, 'templateLastCreated' : templateLastCreated, 'binderLastCreated' : binderLastCreated})
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
            templateCount = BinderTemplate.objects(company=company.id).count()
            binderCount = Binder.objects(company=company.id).count()
            lastCreated = BinderTemplate.objects(company=company.id).order_by('-updated_date')
            lastCreated = list(lastCreated)[0].updated_date
            return JsonResponse({'results' : serializedList.data, 'templateCount': templateCount, 'binderCount': binderCount, 'lastCreated' : lastCreated})
        except Exception as e:
                return Response(str(e))       