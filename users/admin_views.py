from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from conversations.models import Conversation, Message, AIConversation

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdminUser])
def stats(request):
    return Response({
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'banned_users': User.objects.filter(is_active=False).count(),
        'total_conversations': Conversation.objects.count(),
        'total_messages': Message.objects.count(),
        'group_conversations': Conversation.objects.filter(is_group=True).count(),
        'dm_conversations': Conversation.objects.filter(is_group=False).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    users = User.objects.all().order_by('-date_joined').values(
        'id', 'username', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'color'
    )
    return Response(list(users))


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ban_user(request, user_id):
    if request.user.id == user_id:
        return Response({'error': 'Cannot ban yourself'}, status=400)
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return Response({'success': True, 'username': user.username})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def unban_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        return Response({'success': True, 'username': user.username})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):
    if request.user.id == user_id:
        return Response({'error': 'Cannot delete yourself'}, status=400)
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        return Response({'success': True, 'username': username})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_conversations(request):
    convs = []
    for conv in Conversation.objects.all().order_by('-created_at'):
        members = list(conv.members.values_list('username', flat=True))
        convs.append({
            'id': conv.id,
            'name': conv.name or (f"DM: {' & '.join(members)}" if not conv.is_group else f"Group: {conv.name or conv.id}"),
            'is_group': conv.is_group,
            'members': members,
            'member_count': len(members),
            'message_count': conv.messages.count(),
            'created_at': conv.created_at,
        })
    return Response(convs)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_conversation(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id)
        conv.delete()
        return Response({'success': True})
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_messages(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)
    messages = conv.messages.select_related('sender').order_by('created_at').values(
        'id', 'sender__username', 'content', 'is_ai', 'created_at'
    )
    return Response(list(messages))


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_message(request, msg_id):
    try:
        msg = Message.objects.get(id=msg_id)
        msg.delete()
        return Response({'success': True})
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=404)
