from channels.routing import ProtocolTypeRouter, URLRouter
import os
from django.core.asgi import get_asgi_application

# 환경변수 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Django ASGI 애플리케이션 초기화
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import chat.routing
from project.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )     
            ),
        ),
    ),
})
