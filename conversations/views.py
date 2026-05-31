from rest_framework.decorators import api_view
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from users.serializers import UserSerializer

def notify_members(member_ids, conv_id):
    channel_layer = get_channel_layer()
    for uid in member_ids:
        async_to_sync(channel_layer.group_send)(
            f'user_{uid}',
            {'type': 'conversation_created', 'conversationId': conv_id}
        )

@api_view(['GET'])
def list_conversations(request):
    convs = Conversation.objects.filter(members=request.user).distinct()
    # Sort by last message time in Python to avoid duplicate rows from JOIN
    convs = sorted(convs, key=lambda c: c.messages.last().created_at if c.messages.exists() else c.created_at, reverse=True)
    return Response(ConversationSerializer(convs, many=True, context={'request': request}).data)

@api_view(['POST'])
def create_dm(request):
    user_id = request.data.get('userId')
    if not user_id:
        return Response({'error': 'userId required'}, status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        other = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    existing = Conversation.objects.filter(is_group=False, members=request.user).filter(members=other).first()
    if existing:
        return Response({'id': existing.id})

    conv = Conversation.objects.create(is_group=False, created_by=request.user)
    conv.members.add(request.user, other)

    # Notify both users
    notify_members([request.user.id, other.id], conv.id)

    return Response({'id': conv.id})

@api_view(['POST'])
def create_group(request):
    name = request.data.get('name')
    member_ids = request.data.get('memberIds', [])
    if not name or not member_ids:
        return Response({'error': 'name and memberIds required'}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    conv = Conversation.objects.create(name=name, is_group=True, created_by=request.user)
    all_ids = list(set([request.user.id] + member_ids))
    members = User.objects.filter(id__in=all_ids)
    conv.members.set(members)

    # Notify all members
    notify_members(all_ids, conv.id)

    return Response({'id': conv.id})

@api_view(['GET'])
def get_members(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response(UserSerializer(conv.members.all(), many=True).data)

@api_view(['GET'])
def list_messages(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Access denied'}, status=403)
    return Response(MessageSerializer(conv.messages.all(), many=True).data)
