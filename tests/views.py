from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from .models import Totaltest, TestCheck
from .serializers import TotaltestSerializer, TestCheckSerializer

class TotaltestViewSet(ModelViewSet):
    """
    Totaltest 모델을 관리하는 뷰셋
    """
    queryset = Totaltest.objects.all()
    serializer_class = TotaltestSerializer

    def perform_create(self, serializer):
        """
        Totaltest 생성 시 현재 로그인한 사용자와 연결
        score가 5점이면 is_test를 True로 설정
        """
        instance = serializer.save(user=self.request.user)
        if instance.score == 5:
            instance.is_test = True
            instance.save()

    def perform_update(self, serializer):
        """
        Totaltest 업데이트 시 score가 5점이면 is_test를 True로 설정
        """
        instance = serializer.save()
        if instance.score == 5:
            instance.is_test = True
            instance.save()

class TestCheckView(ModelViewSet):
    queryset = TestCheck.objects.all()
    serializer_class = TestCheckSerializer

    def perform_create(self, serializer):
        user = self.request.user  # 로그인한 사용자 가져오기
        
        if user is None or user.is_anonymous:  # 로그인하지 않은 경우 체크
            raise ValidationError({"user": "로그인한 사용자만 데이터를 생성할 수 있습니다."})
        
        TestCheck.objects.filter(user=user).delete()
        serializer.save(user=user, is_test=True)
