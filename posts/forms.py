from django import forms
# Create your models here.
from posts.models import FacebookAndInstagramConfiguration, LinkedInConfiguration
from accounts.models import Post

class FacebookAndInstagramConfigurationForm(forms.ModelForm):
    class Meta:
        model = FacebookAndInstagramConfiguration
        fields = ['access_token', 'page_id', 'user_id']


class LinkedInConfigurationForm(forms.ModelForm):
    class Meta:
        model = LinkedInConfiguration
        fields = ['client_id', 'client_secret','user_urn']



class PostEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['post_type', 'text_content', 'caption', 'image', 'video']
        widgets = {
            'text_content': forms.Textarea(attrs={'rows': 4}),
            'caption': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
        self.fields['video'].required = False