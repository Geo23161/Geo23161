"""
ASGI config for perfectlov project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perfectlov.settings')

django.setup()


from app import routing
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http" : get_asgi_application(),
    "websocket" : JWTAuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    )
})
