from django.urls import re_path
from . import consumers
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import ProtocolTypeRouter, URLRouter
from .middleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
        'websocket': AllowedHostsOriginValidator(
            TokenAuthMiddleware(
                URLRouter(
                    [
                        re_path(r'ws/chat/(?P<room_name>[0-9A-Za-z\- ]+)/$', consumers.ChatConsumer.as_asgi()),
                    ]
                )
            )
        )
    })