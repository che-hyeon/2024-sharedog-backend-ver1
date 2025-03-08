from .models import *
from rest_framework import serializers
from accounts.models import User, Dog
from community.models import Post

class AddDogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.user_name', read_only=True)
    
    class Meta:
        model = Dog
        fields = '__all__'

class DogImageSerializer(serializers.ModelSerializer):
    """
    강아지 모델(Dog)을 직렬화하는 시리얼라이저
    """
    class Meta:
        model = Dog
        fields = ['dog_image']  # 필요한 필드만 포함

class MyPageSerializer(serializers.ModelSerializer):
    """
    사용자(User) 모델과 연결된 강아지(Dog) 모델 데이터를 포함하는 시리얼라이저
    """
    dogs = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user_name','email', 'dogs']
    
    def get_dogs(self, obj):
        """
        represent=True인 강아지만 반환
        """
        represent_dogs = Dog.objects.filter(user=obj, represent=True)  # represent=True로 필터링
        return DogImageSerializer(represent_dogs, many=True, context=self.context).data

class MyPostSerializer(serializers.ModelSerializer):
    writer = serializers.CharField(source='writer.user_name',read_only=True)

    class Meta:
        model = Post
        fields = '__all__'