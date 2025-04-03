from collections import defaultdict
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer

from django.db.models import Count, Q

import re

from channels.layers import get_channel_layer

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
            
            unread_messages = await self.get_unread_messages(room, opponent_email)

            await self.accept()
            print(unread_messages)

            for msg in unread_messages:
                print(f"보낸 메시지: {msg['message']}")
                # 모든 참여자에게 메시지를 전송
                await self.send_json({
                    'type': 'chat_message',
                    'message': msg['message'],
                    'sender_email': msg['sender_email'],
                    'is_read': True  # b는 읽음 처리된 상태로 받음
                })

            # ✅ 3️⃣ 메시지를 읽음 처리 (update 실행)
            await self.mark_messages_as_read(room, opponent_email)
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_send(group_name, {
                'type': 'update_read_status',
                'room_id': self.room_id,
                'is_read': True
            })
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
        image = content.get("image", None)
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
        is_read = opponent_email in self.connected_users[group_name]

        # 메시지 저장
        await self.save_message(room, sender_email, message, is_read, image)

        await self.channel_layer.group_send(group_name, {
            'type': 'chat_message',
            'message': message,
            'sender_email': sender_email,
            'is_read': is_read,
            'image_url': image.url if image else None
        })

        if not is_read:
            unread_count = await self.get_unread_messages_count(room, opponent_email)
            # 여기서 UserChatConsumer로 업데이트 요청
            user_group_name = re.sub(r'[^a-zA-Z0-9._-]', '_', f"user_{opponent_email}")
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

    async def update_read_status(self, event):
        """
        상대방이 채팅을 읽었을 때, 기존 메시지들의 읽음 상태를 업데이트하여 보냄
        """
        await self.send_json({
            'type': 'update_read_status',
            'room_id': event['room_id'],
            'is_read': event['is_read']
        })

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
    def check_room_exists(self, room_id):
        return ChatRoom.objects.filter(id=room_id).exists()

    @database_sync_to_async
    def get_unread_messages(self, room, opponent_email):
        if opponent_email is None:
            return []
        """
        읽지 않은 메시지를 조회만 하는 함수 (update는 하지 않음)
        """
        unread_messages = list(Message.objects.filter(
            room=room, sender__email=opponent_email, is_read=False
        ))

        messages_to_return = [
            {"message": msg.text, "sender_email": msg.sender.email} for msg in unread_messages
        ]

        return messages_to_return
    @database_sync_to_async
    def mark_messages_as_read(self, room, opponent_email):
        if opponent_email is None:
            return
        """
        읽지 않은 메시지를 읽음 처리하는 함수
        """
        Message.objects.filter(room=room, sender__email=opponent_email, is_read=False).update(is_read=True) 
    
    @database_sync_to_async
    def get_opponent_email(self, room, current_user_email):
        opponent = room.participants.exclude(email=current_user_email).first()
        if opponent:
            return opponent.email
        return None
    
    @database_sync_to_async
    def get_unread_messages_count(self, room, user_email):
        return Message.objects.filter(room=room, sender__email=user_email, is_read=False).count()
    
    @database_sync_to_async
    def save_message(self, room, sender_email, message_text, is_read, image):
        sender = User.objects.get(email=sender_email)
        Message.objects.create(room=room, sender=sender, text=message_text, is_read=is_read, image=image)

class UserChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.user_email = self.scope["user"].email
            self.group_name = re.sub(r'[^a-zA-Z0-9._-]', '_', f"user_{self.user_email}")

            await self.channel_layer.group_add(self.group_name, self.channel_name)

            chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)

            await self.accept()

            await self.send_json({
                "type": "chatrooms_list",
                "chatrooms": chatrooms
            })
        except Exception as e:
            await self.send_json({'error': f'연결 오류: {str(e)}'})

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
        try:
            rooms = await database_sync_to_async(
                lambda: list(ChatRoom.objects.filter(participants__email=user_email))
            )()

            chatrooms_info = []
            for room in rooms:
                opponent_name = await database_sync_to_async(room.get_other_participant_name)(self.scope["user"])
                unread_count = await database_sync_to_async(
                    lambda: Message.objects.filter(room=room, is_read=False).exclude(sender__email=user_email).count()
                )()

                latest_message = await database_sync_to_async(
                    lambda: Message.objects.filter(room=room).order_by('-timestamp').first()
                )()

                last_message_text = latest_message.text if latest_message else ""

                chatrooms_info.append({
                    "room_id": room.id,
                    "opponent_name": opponent_name,
                    "unread_messages": unread_count,
                    "last_message": last_message_text,
                })

            return chatrooms_info
        except Exception as e:
            print(f"Error in get_chatrooms_with_unread_messages: {e}")
            return []

    async def update_unread_count(self, event):
        room_id = event['room_id']
        unread_messages = event['unread_messages']

        chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)

        for room in chatrooms:
            if room["room_id"] == int(room_id):
                room["unread_messages"] = unread_messages

    async def update_chatrooms(self, event):
        """ 채팅방 리스트를 즉시 갱신 """
        chatrooms = await self.get_chatrooms_with_unread_messages(self.user_email)
        await self.send_json({
            'type': 'chatrooms_list',
            'chatrooms': chatrooms
        })