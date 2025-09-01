from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_view, name='chat_home'),
    path('<int:friend_id>/', views.chat_view, name='chat_with_friend'),
    path('api/messages/<int:friend_id>/', views.get_messages_api, name='get_messages_api'),
    path('api/messages/send/', views.send_message_api, name='send_message_api'),
    path('api/messages/send-file/', views.send_file_api, name='send_file_api'),
    path('api/messages/send-voice/', views.send_voice_api, name='send_voice_api'),  # New voice endpoint
    path('api/messages/delete/<int:message_id>/', views.delete_message_api, name='delete_message_api'),  # New delete endpoint
    path('api/status/update/', views.update_user_status_api, name='update_user_status_api'),
    path('api/friends/status/', views.get_friend_statuses_api, name='get_friend_statuses_api'),
    path('download/<int:message_id>/', views.download_file, name='download_file'),
    # path('media/<int:friend_id>/', views.media_view, name='media_view'),
    # path('documents/<int:friend_id>/', views.documents_view, name='documents_view'),
    # path('links/<int:friend_id>/', views.links_view, name='links_view'),
]
