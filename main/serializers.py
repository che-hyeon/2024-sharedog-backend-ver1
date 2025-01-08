from rest_framework import serializers
from accounts.models import *
from accounts.serializers import *
from community.serializers import *

class MainPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'image_1',
            'category',
            'region',
            'blood',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    image_1 = serializers.ImageField(use_url=True, required=False)

    created_at =serializers.SerializerMethodField(read_only=True)
    def get_created_at(self, instance):
        now = datetime.now(instance.created_at.tzinfo)
        time_difference = now - instance.created_at

        if time_difference < timedelta(days=1):
            if time_difference < timedelta(hours=1):
                if time_difference < timedelta(minutes=1):
                    return f"방금"
                return f"{int(time_difference.total_seconds() // 60)}분 전"
            return f"{int(time_difference.total_seconds() // 3600)}시간 전"
        else:
            return f"{time_difference.days}일 전"

class MainSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_name',
            'profile_image',
            'posts',
        ]
    
    posts = serializers.SerializerMethodField(read_only=True)
    def get_posts(self, instance):
        request = self.context.get('request', None)
        region = request.query_params.get('region', None)

        posts = Post.objects.filter(category="긴급헌혈").order_by('-created_at')
        if region:
            posts = posts.filter(region=region).order_by('-created_at')
        posts = posts[:3]
        serializer = MainPostSerializer(posts, many=True)
        return serializer.data
    
    profile_image = serializers.SerializerMethodField(read_only=True)
    def get_profile_image(self, instance):
        request = self.context.get('request', None)
        
        if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
            return None  # 요청이 없거나 인증되지 않은 사용자 처리
        
        user = request.user  # JWT 인증을 통해 설정된 현재 사용자
        # 현재 사용자의 대표 Dog 객체를 가져오기
        dog = Dog.objects.filter(user=user, represent=True).first()
        
        if dog:
            # DogSerializer에 context 전달 후 dog_image 반환
            return DogSerializer(dog, context=self.context).data.get('dog_image', None)
        
        return None