# import os
# from celery import Celery

# # Django의 settings 모듈을 Celery의 기본 설정으로 사용
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# app = Celery("project")

# # Django settings에서 Celery 관련 설정을 가져오도록 설정
# app.config_from_object("django.conf:settings", namespace="CELERY")

# # Django의 INSTALLED_APPS에 등록된 앱에서 tasks.py 파일을 자동으로 찾도록 설정
# app.autodiscover_tasks()

# @app.task(bind=True)
# def debug_task(self):
#     print(f"Request: {self.request!r}")
