from django.urls import re_path

from app.consumers import LovConsumer

websocket_urlpatterns = [
    re_path('chat/', LovConsumer.as_asgi())
]