from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path('register/', views.RegisterView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('me/', views.me),
    path('users/search/', views.search_users),

    # Admin endpoints
    path('admin/stats/', admin_views.stats),
    path('admin/users/', admin_views.list_users),
    path('admin/users/<int:user_id>/ban/', admin_views.ban_user),
    path('admin/users/<int:user_id>/unban/', admin_views.unban_user),
    path('admin/users/<int:user_id>/delete/', admin_views.delete_user),
    path('admin/conversations/', admin_views.list_conversations),
    path('admin/conversations/<int:conv_id>/', admin_views.delete_conversation),
    path('admin/conversations/<int:conv_id>/messages/', admin_views.list_messages),
    path('admin/messages/<int:msg_id>/', admin_views.delete_message),
]
