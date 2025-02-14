from django.urls import re_path
from .consumers import SpotifyConsumer

websocket_urlpatterns = [
    re_path(r"ws/spotify/(?P<username>\w+)/$", SpotifyConsumer.as_asgi())
]