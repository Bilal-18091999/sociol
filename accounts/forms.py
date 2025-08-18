from django import forms
from .models import UserDetails

class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = UserDetails
        fields = ['username', 'first_name', 'last_name', 'bio', 'website', 'location', 'profile_photo']
        widgets = {
            'profile_photo': forms.FileInput(),
        }
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['post_type', 'text_content', 'image', 'video', 'caption']
        widgets = {
            'text_content': forms.Textarea(attrs={
                'placeholder': "What's on your mind?",
                'rows': 5,
                'class': 'form-control'
            }),
            'caption': forms.TextInput(attrs={
                'placeholder': 'Add a caption...',
                'class': 'form-control'
            }),
            'post_type': forms.HiddenInput(),
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            }),
            'video': forms.FileInput(attrs={
                'accept': 'video/*',
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        post_type = cleaned_data.get('post_type')
        text_content = cleaned_data.get('text_content')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')
        
        # Validation based on post type
        if post_type == 'text' and not text_content:
            raise forms.ValidationError("Text content is required for text posts.")
        elif post_type == 'image' and not image:
            raise forms.ValidationError("Image is required for image posts.")
        elif post_type == 'video' and not video:
            raise forms.ValidationError("Video is required for video posts.")
        
        # Ensure only one media type is uploaded
        if image and video:
            raise forms.ValidationError("Please upload either an image or video, not both.")
        
        return cleaned_data