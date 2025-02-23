from django.urls import path, include
from rest_framework import routers
from . import views

from .views import ReservationViewSet

reservation_router = routers.SimpleRouter(trailing_slash=False)
reservation_router.register('reservation', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('rooms', views.ChatRoomListCreateView.as_view(), name='chat_rooms'),
    path('<int:room_id>/messages', views.MessageListView.as_view(), name='chat_messages'),
    path('', include(reservation_router.urls))
]