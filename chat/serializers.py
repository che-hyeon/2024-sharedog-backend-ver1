from rest_framework import serializers
from .models import ChatRoom, Message, User

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"

class ChatRoomSerializer(serializers.ModelSerializer):
    latest_message = serializers.SerializerMethodField()
    opponent_email = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True, source="messages.all")
    participants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = ('id', 'participants', 'latest_message', 'opponent_email', 'messages')

    def get_latest_message(self, obj):
        latest_msg = Message.objects.filter(room=obj).order_by('-timestamp').first()
        return latest_msg.text if latest_msg else None

    def get_opponent_email(self, obj):
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            opponent = obj.participants.exclude(id=request_user.id).first()
            return opponent.email if opponent else None
        return None