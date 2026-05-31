from django.urls import path
from . import views

urlpatterns = [
    path('ask/<int:conv_id>/', views.ask_conversation),
    path('chat/', views.private_chat),
    path('chat/history/', views.chat_history),
    path('chat/clear/', views.clear_history),
]
