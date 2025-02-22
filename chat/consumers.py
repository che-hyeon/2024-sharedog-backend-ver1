from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            
            if not await self.check_room_exists(self.room_id):
                raise ValueError('채팅방이 존재하지 않습니다.')
            
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_add(group_name, self.channel_name)
            await self.accept()
        except ValueError as e:
            await self.send_json({'error': str(e)})
            await self.close()

    async def disconnect(self, close_code):
        try:
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except Exception:
            pass

    async def receive_json(self, content):
        try:
            message = content['message']
            sender_email = content['sender_email']
            
            # 기존 room_id가 존재하는 경우, 새 메시지 저장
            if hasattr(self, 'room_id') and await self.check_room_exists(self.room_id):
                room = await self.get_room_by_id(self.room_id)
            
            # 존재하지 않는 경우, 새 채팅방 생성
            else:
                participant1_email = content.get('participant1_email')
                participant2_email = content.get('participant2_email')

                if not participant1_email or not participant2_email:
                    raise ValueError("두 참가자 이메일이 필요합니다.")

                room = await self.get_or_create_room(participant1_email, participant2_email)
                self.room_id = str(room.id)  # 새 방 ID 설정

            group_name = self.get_group_name(self.room_id)
            await self.save_message(room, sender_email, message)

            await self.channel_layer.group_send(group_name, {
                'type': 'chat_message',
                'message': message,
                'sender_email': sender_email
            })
        except ValueError as e:
            await self.send_json({'error': str(e)})

    async def chat_message(self, event):
        try:
            message = event['message']
            sender_email = event['sender_email']
            await self.send_json({'message': message, 'sender_email': sender_email})
        except Exception:
            await self.send_json({'error': '메시지 전송 실패'})

    @staticmethod
    def get_group_name(room_id):
        return f"chat_room_{room_id}"

    @database_sync_to_async
    def get_or_create_room(self, email1, email2):
        user1, _ = User.objects.get_or_create(email=email1)
        user2, _ = User.objects.get_or_create(email=email2)

        room, created = ChatRoom.objects.get_or_create()
        room.participants.set([user1, user2])
        return room

    @database_sync_to_async
    def get_room_by_id(self, room_id):
        return ChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def save_message(self, room, sender_email, message_text):
        sender = User.objects.get(email=sender_email)
        Message.objects.create(room=room, sender=sender, text=message_text)

    @database_sync_to_async
    def check_room_exists(self, room_id):
        return ChatRoom.objects.filter(id=room_id).exists()
