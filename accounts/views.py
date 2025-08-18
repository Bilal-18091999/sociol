from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.contrib.auth import authenticate, login,logout,get_user_model
from django.db import IntegrityError
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .models import UserDetails, FriendRequest, PendingUser # Import Notification
from .forms import UserDetailsForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST # For API views
from django.http import JsonResponse

from notifications.models import Notification  # Import Notification model
def auth_page(request):
    return render(request, 'accounts/auth.html')

def signup(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        if UserDetails.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
        elif PendingUser.objects.filter(email=email).exists():
            messages.warning(request, 'Confirmation link already sent to your email.')
        else:
            pending_user = PendingUser.objects.create(email=email, password=password)
            confirmation_url = request.build_absolute_uri(
                reverse('confirm_email', kwargs={'token': str(pending_user.token)})
            )
            send_mail(
                subject='Confirm your Socio account',
                message=f'Click the link to confirm your email and activate your account: {confirmation_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            messages.success(request, 'Confirmation email sent! Please check your inbox.')
    return redirect('auth_page')

def signin(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        try:
            user = UserDetails.objects.get(email=email)
        except UserDetails.DoesNotExist:
            messages.error(request, 'Invalid email or password!')
            return redirect('auth_page')
        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            login(request, user)
            return redirect('posts:feed')
        else:
            messages.error(request, 'Invalid email or password!')
            return render(request, 'accounts/auth.html')
    return redirect('auth_page')

def confirm_email(request, token):
    try:
        pending_user = PendingUser.objects.get(token=token)
        if UserDetails.objects.filter(email=pending_user.email).exists():
            messages.info(request, "Account already activated.")
        else:
            UserDetails.objects.create_user(
                username=pending_user.email.split('@')[0],
                email=pending_user.email,
                password=pending_user.password,
                is_active=True
            )
            messages.success(request, "Your account has been activated. Please log in.")
        pending_user.delete()
        return redirect('auth_page')
    except PendingUser.DoesNotExist:
        messages.error(request, "Invalid or expired confirmation link.")
        return redirect('auth_page')

@login_required
def friends_page(request):
    current_user = request.user
    sent_requests = FriendRequest.objects.filter(
        from_user=current_user,
        is_accepted=False
    ).select_related('to_user')
    received_requests = FriendRequest.objects.filter(
        to_user=current_user,
        is_accepted=False
    ).select_related('from_user')
    friends = FriendRequest.objects.filter(
        (Q(from_user=current_user) | Q(to_user=current_user)) &
        Q(is_accepted=True)
    ).select_related('from_user', 'to_user')
    friend_list = []
    for fr in friends:
        if fr.from_user == current_user:
            friend_list.append(fr.to_user)
        else:
            friend_list.append(fr.from_user)
    excluded_ids = (
        [fr.to_user.id for fr in sent_requests] +
        [fr.from_user.id for fr in received_requests] +
        [user.id for user in friend_list] +
        [current_user.id]
    )
    discover_users = UserDetails.objects.exclude(id__in=excluded_ids)
    active_tab = request.GET.get('tab', 'friends')
    context = {
        'discover_users': discover_users,
        'sent_requests': [fr.to_user for fr in sent_requests],
        'received_requests': [fr.from_user for fr in received_requests],
        'friends': friend_list,
        'active_tab': active_tab,
    }
    return render(request, 'accounts/friends.html', context)

@login_required
def send_friend_request(request, user_id):
    to_user = UserDetails.objects.get(id=user_id)
    friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
    if created:
        Notification.objects.create( # NEW: Create notification for friend request
            user=to_user,
            sender=request.user,
            notification_type='friend_request',
            content=f"{request.user.username} sent you a friend request.",
            related_object_id=friend_request.id
        )
        messages.success(request, f"Friend request sent to {to_user.username}.")
    else:
        messages.info(request, f"Friend request already sent to {to_user.username}.")
    next_tab = request.POST.get('next_tab', 'discover')
    return redirect(f"{reverse('friends')}?tab={next_tab}")

@login_required
def accept_request(request, user_id):
    req = FriendRequest.objects.get(from_user_id=user_id, to_user=request.user)
    if not req.is_accepted:
        req.is_accepted = True
        req.save()
        Notification.objects.create( # NEW: Create notification for friend request accepted
            user=req.from_user,
            sender=request.user,
            notification_type='friend_accepted',
            content=f"{request.user.username} accepted your friend request.",
            related_object_id=req.id
        )
        messages.success(request, f"You are now friends with {req.from_user.username}.")
    next_tab = request.POST.get('next_tab', 'requests')
    return redirect(f"{reverse('friends')}?tab={next_tab}")

@login_required
def reject_request(request, user_id):
    FriendRequest.objects.filter(from_user_id=user_id, to_user=request.user).delete()
    next_tab = request.POST.get('next_tab', 'requests')
    return redirect(f"{reverse('friends')}?tab={next_tab}")

def user_logout(request):
    logout(request)
    return redirect('auth_page')

@login_required
def profile_view(request):
    user = request.user
    friends = user.get_friends()
    post = user.get_posts().filter(is_active=True)
    posts_count = post.count()
    friends_count = len(friends)
    if request.method == 'POST':
        if 'remove_profile_photo' in request.POST:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
                user.profile_photo = None
                user.save()
            return redirect('profile')
        form = UserDetailsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserDetailsForm(instance=user)
    context = {
        'form': form,
        'friends_count': friends_count,
        'member_since': user.date_joined.strftime("%b %Y"),
        'user': user,
        'post_count': posts_count,
    }
    return render(request, 'profile.html', context)
