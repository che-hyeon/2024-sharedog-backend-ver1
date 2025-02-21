from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter

from django.conf.urls.static import static
from django.conf import settings
from .views import TotaltestViewSet, TestCheckView

app_name = "tests"

router = DefaultRouter()
router.register('', TotaltestViewSet, basename='score')

default_router = routers.SimpleRouter(trailing_slash=False)
default_router.register('check', TestCheckView, basename='check')

urlpatterns = [
    path('', include(router.urls)),  # 라우터 URL 포함
    path('', include(default_router.urls))
]