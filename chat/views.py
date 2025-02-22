from rest_framework import generics, serializers, status
from rest_framework.response import Response
from .models import ChatRoom, Message, User
from .serializers import ChatRoomSerializer, MessageSerializer
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.db.models import Count
from django.conf import settings


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
        user1_email = self.request.data.get('user1_email')
        user2_email = self.request.data.get('user2_email')

        if not user1_email or not user2_email:
            raise ValidationError({'detail': 'user1_email과 user2_email은 필수입니다.'})

        user1, _ = User.objects.get_or_create(email=user1_email)
        user2, _ = User.objects.get_or_create(email=user2_email)

        # 정확히 두 명의 유저만 포함된 채팅방 찾기
        existing_chatroom = ChatRoom.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).annotate(num_participants=Count('participants')).filter(num_participants=2).first()

        if existing_chatroom:
            serializer = ChatRoomSerializer(existing_chatroom, context={'request': self.request})
            raise ImmediateResponseException(Response(serializer.data, status=status.HTTP_200_OK))

        chatroom = serializer.save()
        chatroom.participants.add(user1, user2)

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        if not room_id:
            return Response({'detail': 'room_id 파라미터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Message.objects.filter(room_id=room_id)
        if not queryset.exists():
            raise Http404('해당 room_id로 메시지를 찾을 수 없습니다.')
        return queryset
