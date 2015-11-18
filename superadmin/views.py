from rest_framework_mongoengine import generics as drfme_generics
from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.views import APIView
from mongoengine.queryset.visitor import Q

from superadmin.models import SuperIntegration, SuperJobMonitor
from superadmin.serializers import SuperIntegrationSerializer, SuperJobMonitorSerializer


# Create your lenses here.

class JobViewSet(viewsets.ModelViewSet):  
    
    serializer_class = SuperJobMonitorSerializer
    
    def list(self, request, company_id=None): #retrieve all data extract jobs across all companies
        if company_id != '0':
            return HttpResponse('Company is incorrect', status=status.HTTP_400_BAD_REQUEST) 
        try:
            page_number = int(request.GET.get('page_number'))
            items_per_page = int(request.GET.get('per_page'))
            offset = (page_number - 1) * items_per_page
            
            jobs = SuperJobMonitor.objects().order_by('-started_date')
            totalCount = SuperJobMonitor.objects().count()
            totalCountSuccess = SuperJobMonitor.objects(status='Completed').count()
            totalCountFailure = SuperJobMonitor.objects(status='Failed').count()
            
            qlist = list(jobs)
            result = qlist[offset:offset+items_per_page]
            serializedList = SuperJobMonitorSerializer(result, many=True)
            
            initialCount = SuperJobMonitor.objects(type='initial').count()
            initialCountSuccess = SuperJobMonitor.objects(Q(type='initial') & Q(status='Completed')).count()
            initialCountFailure = SuperJobMonitor.objects(Q(type='initial') & Q(status='Failed')).count()
            
            deltaCount = SuperJobMonitor.objects(type='delta').count()
            deltaCountSuccess = SuperJobMonitor.objects(Q(type='delta') & Q(status='Completed')).count()
            deltaCountFailure = SuperJobMonitor.objects(Q(type='delta') & Q(status='Failed')).count()
            
            return JsonResponse({'totalCount': totalCount, 'totalCountSuccess': totalCountSuccess, \
                                 'totalCountFailure': totalCountFailure, 'initialCount': initialCount, \
                                 'initialCountSuccess': initialCountSuccess, 'initialCountFailure': initialCountFailure, \
                                 'deltaCount': deltaCount, 'deltaCountSuccess': deltaCountSuccess, \
                                 'deltaCountFailure': deltaCountFailure, 'results': serializedList.data})
        except Exception as e:
            return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST) 
