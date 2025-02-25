from django.contrib import admin
from .models import Post, Comment, SearchHistory
# Register your models here.
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(SearchHistory)