# socio/asgi.py
import os

# Set the Django settings module BEFORE importing any Django components
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socio.settings')

# Now import Django and Channels components
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

# Get the default Django ASGI app
django_asgi_app = get_asgi_application() # This call initializes Django's app registry

# Define the full ASGI application with routing for both HTTP and WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app, # This handles traditional HTTP requests
    "websocket": AuthMiddlewareStack( # This handles WebSocket requests
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})