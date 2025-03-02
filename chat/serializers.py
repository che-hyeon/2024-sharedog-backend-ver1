from rest_framework import serializers
from .models import ChatRoom, Message, User, Promise
from accounts.models import User, Dog
from accounts.serializers import DogSerializer
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from django.utils.timezone import get_current_timezone
from collections import defaultdict
import locale

class PromiseSerializer(serializers.ModelSerializer):
    day = serializers.DateField(format="%Y-%m-%d")  # 날짜 포맷 지정
    time = serializers.TimeField(format="%H:%M")  # 시간 포맷 지정

    class Meta:
        model = Promise
        fields = '__all__'
        read_only_fields = ['id', 'user1', 'user2', 'created_at', 'updated_at']

    day_display = serializers.SerializerMethodField()
    time_display = serializers.SerializerMethodField()
    def get_day_display(self, obj):
        """0000년 00월 00일 0요일 형식으로 반환 (한글 요일)"""
        return obj.day.strftime("%m월 %d일 %a요일").replace("Mon", "월").replace("Tue", "화").replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일")

    def get_time_display(self, obj):
        """오전/오후 00:00 형식으로 변환"""
        hour = obj.time.hour
        minute = obj.time.minute
        period = "오전" if hour < 12 else "오후"
        return f"{period} {hour}:{minute:02d}"

    def create(self, validated_data):
        request_user = self.context['request'].user  # 현재 요청한 유저 (예약 요청자)
        room_id = self.context['view'].kwargs.get('room_id')  # URL에서 room_id 가져오기

        # 채팅방이 존재하는지 확인
        chat_room = ChatRoom.objects.filter(id=room_id).first()
        if not chat_room:
            raise serializers.ValidationError("채팅방이 존재하지 않습니다.")

        # 채팅방 참여자 가져오기
        participants = list(chat_room.participants.all())
        if request_user not in participants:
            raise serializers.ValidationError("채팅방에 참여한 사용자만 예약할 수 있습니다.")

        # 상대방(user2) 찾기
        user2 = participants[0] if participants[1] == request_user else participants[1]

        # 예약 정보 자동 설정
        validated_data['user1'] = request_user  # 예약 요청자
        validated_data['user2'] = user2  # 상대방

        promise = super().create(validated_data)

        # 채팅방에 자동 메시지 추가
        message_text = "헌혈 약속을 만들었어요"
        Message.objects.create(
            room=chat_room,
            sender=request_user,  # 예약을 요청한 사람이 sender
            text=message_text,
            promise = promise
        )

        return promise
    
class MessageSerializer(serializers.ModelSerializer):
    formatted_time = serializers.SerializerMethodField()
    opponent_profile = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    is_sender = serializers.SerializerMethodField()
    promise_info = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id",
                "text",
                "formatted_time",
                "room",
                "sender",
                "sender_name",
                "is_sender",
                "opponent_profile",
                "promise_info",
                "promise",
                # "is_read"
                ]

    def get_formatted_time(self, obj):
        """오전/오후 HH:MM 형식으로 변환"""
        tz = get_current_timezone()
        message_time = obj.timestamp.astimezone(tz)
        period = "오전" if message_time.hour < 12 else "오후"
        hour = message_time.hour if message_time.hour <= 12 else message_time.hour - 12
        return f"{period} {hour}:{message_time.minute:02d}"

    def get_opponent_profile(self, obj):
        """메시지 작성자가 요청한 유저가 아닐 때만 상대방 프로필 반환"""
        request_user = self.context["request"].user
        if obj.sender != request_user:
            dog = Dog.objects.filter(user=obj.sender, represent=True).first()
            if dog:
                return DogSerializer(dog, context=self.context).data.get('dog_image', None)  # 상대방 프로필 데이터 추가
        return None  # 내가 작성한 메시지는 opponent_profile 없음

    def get_sender_name(self, instance):
        sender = instance.sender
        return sender.user_name

    def get_is_sender(self, instance):
        sender = instance.sender
        user = self.context["request"].user
        return sender == user

    def get_promise_info(self, obj):
        """메시지와 연결된 예약 정보를 반환"""
        if obj.promise:
            return PromiseSerializer(obj.promise, context=self.context).data
        return None
    
class GroupedMessageSerializer(serializers.Serializer):
    """날짜별 메시지 그룹화"""
    date = serializers.CharField()
    messages = MessageSerializer(many=True)

    @staticmethod
    def group_messages_by_date(messages, request):
        """메시지를 날짜별로 그룹화"""
        tz = get_current_timezone()
        grouped_messages = defaultdict(list)

        for msg in messages:
            message_time = msg.timestamp.astimezone(tz)
            date_str = message_time.strftime("%Y년 %m월 %d일")
            grouped_messages[date_str].append(msg)

        # 직렬화하여 반환 (request context 추가)
        return [
            {"date": date, "messages": MessageSerializer(msgs, many=True, context={"request": request}).data}
            for date, msgs in grouped_messages.items()
        ]

class ChatRoomSerializer(serializers.ModelSerializer):
    latest_message = serializers.SerializerMethodField()
    latest_message_time = serializers.SerializerMethodField()
    opponent_email = serializers.SerializerMethodField()
    opponent_user = serializers.SerializerMethodField()
    opponent_user_profile = serializers.SerializerMethodField()
    # messages = MessageSerializer(many=True, read_only=True, source="messages.all")
    participants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    is_promise = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id',
                'participants',
                'latest_message',
                'latest_message_time',
                'opponent_email',
                'opponent_user',
                'opponent_user_profile',
                'is_promise'
                ]
    def get_latest_message(self, obj):
        latest_msg = Message.objects.filter(room=obj).order_by('-timestamp').first()
        return latest_msg.text if latest_msg else None

    def get_latest_message_time(self, obj):
        latest_msg = Message.objects.filter(room=obj).order_by('-timestamp').first()
        if not latest_msg:
            return None
        
        tz = get_current_timezone()  # 현재 설정된 타임존 가져오기
        message_time = latest_msg.timestamp.astimezone(tz)  # 서버 타임존에서 현재 타임존으로 변환
        now = datetime.now(tz)  # 현재 시간 가져오기 (타임존 적용)

        if message_time.date() == now.date():
            period = "오전" if message_time.hour < 12 else "오후"
            hour = message_time.hour if message_time.hour <= 12 else message_time.hour - 12
            return f"{period} {hour}:{message_time.minute:02d}"
        
        elif message_time.date() == (now - timedelta(days=1)).date():
            return "어제"
        
        elif message_time.year == now.year:
            return message_time.strftime("%m월 %d일")
        
        else:
            return message_time.strftime("%Y.%m.%d")


    def get_opponent_email(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            opponent = obj.participants.exclude(id=request_user.id).first()
            return opponent.email if opponent else None
        return None
    
    def get_opponent_user(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            opponent = obj.participants.exclude(id=request_user.id).first()
            return opponent.user_name if opponent else None
        return None
    
    def get_opponent_user_profile(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            opponent = obj.participants.exclude(id=request_user.id).first()
            if opponent:
                # 상대방의 대표 Dog 객체에서 dog_image 가져오기
                dog = Dog.objects.filter(user=opponent, represent=True).first()
                if dog:
                    return DogSerializer(dog, context=self.context).data.get('dog_image', None)
        return None
    
    def get_is_promise(self, instance):
        latest_msg = Message.objects.filter(room=instance).order_by('-timestamp').first()
        return latest_msg.promise is not None if latest_msg else False