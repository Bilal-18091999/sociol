from django.urls import path
from . import views

app_name = 'chat' # Namespace for your chat app URLs
urlpatterns = [
    path('', views.chat_view, name='chat_home'), # Base URL for chat, no friend selected
    path('<int:friend_id>/', views.chat_view, name='chat_with_friend'), # URL for chat with a specific friend
    path('api/messages/<int:friend_id>/', views.get_messages_api, name='get_messages_api'), # API to get messages
    path('api/messages/send/', views.send_message_api, name='send_message_api'), # API to send messages
    path('api/status/update/', views.update_user_status_api, name='update_user_status_api'), # New API to update user's own status
    path('api/friends/status/', views.get_friend_statuses_api, name='get_friend_statuses_api'), # New API to get friend statuses and unread counts
]
