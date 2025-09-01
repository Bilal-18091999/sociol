from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Max
from .models import Message
from django.contrib.auth import get_user_model
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from notifications.models import Notification
import datetime
import os
from django.core.files.storage import default_storage
from django.conf import settings
import mimetypes
from django.core.files.base import ContentFile
import base64

User = get_user_model()

@login_required
def chat_view(request, friend_id=None):
    """
    Renders the main chat page, displaying friends and the chat history with a selected friend.
    """
    user = request.user
    user.is_online = True
    user.last_seen = timezone.now()
    user.save()

    friends_data = []
    friends = user.get_friends()
    for friend in friends:
        # Get unread count (excluding deleted messages)
        unread_count = Message.objects.filter(
            sender=friend,
            receiver=user,
            is_read=False,
            deleted_for_receiver=False,
            deleted_for_everyone=False
        ).count()

        # Get the latest message timestamp between user and friend (excluding deleted messages)
        latest_message_agg = Message.objects.filter(
            Q(sender=user, receiver=friend, deleted_for_sender=False, deleted_for_everyone=False) |
            Q(sender=friend, receiver=user, deleted_for_receiver=False, deleted_for_everyone=False)
        ).aggregate(latest_timestamp=Max('timestamp'))
        
        latest_message_timestamp = latest_message_agg['latest_timestamp']

        if not latest_message_timestamp:
            latest_message_timestamp = timezone.make_aware(datetime.datetime(1970, 1, 1))

        friends_data.append({
            'user': friend,
            'unread_count': unread_count,
            'latest_message_timestamp': latest_message_timestamp
        })

    friends_data.sort(key=lambda x: x['latest_message_timestamp'], reverse=True)

    selected_friend = None
    messages = []
    if friend_id:
        try:
            selected_friend = User.objects.get(id=friend_id)
            if selected_friend not in user.get_friends():
                selected_friend = None
            else:
                # Get messages excluding deleted ones
                messages = Message.objects.filter(
                    Q(sender=user, receiver=selected_friend) |
                    Q(sender=selected_friend, receiver=user)
                ).exclude(
                    Q(sender=user, deleted_for_sender=True) |
                    Q(receiver=user, deleted_for_receiver=True) |
                    Q(deleted_for_everyone=True)
                ).order_by('timestamp')

                # Mark messages from selected friend as read
                Message.objects.filter(
                    sender=selected_friend, 
                    receiver=user, 
                    is_read=False,
                    deleted_for_receiver=False,
                    deleted_for_everyone=False
                ).update(is_read=True, status=Message.STATUS_READ)

                # Mark messages sent by user to selected friend as delivered
                Message.objects.filter(
                    sender=user,
                    receiver=selected_friend,
                    status=Message.STATUS_SENT
                ).update(status=Message.STATUS_DELIVERED)
        except User.DoesNotExist:
            selected_friend = None

    context = {
        'friends': friends_data,
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
        Message.objects.filter(
            sender=friend, 
            receiver=user, 
            is_read=False,
            deleted_for_receiver=False,
            deleted_for_everyone=False
        ).update(is_read=True, status=Message.STATUS_READ)

        # Mark messages sent by user to this friend as delivered
        Message.objects.filter(
            sender=user,
            receiver=friend,
            status=Message.STATUS_SENT
        ).update(status=Message.STATUS_DELIVERED)

        # Get messages excluding deleted ones
        messages = Message.objects.filter(
            Q(sender=user, receiver=friend) |
            Q(sender=friend, receiver=user)
        ).exclude(
            Q(sender=user, deleted_for_sender=True) |
            Q(receiver=user, deleted_for_receiver=True) |
            Q(deleted_for_everyone=True)
        ).order_by('timestamp')

        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'sender__id': msg.sender.id,
                'sender__username': msg.sender.username,
                'content': msg.content,
                'message_type': msg.message_type,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read,
                'status': msg.status,
                'deleted_for_everyone': msg.deleted_for_everyone,
            }

            # Add file information if it's a file message
            if msg.file_attachment:
                message_data.update({
                    'file_name': msg.file_name,
                    'file_size': msg.file_size,
                    'file_size_display': msg.get_file_size_display(),
                    'file_url': msg.file_attachment.url if msg.file_attachment else None,
                    'is_image': msg.is_image(),
                    'is_video': msg.is_video(),
                    'is_audio': msg.is_audio(),
                    'is_voice': msg.is_voice(),
                })

            messages_data.append(message_data)

        return JsonResponse(messages_data, safe=False)

    except User.DoesNotExist:
        return JsonResponse({'error': 'Friend not found'}, status=404)

