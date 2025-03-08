from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import Dog,User
from .serializers import AddDogSerializer, MyPageSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet
from community.models import Post
from .serializers import MyPostSerializer

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

class MyPageViewSet(ReadOnlyModelViewSet):
    """
    사용자 정보와 represent=True 강아지 이미지를 반환하는 뷰셋
    """
    queryset = User.objects.all()
    serializer_class = MyPageSerializer

    def get_queryset(self):
        """
        현재 로그인한 사용자만 반환
        """
        return User.objects.filter(id=self.request.user.id)

class MyPostViewSet(ReadOnlyModelViewSet):
    serializer_class = MyPostSerializer

    def get_queryset(self):
        return Post.objects.filter(writer=self.request.user)