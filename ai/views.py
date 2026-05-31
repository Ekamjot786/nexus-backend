import requests
import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from conversations.models import Conversation, Message, AIConversation
from conversations.serializers import MessageSerializer

def ask_kin(system_prompt, messages):
    """Call Groq API (free) for Kin AI responses."""
    resp = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {os.getenv('GROQ_API_KEY')}"
        },
        json={
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'system', 'content': system_prompt}] + messages,
            'max_tokens': 1024,
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']

def build_full_context(user):
    """Build context from ALL user conversations for Kin AI."""
    conversations = Conversation.objects.filter(members=user)
    context = ''
    for conv in conversations:
        if conv.is_group:
            conv_name = conv.name or f'Group {conv.id}'
        else:
            other = conv.members.exclude(id=user.id).first()
            conv_name = f'DM with {other.username}' if other else 'DM'

        messages = conv.messages.all()
        if not messages.exists():
            continue

        context += f'\n--- {conv_name} ---\n'
        for m in messages:
            who = 'Kin AI' if m.is_ai else (m.sender.username if m.sender else 'Unknown')
            context += f'[{m.created_at.strftime("%Y-%m-%d %H:%M")}] {who}: {m.content}\n'

    return context or '(no messages yet)'

@api_view(['POST'])
def ask_conversation(request, conv_id):
    """Ask Kin AI about a specific conversation — reads ALL user chats as context."""
    question = request.data.get('question', '')
    try:
        conv = Conversation.objects.get(id=conv_id, members=request.user)
    except Conversation.DoesNotExist:
        return Response({'error': 'Access denied'}, status=403)

    full_context = build_full_context(request.user)
    from datetime import date
    system_prompt = f"""You are Kin AI, an assistant embedded in a messaging app called Nexus.
You have access to ALL of the user's conversations. Use this to answer questions accurately.
When asked about what someone said, refer to the exact messages with dates and which chat they were in.
Today's date is {date.today()}.

ALL CONVERSATIONS:
{full_context}"""

    try:
        reply = ask_kin(system_prompt, [{'role': 'user', 'content': question}])
        ai_msg = Message.objects.create(conversation=conv, sender=None, content=reply, is_ai=True)
        return Response({'reply': reply})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def private_chat(request):
    """Private Kin AI chat — remembers conversation history + reads all user chats."""
    try:
        message = request.data.get('message', '')
        if not message:
            return Response({'error': 'message required'}, status=400)

        history = list(AIConversation.objects.filter(user=request.user).values('role', 'content'))
        AIConversation.objects.create(user=request.user, role='user', content=message)

        full_context = build_full_context(request.user)
        from datetime import date
        system_prompt = f"""You are Kin AI, a personal assistant in the Nexus messaging app.
You have memory of this conversation and access to the user's full message history across all their chats.
Use this context to answer questions about past conversations, summarize chats, or help generally.
Today is {date.today()}.

ALL CONVERSATIONS:
{full_context}"""

        msgs = history + [{'role': 'user', 'content': message}]
        reply = ask_kin(system_prompt, msgs)
        AIConversation.objects.create(user=request.user, role='assistant', content=reply)
        return Response({'reply': reply})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def chat_history(request):
    history = AIConversation.objects.filter(user=request.user).values('role', 'content', 'created_at')
    return Response(list(history))

@api_view(['DELETE'])
def clear_history(request):
    AIConversation.objects.filter(user=request.user).delete()
    return Response({'success': True})
