from django.urls import path
from . import views, consumer

urlpatterns = [
    path("device/initialize", views.device_initialize),
    path("device/websocket_token", views.device_websocket_token),
]

websocket_urlpatterns = [
    path("device/ws", consumer.DeviceConsumer.as_asgi()),
]