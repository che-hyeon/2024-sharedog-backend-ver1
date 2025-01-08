from django.db import models
from accounts.models import User
# Create your models here.
class Totaltest(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)
    score = models.IntegerField(null=False, blank=False,default=0)
    is_test = models.BooleanField(default=False)