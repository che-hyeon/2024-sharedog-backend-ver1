from rest_framework import viewsets, generics, serializers, status
from rest_framework.response import Response
from .models import ChatRoom, Message, User, Promise
from .serializers import ChatRoomSerializer, MessageSerializer, PromiseSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.db.models import Count
from django.conf import settings
from django.utils.timezone import get_current_timezone
from collections import defaultdict
from rest_framework.views import APIView
from django.db.models import Q

class ImmediateResponseException(Exception):
    def __init__(self, response):
        self.response = response


class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        user_email = self.request.user.email
        if not user_email:
            raise ValidationError({'detail': 'Email 파라미터가 필요합니다.'})  # ValidationError를 그대로 발생
        return ChatRoom.objects.filter(participants__email=user_email)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except ImmediateResponseException as e:
            return e.response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        current_user = self.request.user
        other_user_email = self.request.data.get('user_email')

        if not other_user_email:
            raise ValidationError({'detail': 'user_email은 필수입니다.'})

        other_user, _ = User.objects.get_or_create(email=other_user_email)

        # 정확히 두 명의 유저만 포함된 채팅방 찾기
        existing_chatroom = ChatRoom.objects.annotate(num_participants=Count('participants')).filter(
            num_participants=2,
            participants=current_user
        ).filter(participants=other_user).first()
        if existing_chatroom:
            serializer = ChatRoomSerializer(existing_chatroom, context={'request': self.request})
            raise ImmediateResponseException(Response(serializer.data, status=status.HTTP_200_OK))

        chatroom = serializer.save()
        chatroom.participants.add(current_user, other_user)

class MessageListView(APIView):
    def get(self, request, room_id, *args, **kwargs):
        if not room_id:
            return Response({'detail': 'room_id 파라미터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        messages = Message.objects.filter(room_id=room_id).order_by("timestamp")
        if not messages.exists():
            raise Http404('해당 room_id로 메시지를 찾을 수 없습니다.')

        # 현재 로그인한 사용자
        current_user = request.user

        # 채팅방 정보 가져오기
        try:
            chat_room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return Response({'detail': '채팅방을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 상대방 정보 가져오기
        opponent = chat_room.participants.exclude(id=current_user.id).first()


        user_info = {
            "current_user": {
                "user_id": current_user.id,
                "email": current_user.email,
                "name": current_user.user_name
            },
            "opponent": {
                "user_id": opponent.id,
                "email": opponent.email,
                "name": opponent.user_name
            }
        }

        # 날짜별 메시지 그룹화
        grouped_messages = self.group_messages_by_date(messages, request)
        return Response({"user_info": user_info, "messages_by_date": grouped_messages})

    def group_messages_by_date(self, messages, request):
        """메시지를 날짜별로 그룹화"""
        tz = get_current_timezone()
        grouped_messages = defaultdict(list)

        for msg in messages:
            message_time = msg.timestamp.astimezone(tz)
            date_str = message_time.strftime("%Y년 %m월 %d일")
            serialized_msg = MessageSerializer(msg, context={'request': request}).data
            grouped_messages[date_str].append(serialized_msg)

        # 반환 형태 정리
        return [{"date": date, "messages": msgs} for date, msgs in grouped_messages.items()]
        


class PromiseViewSet(viewsets.ModelViewSet):
    queryset = Promise.objects.all()
    serializer_class = PromiseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 로그인한 사용자가 포함된 예약만 조회"""
        user = self.request.user
        return Promise.objects.filter(Q(user1=user) | Q(user2=user))
