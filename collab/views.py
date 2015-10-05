import datetime, json

from django.shortcuts import get_object_or_404, render, redirect
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

from mongoengine.queryset.visitor import Q

from rest_framework_mongoengine import generics as drfme_generics

from authentication.models import Company

from celery import task
from pickle import NONE
from mongoengine.django.shortcuts import get_document_or_404
from bson.json_util import dumps
from bson import json_util, ObjectId
from time import strftime

from collab.serializers import NotificationSerializer, ChatroomSerializer, ChatuserSerializer, ChatusermessageSerializer
from collab.models import Notification, ChatRoom, ChatUser, ChatUserMessage
from company.models import CompanyIntegration, UserOauth
from integrations.views import Slack
from analytics.models import Snapshot

# get leads 

#@api_view(['GET'])
class MessagesViewSet(drfme_generics.ListCreateAPIView):
    
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        #print 'in query'
        user_id = self.request.user.id
        if 'type' in self.kwargs:
            #print 'type is ' + str(self.kwargs['type'])
            if 'subtype' not in self.kwargs:
                if self.kwargs['type'] == 'notifications':
                    user_id = self.request.user.id
                    queryset = Notification.objects(owner = user_id)
                else:
                    queryset = None
            else:
                if self.kwargs['type'] == 'notifications' and self.kwargs['subtype'] == 'unread':
                    queryset = Notification.objects(Q(owner = user_id) & Q(read = False))
                elif self.kwargs['type'] == 'notifications' and self.kwargs['subtype'] == 'all':
                    queryset = Notification.objects(owner = user_id)
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


#@api_view(['POST'])
@renderer_classes((JSONRenderer,))    
def setUnread(request, **kwargs):
    try:
        if kwargs['type'] == 'notifications':
            post_data = json.loads(request.body)
            ids = post_data['ids[]']
            #ids = request.POST.getlist('ids[]')
            #print 'arr is ' + str(ids)
            if ids:
                for id in ids:
                    #print 'id is ' + str(id)
                    existingRecord = Notification.objects(id = id).update(set__read = True)
            result = {'message' : str(len(ids)) + ' records updated'}
            return JsonResponse(result, safe=False)
    except Exception as e:
                return JsonResponse({'Error' : str(e)})

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getCount(request, **kwargs):
        user_id = request.user.id
        if 'type' in kwargs:
            try:
                if kwargs['type'] == 'notifications':
                    count = Notification.objects(owner = user_id).count()
                    unread_count = Notification.objects(Q(owner = user_id) & Q(read = False)).count()
                else: 
                    count =  'Nothing to report'
                result = {'count' : count, 'unread_count' : unread_count}
                return JsonResponse(result, safe=False)
            except Exception as e:
                return JsonResponse({'Error' : str(e)})
    
#chat rooms begin here
@api_view(['GET'])
def rooms(request, id):
    """
    Homepage - lists all rooms
    """
    company_id = request.user.company_id
    company = Company.objects(company_id=company_id).first()
    company_id = company.id
    rooms = []
    rooms = ChatRoom.objects(company=company_id).all()
    serializer = ChatroomSerializer(rooms, many=True) 
    return Response(serializer.data)  
    #context = {"rooms": }
    #return render(request, template, context)
    #return JsonResponse(context)

@api_view(['GET'])
def getUserRooms(request, id):
    try:
        #print 'in user room'
        user_id = request.user.id
        company_id = request.user.company_id
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
        chatUsersRoomIds = ChatUser.objects(Q(user=user_id) & Q(company=company_id))
        #subscribedRooms = ChatRoom.objects(id__in=chatUsersRoomIds)
        #print 'rooms are ' + str(len(subscribedRooms))
        serializer = ChatuserSerializer(chatUsersRoomIds, many=True) 
        return Response(serializer.data)  
    except Exception as e:
        return Response('Error: ' + str(e))    
    
@api_view(['GET'])
def getUserNotJoinedRooms(request, id):
    try:
        #print 'in user room'
        user_id = request.user.id
        company_id = request.user.company_id
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
        #print ' user id is ' + str(user_id)
        roomIds = []
        chatUsers = ChatUser.objects(Q(user=user_id) & Q(company=company_id)).all()
        for chatUser in chatUsers:
            roomIds.append(chatUser.room.id)
        #print 'rooms1 are ' + str(len(chatUsersRoomIds))
        notJoinedRooms = ChatRoom.objects(Q(id__nin=roomIds)  & Q(company=company_id))
        #print 'rooms are ' + str(len(subscribedRooms))
        serializer = ChatroomSerializer(notJoinedRooms, many=True) 
        return Response(serializer.data)  
    except Exception as e:
        return Response(str(e)) 

@api_view(['GET'])
def getUserSlackMembership(request, id):
    try:
        #print 'in user room'
        user_id = request.user.id
        company_id = request.user.company_id
        slck_auth_needed = False
        slck_user_auth_needed = False
