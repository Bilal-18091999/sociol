# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import Notification, FriendRequest, Message, Like, Comment

@receiver(post_save, sender=FriendRequest)
def create_friend_request_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.to_user,
            sender=instance.from_user,
            notification_type='friend_request',
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )
    elif instance.is_accepted:
        # Notification to the requester that their request was accepted
        Notification.objects.create(
            recipient=instance.from_user,
            sender=instance.to_user,
            notification_type='friend_request_accepted',
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.receiver,
            sender=instance.sender,
            notification_type='message',
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created and instance.user != instance.post.user:  # Don't notify if user likes their own post
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='like',
            content_type=ContentType.objects.get_for_model(instance.post),
            object_id=instance.post.id
        )

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created and instance.user != instance.post.user:  # Don't notify if user comments on their own post
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='comment',
            content_type=ContentType.objects.get_for_model(instance.post),
            object_id=instance.post.id
        )