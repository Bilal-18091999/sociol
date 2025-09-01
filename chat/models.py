from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import UserDetails
from django.conf import settings
import os

User = get_user_model()

def user_directory_path(instance, filename):
    """File will be uploaded to MEDIA_ROOT/chat_files/user_<id>/<filename>"""
    return f'chat_files/user_{instance.sender.id}/{filename}'

class Message(models.Model):
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_READ = 'read'
    
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_READ, 'Read'),
    ]

    MESSAGE_TYPE_TEXT = 'text'
    MESSAGE_TYPE_IMAGE = 'image'
    MESSAGE_TYPE_VIDEO = 'video'
    MESSAGE_TYPE_DOCUMENT = 'document'
    MESSAGE_TYPE_AUDIO = 'audio'
    MESSAGE_TYPE_VOICE = 'voice'  # New voice message type
    
    MESSAGE_TYPE_CHOICES = [
        (MESSAGE_TYPE_TEXT, 'Text'),
        (MESSAGE_TYPE_IMAGE, 'Image'),
        (MESSAGE_TYPE_VIDEO, 'Video'),
        (MESSAGE_TYPE_DOCUMENT, 'Document'),
        (MESSAGE_TYPE_AUDIO, 'Audio'),
        (MESSAGE_TYPE_VOICE, 'Voice'),  # New voice message type
    ]

    sender = models.ForeignKey(UserDetails, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(UserDetails, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default=MESSAGE_TYPE_TEXT)
    file_attachment = models.FileField(upload_to=user_directory_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SENT)
    
    # New deletion fields
    deleted_for_sender = models.BooleanField(default=False)
    deleted_for_receiver = models.BooleanField(default=False)
    deleted_for_everyone = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        if self.message_type == self.MESSAGE_TYPE_TEXT:
            return f"{self.sender.username} to {self.receiver.username}: {self.content[:50]}"
        else:
            return f"{self.sender.username} to {self.receiver.username}: [{self.message_type.upper()}] {self.file_name}"

    def get_file_extension(self):
        if self.file_attachment:
            return os.path.splitext(self.file_attachment.name)[1].lower()
        return ''

    def is_image(self):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.get_file_extension() in image_extensions

    def is_video(self):
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']
        return self.get_file_extension() in video_extensions

    def is_audio(self):
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
        return self.get_file_extension() in audio_extensions

    def is_voice(self):
        return self.message_type == self.MESSAGE_TYPE_VOICE

    def get_file_size_display(self):
        if not self.file_size:
            return ''
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"

    def is_deleted_for_user(self, user):
        """Check if message is deleted for a specific user"""
        if self.deleted_for_everyone:
            return True
        if user == self.sender and self.deleted_for_sender:
            return True
        if user == self.receiver and self.deleted_for_receiver:
            return True
        return False
