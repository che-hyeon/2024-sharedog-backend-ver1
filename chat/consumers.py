from collections import defaultdict
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    # 현재 접속 중인 사용자 저장 (그룹별 관리)
    connected_users = defaultdict(set)

    async def connect(self):
        try:
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            
            if not await self.check_room_exists(self.room_id):
                raise ValueError('채팅방이 존재하지 않습니다.')
            
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_add(group_name, self.channel_name)

            # 현재 사용자 이메일
            token = self.scope.get('query_string').decode().split('=')[1]
        
            # JWT 인증을 통해 사용자 정보를 가져옴
            user = await self.authenticate(token)
            current_user_email = user.email

            # 상대방 이메일 가져오기
            room = await self.get_room_by_id(self.room_id)
            opponent_email = await self.get_opponent_email(room, current_user_email)

            # 현재 사용자 등록
            self.connected_users[group_name].add(current_user_email)

            # 읽지 않은 메시지 처리
            await self.mark_unread_messages_as_read(room, current_user_email, opponent_email)

            await self.accept()
        except Exception as e:
            await self.send_json({'error': f'연결 오류: {str(e)}'})

    async def disconnect(self, close_code):
        try:
            group_name = self.get_group_name(self.room_id)
            
            # 사용자 제거
            token = self.scope.get('query_string').decode().split('=')[1]
        
            # JWT 인증을 통해 사용자 정보를 가져옴
            user = await self.authenticate(token)
            current_user_email = user.email
            self.connected_users[group_name].discard(current_user_email)

            # 그룹에서 제거
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except Exception:
            pass

    async def receive_json(self, content):
        try:
            token = self.scope.get('query_string').decode().split('=')[1]
        
            # JWT 인증을 통해 사용자 정보를 가져옴
            user = await self.authenticate(token)
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

            # ✅ 수정된 부분: 상대방이 현재 접속 중인지 확인
            is_read = opponent_email in self.connected_users[group_name]

            await self.save_message(room, sender_email, message, is_read)

            await self.channel_layer.group_send(group_name, {
                'type': 'chat_message',
                'message': message,
                'sender_email': sender_email,
                'is_read': is_read
            })
        except ValueError as e:
            await self.send_json({'error': str(e)})

    async def chat_message(self, event):
        try:
            message = event['message']
            sender_email = event['sender_email']
            is_read = event['is_read']
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
        except Exception:
            await self.send_json({'error': '메시지 전송 실패'})

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
        try:
            sender = User.objects.get(email=sender_email)
        except User.DoesNotExist:
            raise ValueError(f"발신자 {sender_email}를 찾을 수 없습니다.")
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
    def authenticate(self, token):
        """JWT 토큰을 사용하여 인증된 사용자 가져오기"""
        try:
            # JWT 인증을 사용하여 사용자 인증
            validated_token = JWTAuthentication().get_validated_token(token)
            user = JWTAuthentication().get_user(validated_token)
            return user
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None
