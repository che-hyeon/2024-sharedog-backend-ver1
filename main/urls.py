from django.urls import path, include
from rest_framework import routers

from .views import *

from django.conf.urls.static import static
from django.conf import settings

app_name = "main"

default_router = routers.SimpleRouter(trailing_slash=False)
default_router.register('home', MainViewSet, basename='home')

urlpatterns = [
    path('', include(default_router.urls)),
]