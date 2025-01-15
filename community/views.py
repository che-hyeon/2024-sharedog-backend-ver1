from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import filters
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, mixins
from .models import *
from .serializers import *
from .permissions import *
from rest_framework.permissions import IsAuthenticated

# Create your views here.

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-created_at')

    def get_permissions(self):
        if self.action in ["update", "destroy", "partial_update"]:
            return [IsOwnerOrReadOnly()]
        return []

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', 'content']
    filterset_fields = ['category', 'region', 'blood']

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        serializer.save(writer=self.request.user)
    
    @action(methods=['POST'], detail=True)
    def likes(self, request, pk=None):
        like_post = self.get_object()
        if request.user == like_post.writer:
            response = Response({"error": "본인이 작성한 글에는 좋아요를 누를 수 없습니다."})
        else:
            if request.user in like_post.like.all():
                like_post.like.remove(request.user)
                like_post.save()
                response = Response({"success": "좋아요 취소 성공"})
            else:
                like_post.like.add(request.user)
                like_post.save()
                response = Response({"success": "좋아요 성공"})
        return response

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, post_id=None):
        post = get_object_or_404(Post, id=post_id)
        queryset = self.filter_queryset(self.get_queryset().filter(post=post).order_by('created_at'))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, post_id=None):
        post = get_object_or_404(Post, id=post_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post, writer=self.request.user)
        return Response(serializer.data)