from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Full serializer — only use for the logged-in user's own data."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'color', 'is_staff']

class PublicUserSerializer(serializers.ModelSerializer):
    """Safe serializer for search results and member lists — no email exposed."""
    class Meta:
        model = User
        fields = ['id', 'username', 'color']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
