from json import JSONDecodeError
import os, requests, environ, jwt
from pathlib import Path

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, mixins, status
from .serializers import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.shortcuts import redirect, render, get_object_or_404
from project.settings import SECRET_KEY
from allauth.socialaccount.models import SocialAccount

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

class RegisterAPIView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # jwt 토큰 생성
            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)
            res = Response(
                {
                    "user": serializer.data,
                    "success": "회원가입에 성공하였습니다.",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )
            
            # jwt 토큰 => 쿠키에 저장
            res.set_cookie("access", access_token, httponly=True)
            res.set_cookie("refresh", refresh_token, httponly=True)
            
            return res
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        # 유저 인증
        user = authenticate(
            email=request.data.get("email"), password=request.data.get("password")
        )
        if user is not None:
            serializer = UserSerializer(user)
            # jwt 토큰 생성
            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)
            res = Response(
                {
                    "user": serializer.data,
                    "message": "login success",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )
            # jwt 토큰 => 쿠키에 저장
            res.set_cookie("access", access_token, httponly=True)
            res.set_cookie("refresh", refresh_token, httponly=True)
            return res
        else:
            return Response({"error": "ⓘ 아이디와 비밀번호를 정확히 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    def post(self, request):
        # 쿠키에 저장된 토큰 삭제 => 로그아웃 처리
        access = request.COOKIES.get('access', None)
        if access is not None:
            response = Response(
                {"success": "로그아웃 성공!"},
                status=status.HTTP_202_ACCEPTED
            )
            response.delete_cookie("access")
            response.delete_cookie("refresh")
        else:
            response = Response({"detail": "자격 인증데이터(authentication credentials)가 제공되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)
        return response

class AuthAPIView(APIView):
    def get(self, request):
        try:
            # access token을 decode 해서 유저 id 추출
            access = request.COOKIES['access']
            payload = jwt.decode(access, SECRET_KEY, algorithms=['HS256'])
            pk = payload.get('user_id')
            user = get_object_or_404(User, pk=pk)
            serializer = UserSerializer(instance=user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except jwt.exceptions.ExpiredSignatureError:
            # 토큰 만료 시 토큰 갱신
            data = {'refresh': request.COOKIES.get('refresh', None)}
            serializer = TokenRefreshSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                access = serializer.data.get('access', None)
                refresh = serializer.data.get('refresh', None)
                payload = jwt.decode(access, SECRET_KEY, algorithms=['HS256'])
                pk = payload.get('user_id')
                user = get_object_or_404(User, pk=pk)
                serializer = UserSerializer(instance=user)
                res = Response(serializer.data, status=status.HTTP_200_OK)
                res.set_cookie('access', access)
                res.set_cookie('refresh', refresh)
                return res
            raise jwt.exceptions.InvalidTokenError
        except jwt.exceptions.InvalidTokenError:
            return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

class DeleteAccountAPIView(APIView):
    def delete(self, request):
        if request.user.is_authenticated:
            # 유저 삭제
            user = request.user
            user.delete()
            
            # 관련 쿠키 삭제
            response = Response(
                {"success": "계정이 삭제되었습니다."},
                status=status.HTTP_204_NO_CONTENT
            )
            response.delete_cookie("access")
            response.delete_cookie("refresh")
            return response
        else:
            return Response(
                {"message": "Unauthorized"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
# 카카오 로그인
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR,'.env'))
BASE_URL=env('BASE_URL')
KAKAO_CALLBACK_URI = BASE_URL + '/api/accounts/kakao/callback'

def kakao_login(request):
    client_id = os.environ.get("SOCIAL_AUTH_KAKAO_CLIENT_ID")
    return redirect(f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code&scope=account_email,profile_nickname,profile_image")

def kakao_callback(request):
    client_id = os.environ.get("SOCIAL_AUTH_KAKAO_CLIENT_ID")
    code = request.GET.get("code")

    # Access Token 요청
    token_request = requests.get(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code"
        f"&client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&code={code}"
    )
    token_response_json = token_request.json()

    # 에러 발생 시 중단
    if "error" in token_response_json:
        return JsonResponse({'err_msg': 'failed to get access token'}, status=400)

    access_token = token_response_json.get("access_token")
    profile_request = requests.post(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_json = profile_request.json()

    # 사용자 정보 가져오기
    kakao_account = profile_json.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    email = kakao_account.get("email")
    nickname = profile.get("nickname")

    if not email:
        return JsonResponse({'err_msg': 'email not provided'}, status=400)

    # 유저 인증 or 생성
    user, created = User.objects.get_or_create(email=email)

    if created:
        # 새 유저 생성 시 추가 정보 설정
        user.user_name = nickname if nickname else None
        user.set_unusable_password()
        user.save()

    # JWT 토큰 생성
    token = TokenObtainPairSerializer.get_token(user)
    refresh_token = str(token)
    access_token = str(token.access_token)

    response = JsonResponse({
        "message": "success",
        "token": {
            "access": access_token,
            "refresh": refresh_token,
        }
    })
    response.set_cookie(
        "access",
        access_token,
        httponly=True,
        secure=True,  # HTTPS를 사용하는 경우
        samesite="Lax",  # CSRF 공격 방지
        max_age=60 * 60,  # 1시간 (초 단위)
    )
    response.set_cookie(
        "refresh",
        refresh_token,
        httponly=True,
        secure=True,  # HTTPS를 사용하는 경우
        samesite="Lax",  # CSRF 공격 방지
        max_age=7 * 24 * 60 * 60,  # 7일 (초 단위)
    )
    return response
        
class KakaoLogin(SocialLoginView):
    adapter_class = kakao_view.KakaoOAuth2Adapter
    callback_url = KAKAO_CALLBACK_URI
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # 소셜 로그인 처리 후 유저 정보 가져오기
        user = self.request.user
        
        # JWT 토큰 생성
        token = TokenObtainPairSerializer.get_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)

        # 토큰 포함한 응답 반환
        response.data.update({
            "token": {
                "access": access_token,
                "refresh": refresh_token,
            }
        })
        return response
    
class DogViewSet(viewsets.ModelViewSet):
    queryset = Dog.objects.all()
    serializer_class = DogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 현재 사용자와 관련된 강아지들만 반환
        return Dog.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 새로운 강아지 등록 시 처리
        user = self.request.user
        existing_dogs = Dog.objects.filter(user=user)

        if not existing_dogs.exists():
            # 첫 번째 강아지 등록 시 represent=True로 설정
            serializer.save(user=user, represent=True)
        else:
            if serializer.validated_data.get('represent', False):
                # represent=True 요청 시 기존 강아지들의 represent 값을 False로 변경
                existing_dogs.update(represent=False)
            serializer.save(user=user)

    def perform_update(self, serializer):
        # 강아지 정보 업데이트 시 처리
        instance = self.get_object()

        if serializer.validated_data.get('represent', False):
            # represent=True 요청 시, 해당 유저의 다른 강아지 represent를 False로 설정
            Dog.objects.filter(user=instance.user).exclude(id=instance.id).update(represent=False)
        serializer.save()