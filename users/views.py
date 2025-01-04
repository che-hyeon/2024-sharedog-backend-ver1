from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import Dog
from .serializers import AddDogSerializer

class AddDogViewSet(viewsets.ModelViewSet):
    queryset = Dog.objects.all()
    serializer_class = AddDogSerializer

    def get_queryset(self):
        """
        사용자별 강아지 목록만 조회하도록 쿼리셋 필터링.
        """
        user = self.request.user
        return Dog.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        강아지 추가 시 represent가 True라면 다른 강아지의 represent를 False로 설정
        """
        user = self.request.user
        if serializer.validated_data.get('represent'):
            # 현재 사용자의 다른 강아지의 represent를 False로 설정
            Dog.objects.filter(user=user, represent=True).update(represent=False)
        serializer.save(user=user)

    def perform_update(self, serializer):
        """
        강아지 업데이트 시 represent가 True라면 다른 강아지의 represent를 False로 설정
        """
        user = self.request.user
        if serializer.validated_data.get('represent'):
            # 현재 사용자의 다른 강아지의 represent를 False로 설정
            Dog.objects.filter(user=user, represent=True).update(represent=False)
        serializer.save()