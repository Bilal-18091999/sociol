from django.db import models


from django.contrib.auth import get_user_model
from accounts.models import UserDetails

class FacebookAndInstagramConfiguration(models.Model):
  
    access_token = models.TextField()
    page_id = models.CharField(max_length=255)
    user_id = models.CharField(max_length=255)
    created_by = models.ForeignKey(UserDetails, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return self.page_id
    

class LinkedInConfiguration(models.Model):
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    access_token = models.TextField()
    user_urn = models.CharField(max_length=255)
    access_token = models.TextField(null=True,blank=True)
    expires_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(UserDetails, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return self.client_id
    