from django.contrib import admin
from .models import User, Dog  # 모델 임포트

# 모델 등록
admin.site.register(User)
admin.site.register(Dog)
