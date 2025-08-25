from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.views.decorators.http import require_POST
from accounts.forms import PostForm
from accounts.models import Post, Like, Comment, Bookmark
from notifications.models import Notification 

@login_required
def create_post(request):
    """View to handle post creation"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()

            # NEW: Notify friends about the new post
            friends = request.user.get_friends()
            for friend in friends:
                Notification.objects.create(
                    user=friend,
                    sender=request.user,
                    notification_type='new_post',
                    content=f"{request.user.username} posted a new {post.post_type}.",
                    related_object_id=post.id
                )
            messages.success(request, 'Post created successfully!')
            return redirect('posts:feed')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})

def feed_view(request):
    """Main feed view"""
    if request.user.is_authenticated:
        friends = request.user.get_friends()
        friend_ids = [friend.id for friend in friends]
        friend_ids.append(request.user.id)
        posts = Post.objects.filter(
            user_id__in=friend_ids,
            is_active=True
        ).select_related('user').prefetch_related('likes', 'comments', 'bookmarks')
    else:
        posts = Post.objects.filter(is_active=True).select_related('user').prefetch_related('likes', 'comments', 'bookmarks')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    for post in posts:
        post.user_has_liked = post.likes.filter(user=request.user).exists()
        post.user_has_bookmarked = post.bookmarks.filter(user=request.user).exists()
    return render(request, 'feed.html', {'posts': posts})


from django.core.paginator import Paginator
from django.shortcuts import render

def your_feed(request):
    """Main feed view - only user's own posts"""
    if request.user.is_authenticated:
        posts = Post.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('user').prefetch_related('likes', 'comments', 'bookmarks')
    else:
        # If not logged in, probably no posts should be shown or handle accordingly
        posts = Post.objects.none()
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    for post in posts:
        post.user_has_liked = post.likes.filter(user=request.user).exists()
        post.user_has_bookmarked = post.bookmarks.filter(user=request.user).exists()
    
    return render(request, 'your_feed.html', {'posts': posts})

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    print("Deleting post with ID:", post_id)
    if request.method == 'GET':
        post.delete()
        messages.success(request, "Post deleted successfully.")
        print("Post deleted successfully:", post_id)
    else:
        messages.error(request, "Invalid request method.")
    
    return redirect('posts:your_feed')  # Always redirect

from posts.forms import PostEditForm
@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    
    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect('posts:your_feed')
    else:
        form = PostEditForm(instance=post)
    
        return render(request, 'posts/edit_post.html', {'form': form, 'post': post})


