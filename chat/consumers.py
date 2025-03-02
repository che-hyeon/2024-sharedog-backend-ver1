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
        except Exception as e:
            await self.send_json({'error': f'연결 오류: {str(e)}'})

    async def disconnect(self, close_code):
        try:
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except Exception:
            pass

    async def receive_json(self, content):
        try:
            # user = self.scope["user"]
            # if user.is_anonymous:
            #     raise ValueError("인증된 사용자만 메시지를 보낼 수 있습니다.")

            # sender_email = user.email
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
            await self.save_message(room, sender_email, message)
            # message_obj = await self.save_message(room, sender_email, message)

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
            # message_id = event.get('message_id')
            # is_read = event.get('is_read', False)

            # await self.send_json({
            #     'message': message,
            #     'sender_email': sender_email,
            #     'message_id': message_id,
            #     'is_read': is_read
            # })
        except Exception:
            await self.send_json({'error': '메시지 전송 실패'})

    # async def mark_messages_as_read(self, content):
    #     try:
    #         user = self.scope["user"]
    #         if user.is_anonymous:
    #             return

    #         if not hasattr(self, 'room_id'):
    #             return

    #         room = await self.get_room_by_id(self.room_id)
    #         opponent = await self.get_opponent(room, user)

    #         await self.mark_unread_messages_as_read(room, opponent)

    #         group_name = self.get_group_name(self.room_id)
    #         await self.channel_layer.group_send(group_name, {
    #             'type': 'chat_read',
    #             'reader_email': user.email
    #         })
    #     except Exception as e:
    #         print(f"Error in mark_messages_as_read: {e}")

    # async def chat_read(self, event):
    #     await self.send_json({'type': 'chat_read', 'reader_email': event['reader_email']})

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
            room.save()  # DB에 반영

        return room

    @database_sync_to_async
    def get_room_by_id(self, room_id):
        return ChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def save_message(self, room, sender_email, message_text):
        try:
            sender = User.objects.get(email=sender_email)
        except User.DoesNotExist:
            raise ValueError(f"발신자 {sender_email}를 찾을 수 없습니다.")

        Message.objects.create(room=room, sender=sender, text=message_text)
        # message = Message.objects.create(room=room, sender=sender, text=message_text)
        # return message

    @database_sync_to_async
    def check_room_exists(self, room_id):
        return ChatRoom.objects.filter(id=room_id).exists()

    # @database_sync_to_async
    # def mark_unread_messages_as_read(self, room, reader):
    #     Message.objects.filter(room=room, sender=reader, is_read=False).update(is_read=True)

    # @database_sync_to_async
    # def get_opponent(self, room, user):
    #     return room.participants.exclude(id=user.id).first()
