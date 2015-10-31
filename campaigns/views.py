import datetime, json

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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

from integrations.views import Marketo, Salesforce
from campaigns.serializers import CampaignSerializer
from campaigns.models import Campaign
from campaigns.tasks import retrieveMktoCampaigns, retrieveSfdcCampaigns, retrieveHsptCampaigns

# get leads 

#@api_view(['GET'])
class CampaignsViewSet(drfme_generics.ListCreateAPIView): #deprecated
    
    serializer_class = CampaignSerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            #print 'no code'
            queryset = Campaign.objects.all()
            
        return queryset
    
#     def list(self, request, account_username=None):
#         account = Account.objects.filter(username=account_username)
#         try:
#             if 0 < len(account):
#                 #serializedList = LeadSerializer(Lead.objects(), many=True)
#                 #return Response(serializedList.data)
#                 
#                 result = saveMktoCampaigns(request)
#                 return Response(result)
#             else:
#                 return Response("User " + account_username + " does not exist")
#         except Exception as e:
#             return Response(str(e))

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAllCampaigns(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        total = Campaign.objects.filter(company_id=company_id).count()
        
        queryset = Campaign.objects.filter(company_id=company_id).skip(offset).limit(items_per_page)
        
        serializer = CampaignSerializer(queryset, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveCampaigns(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        company_id = request.user.company_id
        try:
            if code == 'mkto':
                result = retrieveMktoCampaigns.delay(user_id=user_id, company_id=company_id)
            elif code == 'sfdc': 
                result = retrieveSfdcCampaigns.delay(user_id=user_id, company_id=company_id)
            elif code == 'hspt': 
                result = retrieveHsptCampaigns.delay(user_id=user_id, company_id=company_id)
            else: 
                result =  'Nothing to report'
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveCampaignsDaily(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    #company_id = request.user.company_id
    company_id = id
    try:
#         if code == 'mkto':
#             #result = retrieveMktoContacts.delay(user_id=user_id, company_id=company_id)
#             pass
#         elif code == 'sfdc': 
#             result = retrieveSfdcCampaignsDaily.delay(user_id=user_id, company_id=company_id)
#         elif code == 'hspt': 
#             pass
#             #result = retrieveHsptContacts.delay(user_id=user_id, company_id=company_id)
#         else:
#             result =  'Nothing to report'
        result = None
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
