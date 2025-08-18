

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification
from django.contrib.auth import get_user_model

from django.contrib.auth.decorators import login_required
@login_required
def notifications_view(request):
    user = request.user
    filter_type = request.GET.get('filter', 'all')  # 'all' or 'unread'

    notifications = Notification.objects.filter(user=user).order_by('-created_at')

    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)

    context = {
        'notifications': notifications,
        'filter_type': filter_type,
        'unread_count': Notification.objects.filter(user=user, is_read=False).count()
    }
    return render(request, 'notifications/notifications.html', context)


# NEW: API to mark a single notification as read
@login_required
@require_POST
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# NEW: API to mark all notifications as read
@login_required
@require_POST
def mark_all_notifications_as_read(request):
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
