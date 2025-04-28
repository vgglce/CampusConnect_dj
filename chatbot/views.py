import requests
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ChatMessage

OLLAMA_API_URL = 'http://ollama:11434/api/generate'

@login_required
def chat_view(request):
    if request.method == 'POST':
        user_message = request.POST.get('message')

        # Kullanıcının mesajını kaydet
        ChatMessage.objects.create(user=request.user, role='user', message=user_message)

        # Geçmiş konuşmaları çekelim
        history = ChatMessage.objects.filter(user=request.user).order_by('timestamp')
        full_conversation = ""
        for msg in history:
            role = "User:" if msg.role == 'user' else "Assistant:"
            full_conversation += f"{role} {msg.message}\n"

        # Ollama'ya istek at
        payload = {
            "model": "mistral",
            "prompt": full_conversation,
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload)
        bot_reply = response.json().get("response", "Sorry, I couldn't generate a response.")

        # Bot cevabını da kaydedelim
        ChatMessage.objects.create(user=request.user, role='bot', message=bot_reply)

        return render(request, 'chatbot/chat.html', {"messages": history})

    else:
        history = ChatMessage.objects.filter(user=request.user).order_by('timestamp')
        return render(request, 'chatbot/chat.html', {"messages": history})