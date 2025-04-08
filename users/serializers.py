from .models import *
from rest_framework import serializers
from accounts.models import User, Dog
from community.models import Post
from chat.models import Promise
class AddDogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.user_name', read_only=True)
    
    class Meta:
        model = Dog
        fields = ['id','represent','user','dog_name','dog_age','weight','gender','neuter','blood','dog_image','created_at','updated_at']

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

    class Meta:
        model = Post
        fields = '__all__'

class MyPromiseSerializer(serializers.ModelSerializer):
    """
    현재 사용자의 약속(Promise) 데이터를 직렬화하는 시리얼라이저
    """
    other_user = serializers.SerializerMethodField(read_only=True)
    other_user_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Promise
        fields = ['id', 'day', 'time', 'place', 'other_user', 'other_user_image','created_at', 'updated_at']

    def get_other_user(self, obj):
        """
        현재 로그인한 사용자가 user1이면 user2의 이름, user2이면 user1의 이름 반환
        """
        request = self.context.get('request')
        if request and request.user:
            if obj.user1 == request.user:
                return obj.user2.user_name  # 상대방 = user2
            else:
                return obj.user1.user_name  # 상대방 = user1
        return None

    def get_other_user_image(self, obj):
        """
        상대방의 대표 강아지 사진을 반환 (대표 강아지가 없으면 첫 번째 강아지)
        """
        request = self.context.get('request')
        if request and request.user:
            other_user = obj.user2 if obj.user1 == request.user else obj.user1  # 상대방 찾기

            # 1️⃣ 대표 강아지가 있으면 대표 강아지 사진 반환
            dog = Dog.objects.filter(user=other_user, represent=True).first()

            # 2️⃣ 대표 강아지가 없으면 첫 번째 강아지 사진 반환
            if not dog:
                dog = Dog.objects.filter(user=other_user).first()

            if dog and dog.dog_image:
                return request.build_absolute_uri(dog.dog_image.url)  # 절대 URL 반환
        return None