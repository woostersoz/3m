import datetime, json


from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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

from integrations.views import Marketo, Salesforce #, get_sfdc_test

from opportunities.tasks import retrieveSfdcOpportunities
# get leads 

#@api_view(['GET'])
class OpportunitiesViewSet(drfme_generics.ListCreateAPIView):
    
    #serializer_class = ActivitySerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            #print 'no code'
            #queryset = Activity.objects.all()
            pass
            
        return queryset

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveOpportunities(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        company_id = request.user.company_id
        try:
            if code == 'mkto':
                #result = retrieveMktoActivities.delay(user_id=user_id, company_id=company_id)
                pass
            elif code == 'sfdc': 
                result = retrieveSfdcOpportunities.delay(user_id=user_id, company_id=company_id)
            else:
                result =  'Nothing to report'
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveOpportunitiesDaily(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        #company_id = request.user.company_id
        company_id = id
        try:
#             if code == 'mkto':
#                 #result = retrieveMktoActivities.delay(user_id=user_id, company_id=company_id)
#                 pass
#             elif code == 'sfdc': 
#                 result = retrieveSfdcOpportunitiesDaily.delay(user_id=user_id, company_id=company_id)
#             else:
#                 result =  'Nothing to report'
            result = None
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    
