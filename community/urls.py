from django.urls import path, include
from rest_framework import routers

from django.conf.urls.static import static
from django.conf import settings

from .views import *

app_name = "community"

default_router = routers.SimpleRouter(trailing_slash=False)
default_router.register('home', PostViewSet, basename='home')

comment_router = routers.SimpleRouter(trailing_slash=False)
comment_router.register('comments', CommentViewSet, basename='comments')

search_history_router = routers.SimpleRouter(trailing_slash=False)
search_history_router.register('search', SearchHistoryViewSet, basename='search')

notice_router = routers.SimpleRouter(trailing_slash=False)
notice_router.register('notice', NoticeViewSet, basename='notice')
urlpatterns = [
    path('', include(default_router.urls)),
    path("home/<int:post_id>/", include(comment_router.urls)),
    path('', include(search_history_router.urls)),
    path('', include(notice_router.urls))
]