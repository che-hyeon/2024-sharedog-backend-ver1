from json import JSONDecodeError
import os, requests, environ, jwt
from pathlib import Path

from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, mixins, status
from rest_framework.viewsets import ViewSet
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
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
            
            return Response(
                {
                    "user": serializer.data,
                    "message": "회원가입에 성공하였습니다.",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
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
            
            return Response(
                {
                    "user": serializer.data,
                    "message": "로그인 성공",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response({"error": "아이디와 비밀번호를 정확히 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')

        if not email or not new_password:
            return Response({"error": "email과 새로운 비밀번호를 모두 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "가입되지 않은 이메일입니다."}, status=status.HTTP_404_NOT_FOUND)
        
        user.set_password(new_password)
        user.save()

        return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Refresh token 블랙리스트 처리 (필요 시 구현)
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # requires `django-rest-framework-simplejwt` with blacklist enabled

            return Response({"message": "로그아웃 성공"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AuthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DeleteAccountAPIView(APIView):
    def delete(self, request):
        if request.user.is_authenticated:
            # 유저 삭제
            user = request.user
            user.delete()
            
            response = Response(
                {"success": "계정이 삭제되었습니다."},
                status=status.HTTP_204_NO_CONTENT
            )
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
FRONT_URL=env('FRONT_URL')
FRONT_REDIRECT_URI = FRONT_URL + '/kakao/callback'
KAKAO_CALLBACK_URI = BASE_URL + '/api/accounts/kakao/callback'

def kakao_login(request):
    client_id = os.environ.get("SOCIAL_AUTH_KAKAO_CLIENT_ID")
    return redirect(f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code&scope=account_email,profile_nickname,profile_image")

def kakao_callback(request):
    client_id = os.environ.get("SOCIAL_AUTH_KAKAO_CLIENT_ID")
    code = request.GET.get("code")

    if not code:
        return JsonResponse({"err_msg": "Authorization code not provided"}, status=400)

    # 인증 코드를 프론트엔드로 전달
    redirect_url = f"{FRONT_REDIRECT_URI}?code={code}"
    return redirect(redirect_url)

@api_view(["POST"])
@permission_classes([AllowAny])
def exchange_token(request):
    client_id = os.environ.get("SOCIAL_AUTH_KAKAO_CLIENT_ID")
    code = request.data.get("code")

    if not code:
        return JsonResponse({"err_msg": "Code not provided"}, status=400)

    # Access Token 요청
    token_request = requests.get(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code"
        f"&client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&code={code}"
    )
    token_response_json = token_request.json()

    if "error" in token_response_json:
        return JsonResponse({"err_msg": "Failed to get access token"}, status=400)

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
        return JsonResponse({"err_msg": "Email not provided"}, status=400)

    # 유저 인증 or 생성
    user, created = User.objects.get_or_create(email=email)

    if created:
        user.user_name = nickname if nickname else None
        user.set_unusable_password()
        user.save()

    # JWT 토큰 생성
    token = TokenObtainPairSerializer.get_token(user)
    refresh_token = str(token)
    access_token = str(token.access_token)

    return JsonResponse({
        "message": "success",
        "is_signed": created,
        "token": {
            "access": access_token,
            "refresh": refresh_token,
        }
    })
        
class KakaoLogin(SocialLoginView):
    adapter_class = kakao_view.KakaoOAuth2Adapter
    callback_url = KAKAO_CALLBACK_URI
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # 소셜 로그인 처리 후 유저 정보 가져오기
        user = self.request.user

        created = not User.objects.filter(email=user.email).exists()
        
        # JWT 토큰 생성
        token = TokenObtainPairSerializer.get_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)

        # 토큰 포함한 응답 반환
        response.data.update({
            "is_signed": created,
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

class CheckEmailExistsView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        exists = User.objects.filter(email=email).exists()
        return Response({"exists": exists}, status=status.HTTP_200_OK)
    
from django.core.mail import EmailMessage
from .utils import sendEmailHelper

from django.core.cache import caches

client = caches["email_verification"] 

class EmailVerifyView(APIView):

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email or "@" not in email:
            return Response({"detail": "Email is required and must be valid"}, status=status.HTTP_400_BAD_REQUEST)
    

        code = sendEmailHelper.make_random_code_for_register()
        client.set(email, code, timeout=300)
        message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; background-color: #f8f9fa; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);">
                <h2 style="color: #ff6f61;">🐶 나눠주개 이메일 인증</h2>
                <p style="font-size: 16px; color: #333;">안녕하세요! <br> 아래 인증 코드를 입력하여 이메일 인증을 완료해주세요.</p>
                <div style="font-size: 22px; font-weight: bold; color: #fff; background: #ff6f61; padding: 10px; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    {code}
                </div>
                <p style="font-size: 14px; color: #555; margin-top: 15px;">이 코드는 5분 후 만료됩니다.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">이 메일은 자동 발송되었습니다. 문의 사항이 있다면 <a href="mailto:support@nanwoojugae.com" style="color: #ff6f61; text-decoration: none;">고객센터</a>로 문의해주세요.</p>
            </div>
        </body>
        </html>
        """
        subject = "[나눠주개] 이메일 인증"
        to = [email]
        mail = EmailMessage(subject=subject, body=message, to=to)
        mail.content_subtype = "html" # html형태로 템플릿을 만들었을 때 필요함
        mail.send()
        
        return Response({"detail": "Success to send Email"}, status=status.HTTP_202_ACCEPTED)

class EmailVerifyConfirmView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Email and code are required", "correct": False}, status=status.HTTP_400_BAD_REQUEST)

        # Redis에서 저장된 코드 가져오기
        stored_code = client.get(email)
        if not stored_code:
            return Response({"error": "Verification code expired or invalid", "correct": False}, status=status.HTTP_400_BAD_REQUEST)

        if stored_code != code:
            return Response({"error": "Incorrect verification code", "correct": False}, status=status.HTTP_400_BAD_REQUEST)

        # 이메일 인증 완료 처리 (예: User 모델에 is_verified 필드 업데이트)
        # user = User.objects.filter(email=email).first()
        # if user:
        #     user.is_verified = True
        #     user.save()

        # 인증 성공 시 Redis에서 코드 삭제
        client.delete(email)

        return Response({"detail": "Email verification successful", "correct": True}, status=status.HTTP_200_OK)
    
class MypageViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user  # 현재 로그인된 사용자
        context = {'request': request}
        serializer = MypageSerializer(instance=user, context=context)
        return Response(serializer.data)
