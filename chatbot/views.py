import requests
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ChatMessage
import logging
import json
from functools import lru_cache

logger = logging.getLogger(__name__)
OLLAMA_API_URL = 'http://localhost:11434/api/generate'

def get_ollama_response(prompt):
    """Ollama API'ye istek gönder"""
    enhanced_prompt = f"""Lütfen aşağıdaki mesaja Türkçe olarak, doğal ve akıcı bir dille yanıt ver. 
    Cevabın samimi ve yardımsever olsun.
    
    Kullanıcı mesajı: {prompt}"""
    
    payload = {
        "model": "mistral",
        "prompt": enhanced_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 1024,
            "stop": ["User:", "Kullanıcı:"],
            "num_thread": 4
        }
    }
    
    logger.info(f"Sending request to Ollama with payload: {json.dumps(payload)}")
    
    response = requests.post(
        OLLAMA_API_URL,
        json=payload,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json().get("response", "")

@login_required
def chat_view(request):
    if request.method == 'POST':
        try:
            # Log raw request data for debugging
            logger.info(f"Request POST data: {request.POST}")
            logger.info(f"Request body: {request.body.decode()}")
            
            user_message = request.POST.get('message', '')
            user_message = user_message.strip()
            
            logger.info(f"Processed message: '{user_message}'")
            
            if not user_message:
                return JsonResponse({'response': "I didn't receive any message. What would you like to ask?"})

            # Kullanıcının mesajını kaydet
            ChatMessage.objects.create(user=request.user, role='user', message=user_message)

            try:
                # Ollama'ya istek gönder
                bot_reply = get_ollama_response(user_message)
                logger.info(f"Received response from Ollama: {bot_reply}")
                
                # Bot cevabını kaydet
                ChatMessage.objects.create(user=request.user, role='bot', message=bot_reply)

                return JsonResponse({'response': bot_reply})

            except requests.Timeout:
                return JsonResponse(
                    {'response': "I'm thinking a bit longer than usual. Could you try asking again, maybe with a shorter question?"},
                    status=200
                )
            except requests.RequestException as e:
                logger.error(f"Error connecting to Ollama: {str(e)}")
                return JsonResponse(
                    {'response': "I'm having trouble thinking right now. Could you try again in a moment?"},
                    status=200
                )
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return JsonResponse(
                    {'response': "Something unexpected happened. Could you try asking your question again?"},
                    status=200
                )

        except Exception as e:
            logger.error(f"View error: {str(e)}")
            return JsonResponse(
                {'response': "I encountered an error. Please try again."},
                status=200
            )

    else:
        history = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:10]
        return render(request, 'chatbot/chat.html', {"messages": reversed(history)})