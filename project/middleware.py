from channels.db import database_sync_to_async
import jwt
from django.conf import settings
from channels.auth import AuthMiddlewareStack
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        print(scope)  # scope를 디버깅
        token = self.get_token_from_scope(scope)
        print(token)
        if token:
            user = await self.authenticate_user(token)
            scope['user'] = user
        # super().__call__ 대신 아래와 같이 수정
        return await self.inner(scope, receive, send)

    def get_token_from_scope(self, scope):
        query_string = scope.get('query_string', b'').decode()
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
        return token

    @database_sync_to_async
    def authenticate_user(self, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return User.objects.get(id=payload['user_id'])
        except jwt.ExpiredSignatureError:
            raise Exception('Token has expired')
        except jwt.DecodeError:
            raise Exception('Token is invalid')
        except User.DoesNotExist:
            raise Exception('User does not exist')