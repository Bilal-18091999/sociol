from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db.models import Q
import uuid
from django.urls import reverse # Import reverse for get_absolute_url

# Your existing UserDetails model
class UserDetails(AbstractUser):
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    bio = models.TextField(max_length=500, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def get_posts(self):
        return self.posts.filter(is_active=True)

    def get_friends(self):
        accepted = FriendRequest.objects.filter(
            Q(from_user=self) | Q(to_user=self),
            is_accepted=True
        )
        return [fr.to_user if fr.from_user == self else fr.from_user for fr in accepted]

    class Meta:
        verbose_name = 'User Details'
        verbose_name_plural = 'Users Details'

# Your existing PendingUser model
class PendingUser(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Your existing FriendRequest model
class FriendRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_requests', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        def __str__(self):
            return f"{self.from_user} -> {self.to_user}"

# Your existing Post model
class Post(models.Model):
    POST_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('poll', 'Poll'),
    ]
    user = models.ForeignKey(UserDetails, on_delete=models.CASCADE, related_name='posts')
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default='text')
    text_content = models.TextField(blank=True, null=True)
    caption = models.TextField(max_length=500, blank=True, null=True)
    image = models.ImageField(
        upload_to='post_images/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])]
    )
    video = models.FileField(
        upload_to='post_videos/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['mp4', 'avi', 'mov', 'wmv', 'flv'])]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
    def __str__(self):
        return f"{self.user.username} - {self.post_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    def get_content_preview(self):
        if self.post_type == 'text' and self.text_content:
            return self.text_content[:100] + "..." if len(self.text_content) > 100 else self.text_content
        elif self.post_type == 'image' and self.image:
            return f"Image: {self.image.name}"
        elif self.post_type == 'video' and self.video:
            return f"Video: {self.video.name}"
        return "No content"
    def is_liked_by_user(self, user):
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False
    def get_like_count(self):
        return self.likes.count()
    def get_comment_count(self):
        return self.comments.count()

# Your existing Like model
class Like(models.Model):
    user = models.ForeignKey(UserDetails, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"

# Your existing Comment model
class Comment(models.Model):
    user = models.ForeignKey(UserDetails, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}..."

# Your existing Bookmark model
class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

# Your existing Message model
# class Message(models.Model):
#     STATUS_SENT = 'sent'
#     STATUS_DELIVERED = 'delivered'
#     STATUS_READ = 'read'
#     MESSAGE_STATUS_CHOICES = [
#         (STATUS_SENT, 'Sent'),
#         (STATUS_DELIVERED, 'Delivered'),
#         (STATUS_READ, 'Read'),
#     ]
#     sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
#     receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
#     content = models.TextField()
#     timestamp = models.DateTimeField(auto_now_add=True)
#     is_read = models.BooleanField(default=False)
#     status = models.CharField(
#         max_length=10,
#         choices=MESSAGE_STATUS_CHOICES,
#         default=STATUS_SENT
#     )
#     class Meta:
#         ordering = ['timestamp']
#     def __str__(self):
#         return f"From {self.sender.username} to {self.receiver.username}: {self.content[:50]}"
#     def save(self, *args, **kwargs):
#         if self.is_read and self.status != self.STATUS_READ:
#             self.status = self.STATUS_READ
#         super().save(*args, **kwargs)

# NEW: Notification Model
