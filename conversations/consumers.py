import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Auth via token query param: ws://...?token=xxx
        qs = dict(p.split('=') for p in self.scope['query_string'].decode().split('&') if '=' in p)
        token_str = qs.get('token', '')
        try:
            token = AccessToken(token_str)
            self.user = await database_sync_to_async(User.objects.get)(id=token['user_id'])
        except (TokenError, User.DoesNotExist):
            await self.close()
            return

        # Join personal notification channel
        self.user_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Join all conversation rooms
        conv_ids = await self.get_conversation_ids()
        for cid in conv_ids:
            await self.channel_layer.group_add(f'conv_{cid}', self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        type_ = data.get('type')

        if type_ == 'send_message':
            await self.handle_send_message(data)
        elif type_ == 'join_conversation':
            conv_id = data.get('conversationId')
            if conv_id:
                await self.channel_layer.group_add(f'conv_{conv_id}', self.channel_name)

    async def handle_send_message(self, data):
        conv_id = data.get('conversationId')
        content = (data.get('content') or '').strip()
        if not conv_id or not content:
            return

        is_member = await self.check_membership(conv_id)
        if not is_member:
            return

        message = await self.save_message(conv_id, content)
        await self.channel_layer.group_send(f'conv_{conv_id}', {
            'type': 'chat_message',
            'conversationId': conv_id,
            'message': message,
        })

    # --- Channel layer event handlers ---
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'conversationId': event['conversationId'],
            'message': event['message'],
        }))

    async def conversation_created(self, event):
        await self.send(text_data=json.dumps({
            'type': 'conversation_created',
            'conversationId': event['conversationId'],
        }))

    # --- DB helpers ---
    @database_sync_to_async
    def get_conversation_ids(self):
        from conversations.models import Conversation
        return list(Conversation.objects.filter(members=self.user).values_list('id', flat=True))

    @database_sync_to_async
    def check_membership(self, conv_id):
        from conversations.models import ConversationMember
        return ConversationMember.objects.filter(conversation_id=conv_id, user=self.user).exists()

    @database_sync_to_async
    def save_message(self, conv_id, content):
        from conversations.models import Conversation, Message
        from conversations.serializers import MessageSerializer
        conv = Conversation.objects.get(id=conv_id)
        msg = Message.objects.create(conversation=conv, sender=self.user, content=content)
        return MessageSerializer(msg).data