#         company = Company.objects(company_id=company_id).first()
#         company_id = company.id
        existingIntegration= CompanyIntegration.objects(company_id=company_id).first()
        if existingIntegration is None or 'slck' not in existingIntegration['integrations']:
            return JsonResponse({'slck_auth_needed' : True})
        #token = existingIntegration['integrations']['slck']
        userOauthRecord = UserOauth.objects(user_id= ObjectId(user_id)).first()
        if userOauthRecord is None:
            return JsonResponse({'slck_user_auth_needed' : True})
        if 'slck_access_token' in userOauthRecord and userOauthRecord['slck_access_token'] is not None and userOauthRecord['slck_access_token'] != "":
            token = userOauthRecord['slck_access_token']
        else:
            return JsonResponse({'slck_user_auth_needed' : True})
            
        slck = Slack(None, None, None, None, token)
        channels = json.loads(slck.api_call("channels.list")) 
        groups = json.loads(slck.api_call("groups.list")) 
        ims = json.loads(slck.api_call("im.list")) 
        users = json.loads(slck.api_call("users.list")) 
        if not users['ok']:
            raise ValueError('Error while retrieving users from Slack')
        rtm = slck.rtm_connect()
        return JsonResponse({'slack_channels': channels, 'slack_groups': groups, 'slack_ims': ims, 'users': users['members'], 'rtm': rtm, 'slck_auth_needed': False, 'slck_user_auth_needed': slck_user_auth_needed })  
    except Exception as e:
        return Response('Error: ' + str(e))   

@api_view(['GET'])
def getUserSlackMessages(request, id):
    try:
        #print 'in user room'
        user_id = request.user.id
        company_id = request.user.company_id
        slack_id = request.GET.get("id")
        slack_type = request.GET.get("type")
#         company = Company.objects(company_id=company_id).first()
#         company_id = company.id
        existingIntegration= CompanyIntegration.objects(company_id=company_id).first()
        if existingIntegration is None or 'slck' not in existingIntegration['integrations']:
            return JsonResponse(None)
        #token = existingIntegration['integrations']['slck']
        userOauthRecord = UserOauth.objects(user_id= ObjectId(user_id)).first()
        if userOauthRecord is None:
            return JsonResponse(None)
        if 'slck_access_token' in userOauthRecord and userOauthRecord['slck_access_token'] is not None:
            token = userOauthRecord['slck_access_token']
        else:
            return JsonResponse(None)
        slck = Slack(None, None, None, None, token)
        messages = None
        params = {'channel': slack_id, 'inclusive': 1, 'count': 1000}
        if slack_type == 'group':
            messages = json.loads(slck.api_call("groups.history", **params)) 
        elif slack_type == 'channel':
            messages = json.loads(slck.api_call("channels.history", **params)) 
        elif slack_type == 'im':
            messages = json.loads(slck.api_call("im.history", **params)) 
        if not messages['ok']:
            raise ValueError('Error while retrieving messages from Slack')
        messages_list = messages['messages']
        rtm = slck.rtm_connect()
        users = json.loads(slck.api_call("users.list")) 
        if not users['ok']:
            raise ValueError('Error while retrieving users from Slack')
        
#         for message in messages_list: #join the user info to each message
#             #print 'msg is ' + str(message['user'])
#             for user in users['members']:
#                 if 'user' in message and message['user'] == user['id']:
#                     message['user_real_name'] = user['profile']['real_name']
#                     message['user_name'] = user['name']
#                     message['user_image_url'] = user['profile']['image_72']
#                     break
        
        return JsonResponse({'slack_messages': messages, 'users': users['members'], 'rtm': rtm}, safe=False)  
    except Exception as e:
        print 'error occurred: ' + str(e)
        return Response('Error: ' + str(e))   
    
