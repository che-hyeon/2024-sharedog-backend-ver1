from django.urls import path, include
from rest_framework import routers
from . import views

from .views import PromiseViewSet

promise_router = routers.SimpleRouter(trailing_slash=False)
promise_router.register(r'rooms/(?P<room_id>\d+)/promise', PromiseViewSet, basename='promise')

urlpatterns = [
    path('rooms', views.ChatRoomListCreateView.as_view(), name='chat_rooms'),
    path('<int:room_id>/messages', views.MessageListView.as_view(), name='chat_messages'),
    path('', include(promise_router.urls))
]