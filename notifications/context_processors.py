# accounts/context_processors.py
from notifications.models import Notification  # or wherever your Notification model is

def unread_notifications(request):
    if request.user.is_authenticated:
        return {
            'unread_count': Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
        }
    return {'unread_count': 0}