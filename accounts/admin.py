from django.contrib import admin

from accounts.models import UserDetails, Post, FriendRequest, PendingUser, Like, Comment, Bookmark

admin.site.register(UserDetails)
admin.site.register(Post)   
admin.site.register(FriendRequest) 
admin.site.register(PendingUser)
admin.site.register(Like)
admin.site.register(Comment)
admin.site.register(Bookmark)  # Register Bookmark modela 