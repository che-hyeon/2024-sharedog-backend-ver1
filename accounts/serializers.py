from .models import *
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'user_name', 'phone']

    def create(self, validated_data):
        user = User.objects.create_user(
            email = validated_data['email'],
            password = validated_data['password'],
            user_name = validated_data.get('user_name', ''),
            phone = validated_data.get('phone', '')
        )
        user.save()
        return user
    
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
    user = serializers.SerializerMethodField(read_only=True)
    def get_user(self, instance):
        user = instance.user
        return user.user_name