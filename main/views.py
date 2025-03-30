from rest_framework.decorators import action
from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.viewsets import ViewSet
from .serializers import *
from rest_framework.permissions import AllowAny

from chat.models import Promise
from rest_framework.response import Response
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from math import ceil
# Create your views here.

class MainViewSet(ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        user = request.user  # 현재 로그인된 사용자
        region = request.query_params.get('region', None)
        context = {'request': request, 'region': region}
        serializer = MainSerializer(instance=user, context=context)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='blood')
    def blood_status(self, request):
        user = request.user
        promises = Promise.objects.filter(Q(user1=user) | Q(user2=user))
        count_blood = promises.count()

        latest_promise = promises.order_by('-day').first()
        count_month = None

        if latest_promise:
            latest_day = latest_promise.day
            next_month = (latest_day.month + 4)  # 헌혈 가능 예상 월
            today = date.today()

            if next_month > 12:
                next_month -= 12  # 연도 넘어가면 월만 계산

            if today.month < next_month:
                count_month = next_month - today.month
            else:
                count_month = 0  # 이미 가능

        return Response({
            "id": user.id,
            "count_blood": count_blood,
            "count_month": count_month
        })