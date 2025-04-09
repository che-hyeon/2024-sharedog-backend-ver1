from django.db import models
from accounts.models import User
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Create your models here.
def image_upload_path(instance, filename):
    return f'{instance.pk}/{filename}'

class Post(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50)
    writer = models.ForeignKey(User, on_delete=models.CASCADE)
    # writer = models.CharField(max_length=30)
    content = models.CharField(max_length=500)
    REGION_TYPES = [
        (None, '지역'),
        ('서울', '서울'),
        ('경기', '경기'),
        ('인천', '인천'),
        ('강원', '강원'),
        ('경상', '경상'),
        ('충청', '충청'),
        ('전라', '전라'),
        ('제주', '제주'),
    ]
    region = models.CharField(max_length=50, choices=REGION_TYPES, default='지역')

    CATEGORY_TYPES = [
        (None, '카테고리'),
        ('긴급헌혈', '긴급헌혈'),
        ('궁금해요', '궁금해요'),
        ('얘기해요', '얘기해요'),
        ('후기에요', '후기에요')
    ]
    category = models.CharField(max_length=30, choices=CATEGORY_TYPES, default='카테고리')

    DOG_BLOOD_TYPES = [
        (None, '혈액형'),
        ('전체', '전체'),
        ('DEA 1-', 'DEA 1-'),
        ('DEA 1.1', 'DEA 1.1'),
        ('DEA 1.2', 'DEA 1.2'),
        ('DEA 3', 'DEA 3'),
        ('DEA 4', 'DEA 4'),
        ('DEA 5', 'DEA 5'),
        ('DEA 7', 'DEA 7'),
    ]
    blood = models.CharField(max_length=30, choices=DOG_BLOOD_TYPES, default='혈액형')
    image_1 = models.ImageField(upload_to=image_upload_path, null=True, blank=True)
    image_2 = models.ImageField(upload_to=image_upload_path, null=True, blank=True)
    image_3 = models.ImageField(upload_to=image_upload_path, null=True, blank=True)

    like = models.ManyToManyField(User, related_name='likes', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        # 먼저 부모 save() 호출해서 id(pk)를 확보
        super().save(*args, **kwargs)

        for image_field in ['image_1', 'image_2', 'image_3']:
            img = getattr(self, image_field)
            if img:
                self.compress_image(img, image_field)
    
    def compress_image(self, image_field_file, image_field_name):
        img = Image.open(image_field_file)
        
        # Pillow는 RGB 모드만 JPEG 저장 가능
        if img.mode != 'RGB':
            img = img.convert('RGB')

        output = BytesIO()
        img.save(output, format='JPEG', quality=70)  # quality 낮추면 용량 줄어듦
        output.seek(0)

        # 새 이미지로 교체
        compressed_image = ContentFile(output.read(), name=image_field_file.name)
        setattr(self, image_field_name, compressed_image)

        # 다시 save (업데이트)
        super().save(update_fields=[image_field_name])


class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    post = models.ForeignKey(Post, null=False, blank=False, on_delete=models.CASCADE, related_name='comments')
    writer = models.ForeignKey(User, on_delete=models.CASCADE)
    # writer = models.CharField(max_length=30)
    content = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_histories')
    keyword = models.CharField(max_length=255)
    searched_at = models.DateTimeField(auto_now_add=True)

class Notice(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=40)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)