@require_POST
@login_required
@csrf_protect
def send_message_api(request):
    """
    API endpoint to send a new text message.
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
            message_type=Message.MESSAGE_TYPE_TEXT,
            status=Message.STATUS_SENT
        )

        # Create a notification for the receiver
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
            'message_type': message.message_type,
            'timestamp': message.timestamp.isoformat(),
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
def send_file_api(request):
    """
    API endpoint to send a file message.
    """
    try:
        receiver_id = request.POST.get('receiver_id')
        file_obj = request.FILES.get('file')
        caption = request.POST.get('caption', '')

        if not receiver_id or not file_obj:
            return JsonResponse({'error': 'Receiver ID and file are required'}, status=400)

        receiver = User.objects.get(id=receiver_id)
        sender = request.user

        # Validate file size (max 50MB)
        max_file_size = 50 * 1024 * 1024  # 50MB
        if file_obj.size > max_file_size:
            return JsonResponse({'error': 'File size exceeds 50MB limit'}, status=400)

        # Determine message type based on file extension
        file_extension = os.path.splitext(file_obj.name)[1].lower()
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            message_type = Message.MESSAGE_TYPE_IMAGE
        elif file_extension in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']:
            message_type = Message.MESSAGE_TYPE_VIDEO
        elif file_extension in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']:
            message_type = Message.MESSAGE_TYPE_AUDIO
        else:
            message_type = Message.MESSAGE_TYPE_DOCUMENT

        message = Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=caption,
            message_type=message_type,
            file_attachment=file_obj,
            file_name=file_obj.name,
            file_size=file_obj.size,
            status=Message.STATUS_SENT
        )

        # Create a notification for the receiver
        file_type_display = message_type.capitalize()
        notification_content = f"{sender.username} sent you a {file_type_display.lower()}"
        if caption:
            notification_content += f": \"{caption[:30]}{'...' if len(caption) > 30 else ''}\""

        Notification.objects.create(
            user=receiver,
            sender=sender,
            notification_type='message',
            content=notification_content,
            related_object_id=message.id
        )

        return JsonResponse({
            'success': True,
            'message': 'File sent successfully',
            'id': message.id,
            'sender_id': message.sender.id,
            'receiver_id': message.receiver.id,
            'content': message.content,
            'message_type': message.message_type,
            'file_name': message.file_name,
            'file_size': message.file_size,
            'file_size_display': message.get_file_size_display(),
            'file_url': message.file_attachment.url,
            'is_image': message.is_image(),
            'is_video': message.is_video(),
            'is_audio': message.is_audio(),
            'is_voice': message.is_voice(),
            'timestamp': message.timestamp.isoformat(),
            'is_read': message.is_read,
            'status': message.status,
        }, status=201)

    except User.DoesNotExist:
        return JsonResponse({'error': 'Receiver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
@csrf_protect
def send_voice_api(request):
    """
    API endpoint to send a voice message.
    """
    try:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        audio_data = data.get('audio_data')
        duration = data.get('duration', 0)

        if not receiver_id or not audio_data:
            return JsonResponse({'error': 'Receiver ID and audio data are required'}, status=400)

        receiver = User.objects.get(id=receiver_id)
        sender = request.user

        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
        except:
            return JsonResponse({'error': 'Invalid audio data'}, status=400)

        # Create file name
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'voice_{sender.id}_{timestamp}.webm'

        # Create ContentFile
        audio_file = ContentFile(audio_bytes, name=filename)

        message = Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=f"Voice message ({duration}s)",
            message_type=Message.MESSAGE_TYPE_VOICE,
            file_attachment=audio_file,
            file_name=filename,
            file_size=len(audio_bytes),
            status=Message.STATUS_SENT
        )

        # Create a notification for the receiver
        Notification.objects.create(
            user=receiver,
            sender=sender,
            notification_type='message',
            content=f"{sender.username} sent you a voice message",
            related_object_id=message.id
        )

        return JsonResponse({
            'success': True,
            'message': 'Voice message sent successfully',
            'id': message.id,
            'sender_id': message.sender.id,
            'receiver_id': message.receiver.id,
            'content': message.content,
            'message_type': message.message_type,
            'file_name': message.file_name,
            'file_size': message.file_size,
            'file_size_display': message.get_file_size_display(),
            'file_url': message.file_attachment.url,
            'is_voice': True,
            'timestamp': message.timestamp.isoformat(),
            'is_read': message.is_read,
            'status': message.status,
        }, status=201)

    except User.DoesNotExist:
        return JsonResponse({'error': 'Receiver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
@csrf_protect
def delete_message_api(request, message_id):
    """
    API endpoint to delete a message.
    """
    try:
        data = json.loads(request.body)
        delete_type = data.get('delete_type')  # 'for_me' or 'for_everyone'

        message = get_object_or_404(Message, id=message_id)
        user = request.user

        # Check if user is sender or receiver
        if user != message.sender and user != message.receiver:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        if delete_type == 'for_everyone':
            # Only sender can delete for everyone, and only within 1 hour
            if user != message.sender:
                return JsonResponse({'error': 'Only sender can delete for everyone'}, status=403)
            
            time_limit = timezone.now() - timezone.timedelta(hours=1)
            if message.timestamp < time_limit:
                return JsonResponse({'error': 'Cannot delete for everyone after 1 hour'}, status=403)
            
            message.deleted_for_everyone = True
            message.deleted_at = timezone.now()
            message.content = "This message was deleted"
            
        elif delete_type == 'for_me':
            if user == message.sender:
                message.deleted_for_sender = True
            elif user == message.receiver:
                message.deleted_for_receiver = True
            message.deleted_at = timezone.now()

        message.save()

        return JsonResponse({
            'success': True,
            'message': 'Message deleted successfully',
            'delete_type': delete_type
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def download_file(request, message_id):
    """
    API endpoint to download a file from a message.
    """
    try:
        message = get_object_or_404(Message, id=message_id)

        # Check if user is sender or receiver
        if request.user != message.sender and request.user != message.receiver:
            raise Http404("File not found")

        # Check if message is deleted for this user
        if message.is_deleted_for_user(request.user):
            raise Http404("File not found")

        if not message.file_attachment:
            raise Http404("No file attached to this message")

        # Get the file path
        file_path = message.file_attachment.path
        if not os.path.exists(file_path):
            raise Http404("File not found on server")

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        # Create response
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{message.file_name}"'
            response['Content-Length'] = message.file_size
            return response

    except Exception as e:
        raise Http404("File not found")

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
            is_read=False,
            deleted_for_receiver=False,
            deleted_for_everyone=False
        ).count()

        friend_statuses.append({
            'id': friend.id,
            'is_online': friend.is_online,
            'last_seen': friend.last_seen.isoformat() if friend.last_seen else None,
            'unread_count': unread_count
        })

    return JsonResponse(friend_statuses, safe=False)

@login_required
def media_view(request, friend_id):
    """View to show media (images and videos) shared with a friend"""
    user = request.user
    try:
        friend = User.objects.get(id=friend_id)
        if friend not in user.get_friends():
            return render(request, 'chat/error.html', {'error': 'Not your friend'})

        # Get images and videos (excluding deleted messages)
        media_messages = Message.objects.filter(
            (Q(sender=user, receiver=friend) | Q(sender=friend, receiver=user)),
            message_type__in=[Message.MESSAGE_TYPE_IMAGE, Message.MESSAGE_TYPE_VIDEO]
        ).exclude(
            Q(sender=user, deleted_for_sender=True) |
            Q(receiver=user, deleted_for_receiver=True) |
            Q(deleted_for_everyone=True)
        ).order_by('-timestamp')

        context = {
            'friend': friend,
            'media_messages': media_messages,
        }
        return render(request, 'chat/media.html', context)

    except User.DoesNotExist:
        return render(request, 'chat/error.html', {'error': 'Friend not found'})

@login_required
def documents_view(request, friend_id):
    """View to show documents shared with a friend"""
    user = request.user
    try:
        friend = User.objects.get(id=friend_id)
        if friend not in user.get_friends():
            return render(request, 'chat/error.html', {'error': 'Not your friend'})

        # Get documents (excluding deleted messages)
        document_messages = Message.objects.filter(
            (Q(sender=user, receiver=friend) | Q(sender=friend, receiver=user)),
            message_type=Message.MESSAGE_TYPE_DOCUMENT
        ).exclude(
            Q(sender=user, deleted_for_sender=True) |
            Q(receiver=user, deleted_for_receiver=True) |
            Q(deleted_for_everyone=True)
        ).order_by('-timestamp')

        context = {
            'friend': friend,
            'document_messages': document_messages,
        }
        return render(request, 'chat/documents.html', context)

    except User.DoesNotExist:
        return render(request, 'chat/error.html', {'error': 'Friend not found'})

@login_required
def links_view(request, friend_id):
    """View to show links shared with a friend"""
    user = request.user
    try:
        friend = User.objects.get(id=friend_id)
        if friend not in user.get_friends():
            return render(request, 'chat/error.html', {'error': 'Not your friend'})

        # Get messages containing links (simple regex pattern, excluding deleted messages)
        import re
        link_pattern = re.compile(r'https?://\S+')
        all_messages = Message.objects.filter(
            (Q(sender=user, receiver=friend) | Q(sender=friend, receiver=user)),
            message_type=Message.MESSAGE_TYPE_TEXT
        ).exclude(
            Q(sender=user, deleted_for_sender=True) |
            Q(receiver=user, deleted_for_receiver=True) |
            Q(deleted_for_everyone=True)
        ).order_by('-timestamp')

        link_messages = []
        for msg in all_messages:
            if link_pattern.search(msg.content):
                # Extract links from message
                links = link_pattern.findall(msg.content)
                link_messages.append({
                    'message': msg,
                    'links': links
                })

        context = {
            'friend': friend,
            'link_messages': link_messages,
        }
        return render(request, 'chat/links.html', context)

    except User.DoesNotExist:
        return render(request, 'chat/error.html', {'error': 'Friend not found'})
