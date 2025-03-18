from datetime import datetime, timedelta
from .models import *
from rest_framework import serializers
from rest_framework.response import Response
from accounts.models import Dog
from accounts.serializers import DogSerializer

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = [
            'id',
            'writer',
            'is_writer',
            'like',
            'like_cnt',
            'is_liked',
            'comments_cnt',
            'created_at',
            'updated_at',
        ]
    image_1 = serializers.ImageField(use_url=True, required=False)
    image_2 = serializers.ImageField(use_url=True, required=False)
    image_3 = serializers.ImageField(use_url=True, required=False)

    writer = serializers.SerializerMethodField(read_only=True)
    def get_writer(self, instance):
        writer = instance.writer
        return writer.user_name
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
    
    comments = serializers.SerializerMethodField(read_only=True)
    def get_comments(self, instance):
        seriallizer = CommentSerializer(instance.comments, context=self.context, many=True)
        return seriallizer.data
    
    comments_cnt = serializers.SerializerMethodField(read_only=True)
    def get_comments_cnt(self, instance):
        return instance.comments.count()
    
    like_cnt = serializers.SerializerMethodField(read_only=True)
    def get_like_cnt(self, instance):
        return instance.like.count()
    
    is_writer = serializers.SerializerMethodField(read_only=True)
    def get_is_writer(self, instance):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return request.user == instance.writer
        return False

    is_liked = serializers.SerializerMethodField(read_only=True)
    def get_is_liked(self, instance):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return instance.like.filter(id=request.user.id).exists()
        return False

class PostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'writer',
            'content',
            'image_1',
            'category',
            'region',
            'blood',
            'is_liked',
            'like_cnt',
            'comments_cnt',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'writer',
            'is_liked',
            'like_cnt',
            'comments_cnt',
            'created_at',
            'updated_at',
        ]
    image_1 = serializers.ImageField(use_url=True, required=False)

    writer = serializers.SerializerMethodField(read_only=True)
    def get_writer(self, instance):
        writer = instance.writer
        return writer.user_name

    is_liked = serializers.SerializerMethodField(read_only=True)
    def get_is_liked(self, instance):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return instance.like.filter(id=request.user.id).exists()
        return False


    like_cnt = serializers.SerializerMethodField(read_only=True)
    def get_like_cnt(self, instance):
        return instance.like.count()

    comments_cnt = serializers.SerializerMethodField(read_only=True)
    def get_comments_cnt(self, instance):
        return instance.comments.count()

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
        
class CommentSerializer(serializers.ModelSerializer):
    post = serializers.SerializerMethodField(read_only = True)
    def get_post(self, instance):
        post = instance.post
        return post.id
    
    writer = serializers.SerializerMethodField(read_only = True)
    def get_writer(self, instance):
        return instance.writer.user_name
    
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
        
    profile_image = serializers.SerializerMethodField(read_only=True)
    def get_profile_image(self, instance):
        user = instance.writer
        dog = Dog.objects.filter(user=user, represent=True).first()
        if dog:
            # DogSerializer에 context 전달
            return DogSerializer(dog, context=self.context).data['dog_image']
        return None
    
    is_writer = serializers.SerializerMethodField(read_only=True)
    def get_is_writer(self, instance):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return request.user == instance.writer
        return False
    
    user_email = serializers.SerializerMethodField(read_only=True)
    def get_user_email(self, instance):
        user = instance.writer
        return user.email

    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = [
            'id',
            'post',
            'writer',
            'profile_image',
            'is_writer',
            'created_at',
            'updated_at',
            'user_email'
        ]

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'keyword', 'searched_at']