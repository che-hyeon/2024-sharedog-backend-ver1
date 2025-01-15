from .models import *
from rest_framework import serializers

class TotaltestSerializer(serializers.ModelSerializer):
    """
    Totaltest 모델을 직렬화하는 시리얼라이저
    """
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Totaltest
        fields = ['id', 'user_name', 'score', 'is_test']
        read_only_fields = ['id', 'user_name', 'is_test']  # user_name과 is_test는 읽기 전용

    def get_user_name(self, obj):
        """
        user 필드의 user_name을 반환
        """
        return obj.user.user_name if obj.user else None