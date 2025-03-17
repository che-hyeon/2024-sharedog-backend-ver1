from collections import defaultdict
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer

from django.db.models import Count, Q

import re

User = get_user_model()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    connected_users = defaultdict(set)

    async def connect(self):
        try:
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            if not await self.check_room_exists(self.room_id):
                raise ValueError('채팅방이 존재하지 않습니다.')

            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_add(group_name, self.channel_name)

            current_user_email = self.scope["user"].email
            print(current_user_email)

            room = await self.get_room_by_id(self.room_id)
            opponent_email = await self.get_opponent_email(room, current_user_email)

            self.connected_users[group_name].add(current_user_email)

            unread_count = await self.mark_unread_messages_as_read(room, current_user_email, opponent_email)

            await self.accept()

        except Exception as e:
            await self.send_json({'error': f'연결 오류: {str(e)}'})

    async def disconnect(self, close_code):
        group_name = self.get_group_name(self.room_id)
        current_user_email = self.scope["user"].email
        self.connected_users[group_name].discard(current_user_email)
        await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content):
        user = self.scope["user"]
        if user.is_anonymous:
            raise ValueError("인증된 사용자만 메시지를 보낼 수 있습니다.")

        sender_email = content['sender_email']
        message = content.get("message", "")
        if not message:
            raise ValueError("메시지가 비어 있습니다.")

        if hasattr(self, 'room_id') and await self.check_room_exists(self.room_id):
            room = await self.get_room_by_id(self.room_id)
        else:
            participant1_email = content.get('participant1_email')
            participant2_email = content.get('participant2_email')
            if not participant1_email or not participant2_email:
                raise ValueError("두 참가자 이메일이 필요합니다.")
            room = await self.get_or_create_room(participant1_email, participant2_email)
            self.room_id = str(room.id)

        if not self.room_id:
            raise ValueError("채팅방 ID를 찾을 수 없습니다.")
        
        group_name = self.get_group_name(self.room_id)
        opponent_email = await self.get_opponent_email(room, sender_email)
        is_read = False
        if group_name in self.connected_users:
            if opponent_email in self.connected_users[group_name]:
                is_read = True

        await self.save_message(room, sender_email, message, is_read)

        await self.channel_layer.group_send(group_name, {
            'type': 'chat_message',
            'message': message,
            'sender_email': sender_email,
            'is_read': is_read
        })

        if not is_read:
            unread_count = await self.get_unread_messages_count(room, opponent_email)
            # 여기서 UserChatConsumer로 업데이트 요청
            user_group_name = f"user_{opponent_email.replace('@', '_').replace('.', '_')}"
            await self.channel_layer.group_send(user_group_name, {
                "type": "update_unread_count",
                "room_id": self.room_id,
                "unread_messages": unread_count
            })

            # 채팅방 리스트 갱신을 요청
            await self.channel_layer.group_send(user_group_name, {
                "type": "update_chatrooms"
            })

    async def chat_message(self, event):
        message = event['message']
        sender_email = event['sender_email']
        is_read = event.get('is_read')
        response_data = {
            'message': message,
            'sender_email': sender_email,
            'is_read': is_read
        }
        if "promise_id" in event:
            response_data.update({
                "promise_id": event["promise_id"],
                "promise_day": event["promise_day"],
                "promise_time": event["promise_time"]
            })
        await self.send_json(response_data)

    @staticmethod
    def get_group_name(room_id):
        return f"chat_room_{room_id}"

    @database_sync_to_async
    def get_or_create_room(self, email1, email2):
        user1, _ = User.objects.get_or_create(email=email1)
        user2, _ = User.objects.get_or_create(email=email2)
        room, created = ChatRoom.objects.get_or_create(
            participants__in=[user1, user2]
        )
        if created:
            room.participants.set([user1, user2])
            room.save()
        return room

    @database_sync_to_async
    def get_room_by_id(self, room_id):
        return ChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def save_message(self, room, sender_email, message_text, is_read):
        sender = User.objects.get(email=sender_email)
        Message.objects.create(room=room, sender=sender, text=message_text, is_read=is_read)

    @database_sync_to_async
    def check_room_exists(self, room_id):
        return ChatRoom.objects.filter(id=room_id).exists()

    @database_sync_to_async
    def mark_unread_messages_as_read(self, room, sender_email, opponent_email):
        unread_messages = Message.objects.filter(room=room, sender__email=opponent_email, is_read=False)
        unread_messages.update(is_read=True)

    @database_sync_to_async
    def get_opponent_email(self, room, current_user_email):
        opponent = room.participants.exclude(email=current_user_email).first()
        if opponent:
            return opponent.email
        return None
    
    @database_sync_to_async
    def get_unread_messages_count(self, room, user_email):
        return Message.objects.filter(room=room, sender__email=user_email, is_read=False).count()

class UserChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_email = self.scope["user"].email
        self.group_name = re.sub(r'[^a-zA-Z0-9._-]', '_', f"user_{self.user_email}")

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)

        await self.accept()

        await self.send_json({
            "type": "chatrooms_list",
            "chatrooms": chatrooms
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if 'message' in content:
            room_id = content.get("room_id")
            message = content.get("message")

            chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)

            await self.send_json({
                "type": "chatrooms_list",
                "chatrooms": chatrooms
            })

            group_name = f"user_{self.user_email.replace('@', '_').replace('.', '_')}"
            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "update_chatrooms",
                    "room_id": room_id,
                }
            )

    async def get_chatrooms_with_unread_messages(self, user_email):
        rooms = await database_sync_to_async(lambda: list(ChatRoom.objects.filter(participants__email=user_email)))()

        chatrooms_info = []
        for room in rooms:
            opponant_name = await database_sync_to_async(room.get_other_participant_name)(self.scope["user"])
            unread_count = await database_sync_to_async(
                lambda: Message.objects.filter(room=room, is_read=False).exclude(sender__email=user_email).count()
            )()
            chatrooms_info.append({
                "room_id": room.id,
                "opponant_name": opponant_name,
                "unread_messages": unread_count
            })

        return chatrooms_info

    async def update_unread_count(self, event):
        room_id = event['room_id']
        unread_messages = event['unread_messages']

        chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)

        for room in chatrooms:
            if room["room_id"] == int(room_id):
                room["unread_messages"] = unread_messages

        await self.send_json({
            "type": "chatrooms_list",
            "chatrooms": chatrooms
        })

    async def update_chatrooms(self, event):
        """ 채팅방 리스트를 즉시 갱신 """
        chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)
        await self.send_json({
            'type': 'chatrooms_list',
            'chatrooms': chatrooms
        })
