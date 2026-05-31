from rest_framework import serializers
from .models import Conversation, Message, ConversationMember
from users.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True, allow_null=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True, allow_null=True)
    sender_color = serializers.CharField(source='sender.color', read_only=True, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'is_ai', 'created_at', 'sender_id', 'sender_username', 'sender_color']

class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    other_color = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'name', 'is_group', 'created_at', 'last_message', 'other_color']

    def get_last_message(self, obj):
        msg = obj.messages.last()
        return msg.content if msg else None

    def get_name(self, obj):
        if obj.is_group:
            return obj.name
        request = self.context.get('request')
        if request:
            other = obj.members.exclude(id=request.user.id).first()
            return other.username if other else 'Unknown'
        return obj.name

    def get_other_color(self, obj):
        if obj.is_group:
            return None
        request = self.context.get('request')
        if request:
            other = obj.members.exclude(id=request.user.id).first()
            return other.color if other else None
        return None
