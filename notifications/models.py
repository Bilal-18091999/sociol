from django.db import models

# Create your models here.
# models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import UserDetails
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Request Accepted'),
        ('new_post', 'New Post'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_notifications', on_delete=models.SET_NULL, null=True, blank=True) # User who triggered the notification
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    content = models.TextField() # e.g., "John sent you a friend request", "Alice posted a new photo"
    related_object_id = models.PositiveIntegerField(null=True, blank=True) # ID of the related object (e.g., FriendRequest ID, Post ID, Message ID)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Newest notifications first

    def __str__(self):
        return f"Notification for {self.user.username}: {self.content[:50]}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()

    @property
    def get_absolute_url(self):
        # This can be used to link to the related object (e.g., chat, profile, post)
        if self.notification_type == 'message' and self.sender:
            return reverse('chat_view', args=[self.sender.id])
        elif self.notification_type == 'friend_request' and self.sender:
            return reverse('friends') + '?tab=requests' # Link to friend requests tab
        elif self.notification_type == 'friend_accepted' and self.sender:
            # Assuming you have a profile view that can take a user ID
            return reverse('profile_view') # Link to profile, user can see friends there
        elif self.notification_type == 'new_post' and self.related_object_id:
            # Assuming you have a post_detail view that takes a post ID
            # You might need to adjust 'posts:post_detail' based on your actual app_name and URL name
            return reverse('posts:feed') # Link to feed for now, or a specific post detail if available
        return '#' # Default fallback
