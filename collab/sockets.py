from __future__ import absolute_import, unicode_literals

import logging
from django.conf import settings
from kombu import BrokerConnection
from kombu.mixins import ConsumerMixin
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin
from socketio.sdjango import namespace

from collab.queues import notifications_queue
from collab.views import rooms

class LonelyRoomMixin(object):
    def __init__(self, *args, **kwargs):
        super(LonelyRoomMixin, self).__init__(*args, **kwargs)
        if 'rooms' not in self.session:
            self.session['rooms'] = set()  # a set of simple strings

    def join(self, room):
        """Lets a user join a room on a specific Namespace."""
        self.session['rooms'].add(self._get_room_name(room))

    def leave(self, room):
        """Lets a user leave a room on a specific Namespace."""
        self.session['rooms'].remove(self._get_room_name(room))

    def _get_room_name(self, room):
        return self.ns_name + '_' + room

    def emit_to_room(self, room, event, *args):
        """This is sent to all in the room (in this particular Namespace)"""
        pkt = dict(type="event",
                   name=event,
                   args=args,
                   endpoint=self.ns_name)
        room_name = self._get_room_name(room)
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'rooms' not in socket.session:
                print 'no room found'
                continue
            #if room_name in socket.session['rooms'] and self.socket != socket:
            if room_name in socket.session['rooms']:
                print 'room found ' + str(room_name)
                socket.send_packet(pkt)

@namespace('/notifications')
class NotificationsNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(NotificationsNamespace, self).__init__(*args, **kwargs)

    def get_initial_acl(self):
        return ['recv_connect']

    def recv_connect(self):
        if self.request.user.is_authenticated():
            self.lift_acl_restrictions()
            self.spawn(self._dispatch)
        else:
            self.disconnect(silent=True)

    def _dispatch(self):
        with BrokerConnection(settings.AMQP_URL) as connection:
            NotificationsConsumer(connection, self.socket, self.ns_name).run()


class NotificationsConsumer(ConsumerMixin):
    def __init__(self, connection, socket, ns_name):
        self.connection = connection
        self.socket = socket
        self.ns_name = ns_name

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[notifications_queue], callbacks=[self.process_notification])]

    def process_notification(self, body, message):
        self.socket.send_packet(dict(
            type='event',
            name='notification',
            args=(body,),
            endpoint=self.ns_name
        ))
        message.ack()

#below code from gevent-socketio docs example      
@namespace('/chat')
class ChatNamespace(BaseNamespace, LonelyRoomMixin, BroadcastMixin):
    nicknames = []

    def initialize(self):
#         roomsList = rooms(self.request, None).render()
#         roomsNames = []
#         for i in roomsList:
#             print 'list is ' + i
#             #roomsNames.append(i.name)
#         self.session['rooms'] = roomsNames
        self.logger = logging.getLogger("socketio.chat")
        print "Socketio session started"

    def log(self, message):
        self.logger.info("[{0}] {1}".format(self.socket.sessid, message))

    def on_join(self, room):
        self.room = room
        self.join(room)
        print 'join happened'
        return True

    def on_nickname(self, nickname):
        print("Creating the nickname: " + nickname)
        self.log('Nickname: {0}'.format(nickname))
        self.socket.session['nickname'] = nickname
        self.nicknames.append(nickname)
        self.broadcast_event('announcement', '%s has connected' % nickname)
        self.broadcast_event('nicknames', self.nicknames)
        return True, nickname

    def recv_disconnect(self):
        self.log('Disconnected')
        nickname = self.socket.session['nickname']
        self.nicknames.remove(nickname)
        self.broadcast_event('announcement', '%s has disconnected' % nickname)
        self.broadcast_event('nicknames', self.nicknames)
        self.disconnect(silent=True)
        return True

    def on_user_message(self, msg, room):
        self.log('User message: {0}'.format(msg["message"]))
        # TODO: dig into the logic of emit_to_room
        self.emit_to_room(room, 'msg_to_room',
                          self.socket.session['nickname'], msg)
        return True
    
    def on_user_typing(self, msg, room):
        #msg = msg.nickname + ' is typing...'
        print str(msg)
        #self.log('User typing: {0}'.format(msg["message"]))
        # TODO: dig into the logic of emit_to_room
        self.emit_to_room(room, 'user_typing',
                          self.socket.session['nickname'], msg)
        return True