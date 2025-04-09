from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter

from django.conf.urls.static import static
from django.conf import settings
from .views import AddDogViewSet, MyPageViewSet, MyPostViewSet, MyPromiseViewSet

app_name = "users"

router = DefaultRouter()
router.register('dogs', AddDogViewSet, basename='dog')
router.register('mypage', MyPageViewSet, basename='mypage')
router.register('mypost', MyPostViewSet, basename='mypost')

my_promise_router = routers.SimpleRouter(trailing_slash=False)
my_promise_router.register('mypromise', MyPromiseViewSet, basename='mypromise')

urlpatterns = [
    path('', include(router.urls)),  # 라우터 URL 포함
    path('', include(my_promise_router.urls))
]