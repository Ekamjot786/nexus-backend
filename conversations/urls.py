from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_conversations),
    path('dm/', views.create_dm),
    path('group/', views.create_group),
    path('<int:conv_id>/members/', views.get_members),
    path('<int:conv_id>/messages/', views.list_messages),
]
