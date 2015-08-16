import json
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render

from rest_framework import status, views

from rest_framework import permissions, viewsets
from rest_framework.response import Response

from authentication.models import CustomUser, Company
from authentication.permissions import IsAccountOwner
from authentication.serializers import CustomUserSerializer, CompanySerializer

from rest_framework_mongoengine import generics as drfme_generics
from django.http import HttpResponse, JsonResponse

class LoginView(views.APIView):
    
    def get(self, request, format=None):
        if not request.user.is_authenticated():
            return render(request, 'authentication/login.html')
    
    def post(self, request, format=None):
        data = json.loads(request.body)
        email = data.get('email', None)
        password = data.get('password', None)
        account = authenticate(email=email, password=password)
        
        if account is not None:
            if account.is_active:
                login(request, account)
                account.company = account.company.company_id # hack to return only the company ID instead of entire object
                serialized = CustomUserSerializer(account)
                request.session['django_timezone'] = account.timezone
                return Response(serialized.data)
            else:
                return Response({
                    'status': 'Unauthorized',
                    'message': 'This account has been disabled.'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Username/password combination invalid.'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        logout(request)

        return Response({}, status=status.HTTP_204_NO_CONTENT)

class UserViewSet(viewsets.ModelViewSet):
    lookup_field = 'id'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
        
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)

        if self.request.method == 'POST':
            return (permissions.AllowAny(),)

        return (permissions.IsAuthenticated(), IsAccountOwner(),)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            CustomUser.objects.create_user(**serializer.validated_data)

            return Response(serializer.validated_data, status=status.HTTP_201_CREATED)

        return Response({
            'status': 'Bad request',
            'message': 'Account could not be created with received data.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, id):
        #print 'in list'
        company_id = request.user.company_id #TO-DO - check if company ID sent is the same as user's company ID
        company = Company.objects.filter(company_id=company_id).first()
        queryset = CustomUser.objects.filter(company=company.id)
        serializer = CustomUserSerializer(queryset, many=True)
        return Response(serializer.data)
    
# Handle GET and DELETE for a single user profile
class SingleUserViewSet(viewsets.ModelViewSet): #drfme_generics.RetrieveDestroyAPIView
    
    serializer_class = CustomUserSerializer
    
    def get_queryset(self):
        pass
           
                
    def delete(self, request, companyid, id):
        
        queryset = CustomUser.objects(id=id).first()
        if queryset is not None and self.request.method == 'DELETE':
            try: 
                queryset.delete()
            except Exception as e:
                return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST)   
        
        return HttpResponse('User with ID ' +  id + ' deleted', status=status.HTTP_200_OK) 
    
    def list(self, request, companyid, id):
        
        user = CustomUser.objects(id=id).first()
        if user is not None:
            serializedData = CustomUserSerializer(user)
            return Response(serializedData.data)
        return HttpResponse("No editable record for " + id + " found!", status=status.HTTP_400_BAD_REQUEST)
   
    def put(self, request, companyid, id):
        
        user = CustomUser.objects(id=id).first()
        if user is not None:
            try:
                data = json.loads(request.body)
                user.email = data.get('email', None)
                user.username = data.get('username', None)
                user.timezone = data.get('timezone', None)
                user.save()
                password = data.get('password', None)
                confirm_password = data.get('confirm_password', None)
                if password and confirm_password and password == confirm_password:
                    user.set_password(password)
                    user.save()
                update_session_auth_hash(request, user)
                return HttpResponse('User ' +  user.username + ' updated', status=status.HTTP_200_OK) 
            except Exception as e:
                return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST)
        
class CompanyViewSet(viewsets.ModelViewSet):
    lookup_field = 'id'
    queryset = Company.objects.all()
    serializer_class = CompanySerializer      
    
    def list(self, request):
        #print 'in list'
        queryset = Company.objects.filter(id!=0)
        serializer = CompanySerializer(queryset, many=True)
        return Response(serializer.data) 