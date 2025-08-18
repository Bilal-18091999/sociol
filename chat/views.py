from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Max # Import Max for aggregation
from .models import Message
from django.contrib.auth import get_user_model
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from notifications.models import Notification # Import Notification
import datetime # Import datetime for default timestamp

User = get_user_model()

@login_required
def chat_view(request, friend_id=None):
    """
    Renders the main chat page, displaying friends and the chat history
    with a selected friend.
    """
    user = request.user
    user.is_online = True
    user.last_seen = timezone.now()
    user.save()

    friends_data = []
    friends = user.get_friends() # Assuming this returns a QuerySet of User objects

    for friend in friends:
        # Get unread count
        unread_count = Message.objects.filter(
            sender=friend,
            receiver=user,
            is_read=False
        ).count()

        # Get the latest message timestamp between user and friend
        # Use aggregate to get the maximum timestamp
        latest_message_agg = Message.objects.filter(
            Q(sender=user, receiver=friend) | Q(sender=friend, receiver=user)
        ).aggregate(latest_timestamp=Max('timestamp'))

        latest_message_timestamp = latest_message_agg['latest_timestamp']

        # If no messages exist, default to a very old timestamp to put them at the bottom
        if not latest_message_timestamp:
            latest_message_timestamp = timezone.make_aware(datetime.datetime(1970, 1, 1))

        friends_data.append({
            'user': friend,
            'unread_count': unread_count,
            'latest_message_timestamp': latest_message_timestamp
        })

    # Sort friends by latest message timestamp in descending order
    friends_data.sort(key=lambda x: x['latest_message_timestamp'], reverse=True)

    selected_friend = None
    messages = []
    if friend_id:
        try:
            selected_friend = User.objects.get(id=friend_id)
            if selected_friend not in user.get_friends():
                selected_friend = None
            else:
                messages = Message.objects.filter(
                    Q(sender=user, receiver=selected_friend) |
                    Q(sender=selected_friend, receiver=user)
                ).order_by('timestamp')
                # Mark messages from selected friend as read
                Message.objects.filter(sender=selected_friend, receiver=user, is_read=False).update(is_read=True, status=Message.STATUS_READ)
                # Mark messages sent by user to selected friend as delivered
                Message.objects.filter(
                    sender=user,
                    receiver=selected_friend,
                    status=Message.STATUS_SENT
                ).update(status=Message.STATUS_DELIVERED)
        except User.DoesNotExist:
            selected_friend = None

    context = {
        'friends': friends_data, # Use the sorted list
        'selected_friend': selected_friend,
        'messages': messages,
    }
    return render(request, 'chat/chat_page.html', context)

@login_required
def get_messages_api(request, friend_id):
    """
    API endpoint to fetch message history for a specific friend.
    """
    user = request.user
    try:
        friend = User.objects.get(id=friend_id)
        if friend not in user.get_friends():
            return JsonResponse({'error': 'Not your friend'}, status=403)
        
        # Mark messages from this friend as read
        Message.objects.filter(sender=friend, receiver=user, is_read=False).update(is_read=True, status=Message.STATUS_READ)
        # Mark messages sent by user to this friend as delivered
        Message.objects.filter(
            sender=user,
            receiver=friend,
            status=Message.STATUS_SENT
        ).update(status=Message.STATUS_DELIVERED)

        messages = Message.objects.filter(
            Q(sender=user, receiver=friend) |
            Q(sender=friend, receiver=user)
        ).order_by('timestamp').values('sender__id', 'sender__username', 'content', 'timestamp', 'is_read', 'status')
        
        # Ensure timestamps are in ISO format for consistent JS parsing
        for msg in messages:
            msg['timestamp'] = msg['timestamp'].isoformat()

        return JsonResponse(list(messages), safe=False)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Friend not found'}, status=404)

@require_POST
@login_required
@csrf_protect
def send_message_api(request):
    """
    API endpoint to send a new message.
    """
    try:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        content = data.get('content')
        if not receiver_id or not content:
            return JsonResponse({'error': 'Receiver ID and content are required'}, status=400)
        receiver = User.objects.get(id=receiver_id)
        sender = request.user
        message = Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=content,
            status=Message.STATUS_SENT
        )
        # NEW: Create a notification for the receiver
        Notification.objects.create(
            user=receiver,
            sender=sender,
            notification_type='message',
            content=f"{sender.username} sent you a message: \"{content[:50]}{'...' if len(content) > 50 else ''}\"",
            related_object_id=message.id
        )
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully',
            'id': message.id,
            'sender_id': message.sender.id,
            'receiver_id': message.receiver.id,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(), # Ensure ISO format
            'is_read': message.is_read,
            'status': message.status,
        }, status=201)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Receiver not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
@csrf_protect
def update_user_status_api(request):
    """
    API endpoint to update the current user's online status and last seen timestamp.
    """
    user = request.user
    user.is_online = True
    user.last_seen = timezone.now()
    user.save()
    return JsonResponse({'status': 'online', 'last_seen': user.last_seen.isoformat()})

@login_required
def get_friend_statuses_api(request):
    """
    API endpoint to fetch online status, last seen, and unread message counts for all friends.
    """
    user = request.user
    friend_statuses = []
    for friend in user.get_friends():
        unread_count = Message.objects.filter(
            sender=friend,
            receiver=user,
            is_read=False
        ).count()
        friend_statuses.append({
            'id': friend.id,
            'is_online': friend.is_online,
            'last_seen': friend.last_seen.isoformat() if friend.last_seen else None,
            'unread_count': unread_count
        })
    return JsonResponse(friend_statuses, safe=False)
