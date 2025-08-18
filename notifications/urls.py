# urls.py
from django.urls import path
from . import views
app_name = 'notifications'  # Namespace for your notifications app URLs
urlpatterns = [
   
    # NEW: Notification URLs
    path('', views.notifications_view, name='notifications_view'),
    path('mark-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('mark-all-read/', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
]