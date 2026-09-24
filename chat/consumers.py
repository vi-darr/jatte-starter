import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timesince import timesince

from .templatetags.chatextras import initials

from account.models import User
from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # join room group
        await self.get_room()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # If this is a reconnecting client (room already has messages),
        # send the message history so they can see previous conversation
        messages = await self.get_message_history()
        if messages:
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'messages': messages
            }))

        # Inform user
        if self.user.is_staff:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'users_update',
                }
            )

    async def disconnect(self, close_code):
        # leave room
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if not self.user.is_staff:
            await self.set_room_closed()

    async def receive(self, text_data):
        # Receive message from WebSocket (frontend)
        text_data_json = json.loads(text_data)
        type = text_data_json['type']
        message = text_data_json['message']
        name = text_data_json['name']
        agent = text_data_json.get('agent', '')

        print('Recieve:', type)

        if type == 'message':
            new_message = await self.create_message(name, message, agent)

            #send message to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'name': name,
                    'agent': agent,
                    'initials': initials(name),
                    'created_at': new_message.created_at.strftime('%H:%M')
                }
            )

        elif type == 'update':
            print('is update')
            # send update to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'writing_active',
                    'message': message,
                    'name': name,
                    'agent': agent,
                    'initials': initials(name),
                }
            )

    async def chat_message(self, event):
        # Send message to WebSocket (frontend)
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'message': event['message'],
            'name': event['name'],
            'agent': event['agent'],
            'initials': event['initials'],
            'created_at': event['created_at'],
        }))

    async def writing_active(self, event):
        # send writing is active to room
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'message': event['message'],
            'name': event['name'],
            'agent': event['agent'],
            'initials': event['initials'],
        }))

    async def users_update(self, event):
        # Send message to WebSocket (frontend)
        await self.send(text_data=json.dumps({
            'type': 'users_update',
        }))

    async def room_closed(self, event):
        # Notify client that the room has been closed
        await self.send(text_data=json.dumps({
            'type': 'room_closed',
        }))

    @sync_to_async
    def get_room(self):
        self.room = Room.objects.get(uuid=self.room_name)

    @sync_to_async
    def get_message_history(self):
        """Return all messages for this room so a reconnecting client
        can see the previous conversation."""
        messages = self.room.messages.all().order_by('created_at')
        result = []
        for msg in messages:
            result.append({
                'message': msg.body,
                'name': msg.sent_by,
                'agent': str(msg.created_by.pk) if msg.created_by else '',
                'initials': initials(msg.sent_by),
                'created_at': msg.created_at.strftime('%H:%M'),
            })
        return result

    @sync_to_async
    def create_message(self, sent_by, message, agent):
        message = Message.objects.create(sent_by=sent_by, body=message)

        if agent:
            message.created_by = User.objects.get(pk=agent)
            message.save()

        self.room.messages.add(message)

        return message

    @sync_to_async
    def set_room_closed(self):
        self.room = Room.objects.get(uuid=self.room_name)
        self.room.status = Room.CLOSED
        self.room.save()