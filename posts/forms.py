from django import forms
# Create your models here.
from posts.models import FacebookAndInstagramConfiguration, LinkedInConfiguration

class FacebookAndInstagramConfigurationForm(forms.ModelForm):
    class Meta:
        model = FacebookAndInstagramConfiguration
        fields = ['access_token', 'page_id', 'user_id']


class LinkedInConfigurationForm(forms.ModelForm):
    class Meta:
        model = LinkedInConfiguration
        fields = ['client_id', 'client_secret','user_urn']