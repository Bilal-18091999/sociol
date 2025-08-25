from django.urls import path
from . import views
app_name = 'posts'

urlpatterns = [
    path('create/', views.create_post, name='create_post'),
   
    path('feed/', views.feed_view, name='feed'),
    path('your_feed/', views.your_feed, name='your_feed'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('edit-post/<int:post_id>/', views.edit_post, name='edit_post'),

    
    path('post/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:post_id>/comments/', views.get_comments, name='get_comments'),
    path('post/<int:post_id>/likers/', views.get_likers, name='get_likers'),


    path('post/<int:post_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('saved-posts/', views.saved_posts_view, name='saved_posts'),


    path('linkedin_config/',views.linkedin_config,name='linkedin_config'),
    path('facebook_instagram_config/',views.facebook_instagram_config,name='facebook_instagram_config'),
    path('post/<int:post_id>/share/instagram/', views.post_to_instagram, name='post_to_instagram'),


    path('post/<int:post_id>/share/facebook/', views.post_to_facebook, name='post_to_facebook'),

    path('post/<int:post_id>/share/linkedin/', views.linkedin_login, name='linkedin_login'),
    path("linkedin/callback/", views.linkedin_callback, name="linkedin_callback"),

   
]

