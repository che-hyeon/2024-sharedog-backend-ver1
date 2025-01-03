import jwt
from rest_framework.views import APIView
from .serializers import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.shortcuts import render, get_object_or_404
from project.settings import SECRET_KEY


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