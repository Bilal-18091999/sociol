from django.db import models
from django.conf import settings
from django.utils import timezone

class Message(models.Model):
    # Message Status Choices
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_READ = 'read'
    MESSAGE_STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_READ, 'Read'),
    ]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False) # Keep this for explicit read status
    status = models.CharField( # New field for detailed status
        max_length=10,
        choices=MESSAGE_STATUS_CHOICES,
        default=STATUS_SENT
    )

    class Meta:
        ordering = ['timestamp'] # Order messages by time

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}: {self.content[:50]}"
    
    def save(self, *args, **kwargs):
        # If is_read is set to True, ensure status is 'read'
        if self.is_read and self.status != self.STATUS_READ:
            self.status = self.STATUS_READ
        super().save(*args, **kwargs)
