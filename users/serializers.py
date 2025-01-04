from .models import *
from rest_framework import serializers
from accounts.models import Dog

class AddDogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.user_name', read_only=True)
    
    class Meta:
        model = Dog
        fields = '__all__'
