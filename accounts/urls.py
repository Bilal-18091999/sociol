from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [
    path('', views.auth_page, name='auth_page'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path("user_logout/", views.user_logout, name="user_logout"),
    
    path('confirm/<uuid:token>/', views.confirm_email, name='confirm_email'),

    # path('friends/', views.friends_page, name='friends'),
    # path('send-request/<int:user_id>/', views.send_friend_request, name='send_request'),
    # path('accept-request/<int:user_id>/', views.accept_request, name='accept_request'),
    # path('reject-request/<int:user_id>/', views.reject_request, name='reject_request'),

     path('friends/', views.friends_page, name='friends'),
    path('send-request/<int:user_id>/', views.send_friend_request, name='send_request'),
    path('accept-request/<int:user_id>/', views.accept_request, name='accept_request'),
    path('reject-request/<int:user_id>/', views.reject_request, name='reject_request'),
    path('user-profile/<int:user_id>/', views.user_profile_view, name='user_profile'),

    path('profile/', views.profile_view, name='profile'),

]