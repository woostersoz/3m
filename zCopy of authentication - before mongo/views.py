import json

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render

from rest_framework import status, views

from rest_framework import permissions, viewsets
from rest_framework.response import Response

from authentication.models import Account, Company
from authentication.permissions import IsAccountOwner
from authentication.serializers import AccountSerializer, CompanySerializer

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

                serialized = AccountSerializer(account)
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

class AccountViewSet(viewsets.ModelViewSet):
    lookup_field = 'id'
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
        
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)

        if self.request.method == 'POST':
            return (permissions.AllowAny(),)

        return (permissions.IsAuthenticated(), IsAccountOwner(),)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            Account.objects.create_user(**serializer.validated_data)

            return Response(serializer.validated_data, status=status.HTTP_201_CREATED)

        return Response({
            'status': 'Bad request',
            'message': 'Account could not be created with received data.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        #print 'in list'
        company_id = request.user.company_id
        queryset = Account.objects.filter(company_id=company_id)
        serializer = AccountSerializer(queryset, many=True)
        return Response(serializer.data)
        
class CompanyViewSet(viewsets.ModelViewSet):
    lookup_field = 'id'
    queryset = Company.objects.all()
    serializer_class = CompanySerializer      
    
    def list(self, request):
        #print 'in list'
        queryset = Company.objects.filter(id!=0)
        serializer = CompanySerializer(queryset, many=True)
        return Response(serializer.data) 