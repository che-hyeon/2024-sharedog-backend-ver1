from rest_framework import generics, serializers, status
from rest_framework.response import Response
from .models import ChatRoom, Message, User
from .serializers import ChatRoomSerializer, MessageSerializer
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.db.models import Count
from django.conf import settings
from django.utils.timezone import get_current_timezone
from collections import defaultdict
from rest_framework.views import APIView

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

        # 날짜별 메시지 그룹화
        grouped_messages = self.group_messages_by_date(messages, request)
        return Response(grouped_messages)

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