# @login_required
# @require_POST
# def toggle_like(request, post_id):
#     """Toggle like/unlike for a post"""
#     try:
#         post = get_object_or_404(Post, id=post_id)
#         like, created = Like.objects.get_or_create(user=request.user, post=post)
#         if not created:
#             like.delete()
#             liked = False
#         else:
#             liked = True
#         return JsonResponse({
#             'success': True,
#             'liked': liked,
#             'like_count': post.get_like_count()
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=400)
@login_required
@require_POST
def toggle_like(request, post_id):
    """Toggle like/unlike for a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

            # ✅ Create notification when liked (but NOT for your own post)
            if post.user != request.user:
                Notification.objects.create(
                    user=post.user,
                    sender=request.user,
                    notification_type='like',
                    content=f"{request.user.username} liked your post.",
                    related_object_id=post.id
                )

        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.get_like_count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# @login_required
# @require_POST
# def add_comment(request, post_id):
#     """Add a comment to a post"""
#     try:
#         post = get_object_or_404(Post, id=post_id)
#         data = json.loads(request.body)
#         content = data.get('content', '').strip()
#         if not content:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'Comment content cannot be empty'
#             }, status=400)
#         comment = Comment.objects.create(
#             user=request.user,
#             post=post,
#             content=content
#         )
#         return JsonResponse({
#             'success': True,
#             'comment': {
#                 'id': comment.id,
#                 'content': comment.content,
#                 'user': {
#                     'username': comment.user.username,
#                     'profile_photo': comment.user.profile_photo.url if comment.user.profile_photo else None
#                 },
#                 'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#                 'time_ago': 'just now'
#             },
#             'comment_count': post.get_comment_count()
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=400)
@login_required
@require_POST
def add_comment(request, post_id):
    """Add a comment to a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Comment content cannot be empty'
            }, status=400)

        comment = Comment.objects.create(
            user=request.user,
            post=post,
            content=content
        )

        # ✅ Create notification when commented (but NOT for your own post)
        if post.user != request.user:
            Notification.objects.create(
                user=post.user,
                sender=request.user,
                notification_type='comment',
                content=f"{request.user.username} commented on your post.",
                related_object_id=post.id
            )

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': {
                    'username': comment.user.username,
                    'profile_photo': comment.user.profile_photo.url if comment.user.profile_photo else None
                },
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': 'just now'
            },
            'comment_count': post.get_comment_count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_comments(request, post_id):
    """Get all comments for a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        comments = post.comments.select_related('user').order_by('created_at')
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'user': {
                    'username': comment.user.username,
                    'profile_photo': comment.user.profile_photo.url if comment.user.profile_photo else None
                },
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
            })
        return JsonResponse({
            'success': True,
            'comments': comments_data,
            'comment_count': len(comments_data)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def get_likers(request, post_id):
    """Get users who liked a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        likes = post.likes.select_related('user').order_by('-created_at')
        likers_data = []
        for like in likes:
            likers_data.append({
                'username': like.user.username,
                'profile_photo': like.user.profile_photo.url if like.user.profile_photo else None
            })
        return JsonResponse({
            'success': True,
            'likers': likers_data,
            'like_count': post.get_like_count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@require_POST
def toggle_bookmark(request, post_id):
    """Toggle bookmark/unbookmark for a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True
        return JsonResponse({
            'success': True,
            'bookmarked': bookmarked,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def saved_posts_view(request):
    """View to display all bookmarked posts for the current user"""
    bookmarked_posts = Post.objects.filter(bookmarks__user=request.user).order_by('-bookmarks__created_at')
    paginator = Paginator(bookmarked_posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    for post in posts:
        post.user_has_liked = post.likes.filter(user=request.user).exists()
        post.user_has_bookmarked = post.bookmarks.filter(user=request.user).exists()
    return render(request, 'saved_posts.html', {'posts': posts})


from posts.forms import FacebookAndInstagramConfigurationForm, LinkedInConfigurationForm
from posts.models import FacebookAndInstagramConfiguration, LinkedInConfiguration
def facebook_instagram_config(request):
    post = FacebookAndInstagramConfiguration.objects.filter(created_by=request.user).last()
    print("qqqqqqqqqqqqqqqq",post)

    if request.method == 'POST':
        print("Received facebook Data```````````````:", request.POST)
        facebook_instagram_form = FacebookAndInstagramConfigurationForm(request.POST,instance=post)

        if facebook_instagram_form.is_valid() :
          
            facebookInstagram = facebook_instagram_form.save(commit=False)
            facebookInstagram.created_by=request.user
            facebookInstagram.save()

            return redirect('posts:feed')  # Redirect to login page

    else:
      
        facebook_instagram_form = FacebookAndInstagramConfigurationForm(instance=post)

    return render(request, 'posts/facebook_form.html', {
        'facebook_form': facebook_instagram_form, 
    })

def linkedin_config(request):
    post = LinkedInConfiguration.objects.filter(created_by=request.user).last()
    if request.method == 'POST':
        print("Received linkedin Data```````````````:", request.POST)
        linkedin_form = LinkedInConfigurationForm(request.POST,instance=post)

        if linkedin_form.is_valid() :
          
            linkedin = linkedin_form.save(commit=False)
            linkedin.created_by = request.user
            linkedin.save()

            return redirect('posts:feed')  # Redirect to login page

    else:
      
        linkedin_form = LinkedInConfigurationForm(instance=post)

    return render(request, 'posts/linkedin_form.html', {
        'linkedin_form': linkedin_form, 
    })



from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
import requests

def post_to_facebook(request, post_id):
    try:
        # Get the post and user
        post = get_object_or_404(Post, id=post_id, is_active=True)
        user = request.user
        
        # Get Facebook configuration for this user
        fb_config = get_object_or_404(FacebookAndInstagramConfiguration, created_by=user)
        
        # Prepare the API endpoint
        page_id = fb_config.page_id
        access_token = fb_config.access_token
        api_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        
        # Handle different post types
        if post.post_type == 'text':
            payload = {
                'message': post.text_content,
                'access_token': access_token
            }
            response = requests.post(api_url, data=payload)
            print("Text Post Response:", response.json())
            
        elif post.post_type == 'image' and post.image:
            upload_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            files = {'source': post.image.file}
            data = {
                'message': post.caption if post.caption else '',
                'access_token': access_token
            }
            response = requests.post(upload_url, files=files, data=data)
            
        elif post.post_type == 'video' and post.video:
            upload_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
            files = {'source': post.video.file}
            data = {
                'description': post.caption if post.caption else '',
                'access_token': access_token
            }
            response = requests.post(upload_url, files=files, data=data)
            
        else:
            messages.error(request, 'Unsupported post type or missing media')
            return redirect('some_view_name')  # Redirect to appropriate view
        
        if response.status_code == 200:
            messages.success(request, 'Post shared to Facebook successfully!')
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            messages.error(request, f'Facebook error: {error_msg}')
            
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('posts:your_feed')  # Redirect back to where you came from

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

import time


def wait_for_video_ready(media_id, access_token, timeout=180):
    """
    Poll Instagram Graph API until the video media container status is FINISHED or timeout reached.
    Checks every 2 seconds up to 'timeout' seconds.
    """
    status_url = f"https://graph.facebook.com/v19.0/{media_id}"
    for _ in range(timeout // 2):
        response = requests.get(status_url, params={
            "fields": "status_code",
            "access_token": access_token
        })
        data = response.json()
        print("Media Status Check:", data)

        if data.get("status_code") == "FINISHED":
            return True
        time.sleep(2)
    return False

def post_to_instagram(request, post_id):
    try:
        post = get_object_or_404(Post, id=post_id, is_active=True)
        user = request.user
        config = get_object_or_404(FacebookAndInstagramConfiguration, created_by=user)
        
        access_token = config.access_token
        ig_user_id = config.user_id  # Instagram Business User ID

        if post.post_type == 'text':
            messages.error(request, "Instagram does not support text-only posts.")
            return redirect('posts:your_feed')

        # Domain for public URLs
        domain = "https://sociov1.pythonanywhere.com"

        # Construct full media URL
        media_url = ""
        if post.post_type == 'image' and post.image:
            media_path = post.image.url
            media_url = f"{domain}{media_path}"
            print("Image URL:", media_url)
        elif post.post_type == 'video' and post.video:
            media_path = post.video.url
            media_url = f"{domain}{media_path}"
            print("Video URL:", media_url)
        else:
            messages.error(request, "Missing media file.")
            return redirect('posts:your_feed')

        # Step 1: Create media container
        media_api_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
        data = {
            "caption": post.caption or "",
            "access_token": access_token
        }

        if post.post_type == 'image':
            data["image_url"] = media_url

        elif post.post_type == 'video':
            data["video_url"] = media_url
            data["media_type"] = "REELS"  # Use REELS for videos

        media_response = requests.post(media_api_url, data=data)
        media_json = media_response.json()
        print("Media Response:", media_json)

        if 'id' not in media_json:
            error_msg = media_json.get('error', {}).get('message', 'Failed to create Instagram media container.')
            messages.error(request, f"Instagram error: {error_msg}")
            return redirect('posts:your_feed')

        creation_id = media_json['id']

        # For videos, wait until media is ready before publishing
        if post.post_type == 'video':
            is_ready = wait_for_video_ready(creation_id, access_token)
            if not is_ready:
                messages.error(request, "Instagram video not ready to publish. Please try again later.")
                return redirect('posts:your_feed')

        # Step 2: Publish media
        publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
        publish_response = requests.post(publish_url, data={
            "creation_id": creation_id,
            "access_token": access_token
        })
        publish_json = publish_response.json()
        print("Publish Response:", publish_json)

        if 'id' in publish_json:
            messages.success(request, "Post published to Instagram successfully!")
        else:
            error_msg = publish_json.get('error', {}).get('message', 'Failed to publish to Instagram.')
            messages.error(request, f"Instagram error: {error_msg}")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")


    return redirect('posts:your_feed')
import requests
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.utils.timezone import now
import datetime
import requests
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.utils.timezone import now
import datetime

# Step 1: Redirect to LinkedIn's OAuth
def linkedin_login(request, post_id):
    # Get the post and user
    post = get_object_or_404(Post, id=post_id, is_active=True)
    user = request.user
    request.session["post_id"] = post_id

    # Get LinkedIn configuration for this user
    linkedin_config = get_object_or_404(LinkedInConfiguration, created_by=user)
    
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={linkedin_config.client_id}"
        f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
        f"&scope=w_member_social%20openid%20profile"
    )
    
    return redirect(auth_url)

# Step 2: Callback to get token
def linkedin_callback(request):
    code = request.GET.get('code')
    post_id = request.session.get("post_id")
    
    if not post_id:
        messages.error(request, "Post ID not found in session")
        return redirect('posts:your_feed')
        
    post_obj = get_object_or_404(Post, id=post_id)
    
    # FIXED: Use post_obj.user instead of post_obj.created_by
    linkedin_config = LinkedInConfiguration.objects.filter(created_by=post_obj.user).last()

    if not code:
        messages.error(request, "No code returned from LinkedIn")
        return redirect('posts:your_feed')

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
        'client_id': linkedin_config.client_id,
        'client_secret': linkedin_config.client_secret,
    }
    
    try:
        r = requests.post(token_url, data=payload)
        token_data = r.json()
        
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 5184000)  # Default to 60 days
        
        if not access_token:
            messages.error(request, "Failed to get LinkedIn access token")
            return redirect('posts:your_feed')

        # Save token in DB with expiry
        expiry_time = now() + datetime.timedelta(seconds=expires_in)
        LinkedInConfiguration.objects.update_or_create(
            created_by=post_obj.user,  # FIXED: Use post_obj.user
            defaults={
                'access_token': access_token,
                'expires_at': expiry_time
            }
        )
        
        print("LinkedIn access token saved:", access_token)
        messages.success(request, "LinkedIn connected successfully!")
        
        # Proceed to post
        return post_to_linkedin(request, post_id, access_token)
        
    except Exception as e:
        messages.error(request, f"Error during LinkedIn authentication: {str(e)}")
        return redirect('posts:your_feed')

def post_to_linkedin(request, post_id, access_token=None):
    try:
        print("Post to LinkedIn called with post_id:", post_id)
        post = get_object_or_404(Post, id=post_id, is_active=True)
        
        # FIXED: Use post.user instead of post.created_by
        user = post.user

        # If access_token is not provided, get it from the database
        if not access_token:
            linkedin_config = get_object_or_404(LinkedInConfiguration, created_by=user)
            access_token = linkedin_config.access_token
            person_urn = linkedin_config.user_urn
        else:
            # FIXED: Get linkedin_config even when access_token is provided
            linkedin_config = get_object_or_404(LinkedInConfiguration, created_by=user)
            person_urn = linkedin_config.user_urn

        headers = {
            "Authorization": f"Bearer {access_token}", 
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # TEXT ONLY POST
        if post.post_type == "text":
            print("Processing text post for LinkedIn")
            data = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post.text_content},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            r = requests.post("https://api.linkedin.com/v2/ugcPosts", json=data, headers=headers)

        # IMAGE POST
        elif post.post_type == "image" and post.image:
            print("Processing image post for LinkedIn")
            # 1. Register Upload
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": f"urn:li:person:{person_urn}",
                    "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                }
            }
            
            reg_res = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                json=register_data, 
                headers=headers
            ).json()
            
            if "value" not in reg_res:
                messages.error(request, "Failed to register image upload")
                return redirect('posts:your_feed')
                
            upload_url = reg_res["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = reg_res["value"]["asset"]
            print("Asset ID for image:", asset_id)
            
            # 2. Upload Image
            image_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "image/jpeg"}
            with post.image.open('rb') as img_file:
                upload_response = requests.put(upload_url, headers=image_headers, data=img_file)
                
            if upload_response.status_code != 201:
                messages.error(request, "Failed to upload image to LinkedIn")
                return redirect('posts:your_feed')

            # 3. Create Post
            post_data = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post.caption or ""},
                        "shareMediaCategory": "IMAGE",
                        "media": [{
                            "status": "READY",
                            "description": {"text": post.caption or ""},
                            "media": asset_id,
                            "title": {"text": "Image Post"}
                        }]
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            r = requests.post("https://api.linkedin.com/v2/ugcPosts", json=post_data, headers=headers)

        # VIDEO POST
        elif post.post_type == "video" and post.video:
            print("Processing video post for LinkedIn")
            # 1. Register Upload
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                    "owner": f"urn:li:person:{person_urn}",
                    "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                }
            }
            
            reg_res = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                json=register_data, 
                headers=headers
            ).json()
            
            if "value" not in reg_res:
                messages.error(request, "Failed to register video upload")
                return redirect('posts:your_feed')
                
            upload_url = reg_res["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = reg_res["value"]["asset"]
            print("Asset ID for video:", asset_id)
            
            # 2. Upload Video
            video_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
            with post.video.open('rb') as video_file:
                upload_response = requests.put(upload_url, headers=video_headers, data=video_file)
                
            if upload_response.status_code != 201:
                messages.error(request, "Failed to upload video to LinkedIn")
                return redirect('posts:your_feed')

            # 3. Create Post
            post_data = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post.caption or ""},
                        "shareMediaCategory": "VIDEO",
                        "media": [{
                            "status": "READY",
                            "description": {"text": post.caption or ""},
                            "media": asset_id,
                            "title": {"text": "Video Post"}
                        }]
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            r = requests.post("https://api.linkedin.com/v2/ugcPosts", json=post_data, headers=headers)

        else:
            messages.error(request, "Unsupported post type or missing media")
            return redirect('posts:your_feed')

        print("LinkedIn post response status:", r.status_code)
        print("LinkedIn post response:", r.json())


    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        print("Exception in post_to_linkedin:", str(e))
    
    return redirect('posts:your_feed')