from django.db import models
from accounts.models import User

# Create your models here.

class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["id"], name="unique_chat_room"
            )  # 중복 방지
        ]

    def __str__(self):
        return f"ChatRoom {self.id} - Participants: {', '.join(user.email for user in self.participants.all())}"

# ✅ Message 모델 (sender_email → sender를 User로 변경)
class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.email}: {self.text[:30]}"