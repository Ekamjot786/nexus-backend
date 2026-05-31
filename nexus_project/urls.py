from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('users.urls')),
    path('api/conversations/', include('conversations.urls')),
    path('api/ai/', include('ai.urls')),
]
