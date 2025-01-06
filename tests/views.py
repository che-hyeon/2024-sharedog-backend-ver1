from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Totaltest
from .serializers import TotaltestSerializer

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
