from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import filters, status
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, mixins
from .models import *
from .serializers import *
from .permissions import *
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

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

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        region = self.request.query_params.get('region')
        blood = self.request.query_params.get('blood')

        if category:
            queryset = queryset.filter(category=category)
        if region:
            queryset = queryset.filter(region=region)
        if blood:
            queryset = queryset.filter(blood=blood)

        return queryset

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

    def list(self, request, *args, **kwargs):
        query = request.query_params.get("search", "").strip()  # 검색어 가져오기
        response = super().list(request, *args, **kwargs)  # 기본 list 기능 실행

        if query:  # 검색어가 존재하면 기록 저장
            user = request.user
            if user.is_authenticated:
                search_entry, created = SearchHistory.objects.get_or_create(user=user, keyword=query, defaults={'searched_at': timezone.now()})
                if not created:
                    search_entry.searched_at = timezone.now()
                    search_entry.save()

                # 검색 기록이 10개를 초과하면 가장 오래된 기록 삭제
                search_history_qs = SearchHistory.objects.filter(user=user).order_by('-searched_at')
                if search_history_qs.count() > 10:
                    oldest_history = search_history_qs.last()
                    oldest_history.delete()

        return response
    
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

class SearchHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user).order_by('-searched_at')

    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_searches = self.get_queryset()[:10]  # 최근 10개 검색 기록 반환
        serializer = self.get_serializer(recent_searches, many=True)
        return Response(serializer.data)
    
class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notice.objects.all().order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:  # 🔹 superuser인지 체크
            return Response(
                {"detail": "공지사항 생성 권한이 없습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)