@api_view(['POST'])
@renderer_classes((JSONRenderer,))   
def user_create_slack_message(request): #this is only for messages with attachments (e.g. Snapshots). Simple messages are sent via websocket from the client
    try:
        post_data = json.loads(request.body)
        channel_id = post_data['channel_id']
        message = post_data['message']
        #company_id = post_data['company_id'] 
        user_id = request.user.id
        company_id = request.user.company_id
        if 'snapshot_id' in post_data:
            snapshot_id = post_data['snapshot_id']
        else:
            snapshot_id = None
        print 'snap id ' + str(snapshot_id)
        existingIntegration= CompanyIntegration.objects(company_id=company_id).first()
        if existingIntegration is None or 'slck' not in existingIntegration['integrations']:
            return JsonResponse(None)
        #token = existingIntegration['integrations']['slck']
        userOauthRecord = UserOauth.objects(user_id= ObjectId(user_id)).first()
        if userOauthRecord is None:
            return JsonResponse(None)
        if 'slck_access_token' in userOauthRecord and userOauthRecord['slck_access_token'] is not None:
            token = userOauthRecord['slck_access_token']
        else:
            return JsonResponse(None)
        slck = Slack(None, None, None, None, token)
        attachments = []
        if snapshot_id is not None:
            snapshot = Snapshot.objects(id=ObjectId(snapshot_id)).first()
            if snapshot is None:
                raise ValueError('Snapshot not found!')
            attachment = {
                          "fallback": "New Claritix" + snapshot['chart_name'] + " chart snapshot - http://app.claritix.io/snapshots/" + snapshot_id,
                          "pretext": "New Claritix chart snapshot",
                          "title": "Claritix snapshot - " +  snapshot['chart_name'] + " as of " + strftime('%Y-%m-%d %H:%M:%S', snapshot['updated_date'].timetuple()),
                          "title_link": "http://app.claritix.io/snapshots/" + snapshot_id,
                          "text": "Click above link to view the snapshot within Claritix",
                          "color": "#0491c3",
                          "author_name": "Claritix",
                          "author_link": "http://claritix.io",
                          "author_icon": "http://app.claritix.io/static/images/logo-icon-16x16.png"
                          }
            attachments.append(attachment)
        print 'attachme ' + str(attachments)
        
        params = {'channel': channel_id, 'text': message, 'as_user': True, "attachments": json.dumps(attachments)}
        
        result = json.loads(slck.api_call("chat.postMessage", **params))
        
        return JsonResponse({"result": result}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

    
@api_view(['GET'])
def room(request, id):
    """
    Show a room
    """
    #context = {"room": get_object_or_404(ChatRoom, slug=slug)}

    if not request.session.get("has_session"):
        request.session["has_session"] = True

    room = request.session.session_key
    serializer = ChatroomSerializer(room, many=False) 
    return Response(serializer.data) 
    #context = {"room": room}
    #return render(request, template, context)


def create(request):
    name = request.POST.get("name")
    if name:
        room, created = ChatRoom.objects(name=name).update(upsert=True)
        return redirect(room)
    return redirect(room)

@api_view(['POST'])
@renderer_classes((JSONRenderer,))   
def user_join_room(request):
    try:
        post_data = json.loads(request.body)
        user_id = post_data['user_id']
        nickname = post_data['nickname']
        room = post_data['room_id']
        company_id = post_data['company_id'] 
        
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
        
        chatUser = ChatUser(user=user_id, room=room, company=company_id, nickname=nickname)
        chatUser.save()
        return JsonResponse({"message": "You have joined the channel", "roomId" : room}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
        
    
@api_view(['POST'])
@renderer_classes((JSONRenderer,))   
def user_create_room(request):
    try:
        post_data = json.loads(request.body)
        user_id = post_data['user_id']
        nickname = post_data['nickname'] #redundant but needed
        room_name = post_data['room_name']
        room_description = post_data['room_description']
        company_id = post_data['company_id'] 
        
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
    
        chatRoom = ChatRoom(owner=user_id, name=room_name, description=room_description, company=company_id, nickname=nickname)
        chatRoom.save()
        serializer = ChatroomSerializer(chatRoom, many=False) 
        chatUser = ChatUser(user=user_id, room=chatRoom.id, company=company_id, nickname=nickname)
        chatUser.save()
        return JsonResponse({"message": "Channel created and you have joined it", "room" : serializer.data}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['POST'])
@renderer_classes((JSONRenderer,))   
def user_create_message(request):
    try:
        post_data = json.loads(request.body)
        user_id = post_data['user_id']
        nickname = post_data['nickname'] #redundant but needed
        room = post_data['room_id']
        message = post_data['message']
        company_id = post_data['company_id'] 
        if 'snapshot_id' in post_data:
            snapshot_id = post_data['snapshot_id']
        else:
            snapshot_id = None
        
        company = Company.objects(company_id=company_id).first()
        company_id = company.id
    
        if snapshot_id is not None:
            chatUserMessage = ChatUserMessage(user=user_id, room=room, message=message, company=company_id, nickname=nickname, snapshot=snapshot_id) #, 
        else:
            chatUserMessage = ChatUserMessage(user=user_id, room=room, message=message, company=company_id, nickname=nickname)
        chatUserMessage.save()
        serializer = ChatusermessageSerializer(chatUserMessage, many=False) 
        return JsonResponse({"message": "Message created", "message" : serializer.data}, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

@api_view(['GET'])      
def room_get_messages(request, id):
    try:
        room_id = request.GET.get('roomId')
        user_id = request.user.id
        
        chatUserMessages = ChatUserMessage.objects(room=room_id).all()
        serializer = ChatusermessageSerializer(chatUserMessages, many=True) 
        return Response(serializer.data)  
    except Exception as e:
        return Response(str(e))
        