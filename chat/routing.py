from django.urls import path

from chat import consumers

websocket_urlpatterns = [
    path("ws/room/<int:room_id>/messages", consumers.ChatConsumer.as_asgi()),
    path("ws/user/chatrooms", consumers.UserChatConsumer.as_asgi()),
]