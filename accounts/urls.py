from django.urls import path, include
from rest_framework import routers

from django.conf.urls.static import static
from django.conf import settings

from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

app_name = "accounts"

dog_router = routers.SimpleRouter(trailing_slash=False)
dog_router.register('dog', DogViewSet, basename='dog')

urlpatterns = [
    path("signup", RegisterAPIView.as_view(), name="signup"),  # 회원가입
    path("login", LoginAPIView.as_view(), name="login"),       # 로그인
    path("logout", LogoutAPIView.as_view(), name="logout"),    # 로그아웃
    path("auth", AuthAPIView.as_view(), name="auth"),          # 유저 정보 확인
    path("delete-account", DeleteAccountAPIView.as_view(), name="delete_account"),
    path("auth/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path('kakao/login', kakao_login, name='kakao_login'),
    path('kakao/callback', kakao_callback, name='kakao_callback'),
    path('kakao/login/finish', KakaoLogin.as_view(), name='kakao_login_todjango'),
    path('', include(dog_router.urls)),
]
