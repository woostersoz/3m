import datetime, json, time
from datetime import timedelta, date, datetime
import pytz
import os
from collections import OrderedDict
from operator import itemgetter
from bson.code import Code

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

from leads.models import Lead, LeadWithForm
from leads.serializers import LeadSerializer, LeadWithFormSerializer
from leads.views import getLeads
from campaigns.views import getCampaigns
from opportunities.views import getOpportunities
from integrations.views import Marketo, Salesforce #, get_sfdc_test
from analytics.serializers import SnapshotSerializer, BinderTemplateSerializer, BinderSerializer
from company.models import CompanyIntegration
from analytics.models import Snapshot, AnalyticsData, AnalyticsIds, BinderTemplate, Binder
from accounts.views import getAccounts, getAccountsAndCounts
from accounts.models import Account

from superadmin.models import SuperIntegration, SuperAnalytics, SuperDashboards, SuperCountry, SuperViews, SuperFilters
from superadmin.serializers import SuperAnalyticsSerializer, SuperDashboardsSerializer, SuperViewsSerializer, SuperFiltersSerializer

from authentication.models import Company, CustomUser

from analytics.tasks import calculateHsptAnalytics, calculateMktoAnalytics, calculateSfdcAnalytics, calculateBufrAnalytics, calculateGoogAnalytics,\
    mkto_waterfall

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveViews(request, company_id):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    view_name = request.GET.get('view_name')
    system_type = request.GET.get('system_type')
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:
        #first see if generic view i.e. not dependent on a specific system
        generic_views = {'contacts': getLeads, 'campaigns': getCampaigns, 'accounts': getAccounts, 'opps': getOpportunities} 
        if view_name in generic_views:
            result = generic_views[view_name](request, company_id)
            return result #assume that the view will convert to JSONResponse
        else: #if view is dependent on type of system
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
                pass
                #result = retrieveHsptDashboards(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, dashboard_name=dashboard_name)
            elif code == 'mkto': 
                pass
                #result = retrieveMktoDashboards(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, dashboard_name=dashboard_name)
            else:
                result =  {'Error': 'No view found'}
            return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getViews(request, company_id):
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        views_temp = []
        views = []
#         if existingIntegration is not None:
#             sources = set()
#             defined_system_types = set()
#             for source in existingIntegration.integrations.keys():
#                 sources.add(source)
#             for source in sources:
#                 #print 'source is ' + str(source)
#                 defined_system = SuperIntegration.objects(code = source).first()
#                 defined_system_types.add(defined_system.system_type)
#             for defined_system_type in defined_system_types:
#                 #print 'def system is ' + str(defined_system.system_type)
#                 if defined_system_type is not None:
#                     dashboards_temp = SuperDashboards.objects(Q(system_type = defined_system_type) & Q(status__ne='Inactive')).all()
#                     for dashboard_temp in list(dashboards_temp):
#                         serializer = SuperDashboardsSerializer(dashboard_temp, many=False) 
#                         dashboards.append(serializer.data)
        views_temp = SuperViews.objects().all()
        for view_temp in list(views_temp):
            serializer = SuperViewsSerializer(view_temp, many=False) 
            views.append(serializer.data)
        return JsonResponse({"results": views}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getSuperFilters(request, company_id):
    
    user_id = request.user.id
    company_id = request.user.company_id
    object_type = request.GET.get('object_type')
    system_type = request.GET.get('system_type')
    #existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    existingIntegration = {}
    existingIntegration['integrations'] = {}
    
    map = Code("function () {"
             "  for (var key in this.integrations) emit(key, this.integrations[key]['filters']); } ")
    
    reduce = Code("function (key, values) { return null; } ")
    
    results = CompanyIntegration.objects(company_id=company_id).map_reduce(map, reduce, "inline")
    results = list(results)
    for result in results:
        existingIntegration['integrations'][result.key] = {'filters': result.value}
    try:
        code = None
        if existingIntegration is not None:
            for source in existingIntegration['integrations'].keys():
                defined_system_type = SuperIntegration.objects(Q(code = source) & Q(system_type = system_type)).first()
                if defined_system_type is not None:
                    code = source
            print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        else:
            super_filters = SuperFilters.objects(source_system = code).first()
            if super_filters is None:
                result = []
            else:
                if object_type not in super_filters['filters']:
                    result = []
                else:                    
                    temp = super_filters['filters'].get(object_type, None)
                    filters = existingIntegration['integrations'][code].get('filters', None)
                    if filters is not None:
                        filter_obj = filters.get(object_type, None)
                        if filter_obj is None:
                            return JsonResponse({'results': temp}, safe=False)
                        for filter, values in filter_obj.items():
                            if filter in temp:
                                if filter == 'OwnerId': #reduce the users list to only those with opportunities
                                    temp_values = {}
                                    opp_field_qry = 'opportunities__sfdc__exists'
                                    company_field_qry = 'company_id'
                                    projection = {'$project': {'owner_id': '$opportunities.sfdc.OwnerId'  } }
                                    querydict = {opp_field_qry: True, company_field_qry: company_id}
                                    opps = Account.objects(**querydict).aggregate({'$unwind': '$opportunities.sfdc'}, projection)
                                    opps = list(opps)
                                    opps_owner_ids = [opp['owner_id'] for opp in opps]
                                    print 'opp owner ids ' + str(opps_owner_ids)
                                    tempValues = [value for value in values['values'] if value['value'] in opps_owner_ids]
                                    print 'temp values2 is ' + str(tempValues)
                                    temp_values['values'] = tempValues
                                    temp_values['label'] = values['label']
                                    values = temp_values
                                values['values'].sort()
                                temp[filter] = values
                    result = {'results': temp}
            #result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
