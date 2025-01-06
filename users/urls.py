from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter

from django.conf.urls.static import static
from django.conf import settings
from .views import AddDogViewSet, MyPageViewSet

app_name = "users"

router = DefaultRouter()
router.register('dogs', AddDogViewSet, basename='dog')
router.register('mypage', MyPageViewSet, basename='mypage')

urlpatterns = [
    path('', include(router.urls)),  # 라우터 URL 포함
]