from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_conversations),
    path('dm/', views.create_dm),
    path('group/', views.create_group),
    path('<int:conv_id>/members/', views.get_members),
    path('<int:conv_id>/messages/', views.list_messages),
    # Invite
    path('<int:conv_id>/invite/', views.generate_invite),
    path('invite/<str:code>/', views.invite_info),
    path('invite/<str:code>/join/', views.join_via_invite),
    # Calendar tasks
    path('<int:conv_id>/tasks/', views.list_tasks),
    path('<int:conv_id>/tasks/create/', views.create_task),
    path('tasks/<int:task_id>/', views.delete_task),
]
