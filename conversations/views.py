import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Conversation, Message, GroupTask
from .serializers import ConversationSerializer, MessageSerializer
from users.serializers import UserSerializer, PublicUserSerializer

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
    return Response(PublicUserSerializer(conv.members.all(), many=True).data)

@api_view(['GET'])
def list_messages(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Access denied'}, status=403)
    return Response(MessageSerializer(conv.messages.all(), many=True).data)


# --- Invite links ---

@api_view(['POST'])
def generate_invite(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user, is_group=True)
    except Conversation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if not conv.invite_code:
        conv.invite_code = uuid.uuid4().hex[:12]
        conv.save()
    return Response({'invite_code': conv.invite_code})


@api_view(['GET'])
@permission_classes([])
def invite_info(request, code):
    try:
        conv = Conversation.objects.get(invite_code=code, is_group=True)
    except Conversation.DoesNotExist:
        return Response({'error': 'Invalid invite link'}, status=404)
    return Response({'id': conv.id, 'name': conv.name, 'member_count': conv.members.count()})


@api_view(['POST'])
def join_via_invite(request, code):
    try:
        conv = Conversation.objects.get(invite_code=code, is_group=True)
    except Conversation.DoesNotExist:
        return Response({'error': 'Invalid invite link'}, status=404)
    if not conv.members.filter(id=request.user.id).exists():
        conv.members.add(request.user)
        notify_members([m.id for m in conv.members.all()], conv.id)
    return Response({'id': conv.id, 'name': conv.name})


# --- Group calendar tasks ---

@api_view(['GET'])
def list_tasks(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    tasks = conv.tasks.prefetch_related('assigned_to').all()
    data = [{
        'id': t.id,
        'title': t.title,
        'due_date': t.due_date,
        'assigned_to': list(t.assigned_to.values('id', 'username', 'color')),
        'created_by': t.created_by.username if t.created_by else None,
    } for t in tasks]
    return Response(data)


@api_view(['POST'])
def create_task(request, conv_id):
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    title = request.data.get('title', '').strip()
    due_date = request.data.get('due_date')
    assigned_ids = request.data.get('assigned_to', [])
    if not title or not due_date:
        return Response({'error': 'title and due_date required'}, status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    task = GroupTask.objects.create(conversation=conv, title=title, due_date=due_date, created_by=request.user)
    if assigned_ids:
        task.assigned_to.set(User.objects.filter(id__in=assigned_ids))

    # Post a system message to the group chat
    assigned = list(task.assigned_to.values_list('username', flat=True))
    assigned_str = f" · Assigned to: {', '.join(assigned)}" if assigned else ''
    system_msg = Message.objects.create(
        conversation=conv,
        sender=None,
        is_ai=True,
        content=f"📅 {request.user.username} added a new task: \"{title}\" — Due {due_date}{assigned_str}"
    )
    from .serializers import MessageSerializer
    from channels.layers import get_channel_layer as gcl
    channel_layer2 = get_channel_layer()
    async_to_sync(channel_layer2.group_send)(
        f'conv_{conv.id}',
        {
            'type': 'chat_message',
            'conversationId': conv.id,
            'message': MessageSerializer(system_msg).data,
        }
    )

    # Notify all group members via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'conv_{conv.id}',
        {
            'type': 'new_task',
            'conversationId': conv.id,
            'task': {
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'created_by': request.user.username,
                'assigned_to': list(task.assigned_to.values('id', 'username', 'color')),
            }
        }
    )

    return Response({
        'id': task.id, 'title': task.title, 'due_date': task.due_date,
        'assigned_to': list(task.assigned_to.values('id', 'username', 'color')),
        'created_by': request.user.username,
    }, status=201)


@api_view(['DELETE'])
def delete_task(request, task_id):
    try:
        task = GroupTask.objects.get(id=task_id, conversation__members=request.user)
    except GroupTask.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    task.delete()
    return Response({'success': True})
