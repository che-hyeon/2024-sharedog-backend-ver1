from .models import *
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'user_name']

    def create(self, validated_data):
        user = User.objects.create_user(
            email = validated_data['email'],
            password = validated_data['password'],
            user_name = validated_data.get('user_name', '')
        )
        user.save()
        return user
    
class MypageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'user_name', 'profile_image']

    profile_image = serializers.SerializerMethodField(read_only=True)
    def get_profile_image(self, instance):
        request = self.context.get('request', None)
        
        user = request.user  # JWT 인증을 통해 설정된 현재 사용자
        # 현재 사용자의 대표 Dog 객체를 가져오기
        dog = Dog.objects.filter(user=user, represent=True).first()
        
        if dog:
            # DogSerializer에 context 전달 후 dog_image 반환
            return DogSerializer(dog, context=self.context).data.get('dog_image', None)
        
        return None
    
    user_name = serializers.SerializerMethodField(read_only=True)
    def get_user_name(self, instance):
        request = self.context.get('request', None)

        return request.user.user_name

class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = '__all__'
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
        ]
    
    dog_image = serializers.ImageField(use_url=True, required=False)

    user = serializers.SerializerMethodField(read_only=True)
    def get_user(self, instance):
        user = instance.user
        return user.user_name