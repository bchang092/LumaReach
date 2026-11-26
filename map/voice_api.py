"""Bounded, memory-only audio transcription. No file/model output is persisted."""
import os
from lifeline_core.schemas import MAX_NEED_TEXT_LENGTH
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from django.views.decorators.http import require_POST
from .intake_api import limited

MAX_AUDIO_BYTES = 2_000_000
FORMATS = {'audio/webm': ('webm', lambda b: b.startswith(b'\x1aE\xdf\xa3')),
           'audio/mp4': ('mp4', lambda b: len(b) > 12 and b[4:8] == b'ftyp'),
           'audio/wav': ('wav', lambda b: b.startswith(b'RIFF') and b[8:12] == b'WAVE')}


def voice_enabled():
    return bool(os.environ.get('OPENAI_API_KEY')) and os.environ.get('VOICE_USE_API', 'false').lower() == 'true'


@require_POST
@never_cache
@sensitive_post_parameters()
@sensitive_variables()
def transcribe_api(request):
    if not voice_enabled():
        return JsonResponse({'error': 'Server voice is not configured. Use browser voice or type your request.'}, status=503)
    if limited(request, 10):
        return JsonResponse({'error': 'Please wait a minute before recording again.'}, status=429)
    try:
        if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_AUDIO_BYTES:
            return JsonResponse({'error': 'Please record a shorter message.'}, status=413)
        mime = request.content_type
        language = request.GET.get('language', 'en')
        if mime not in FORMATS or language not in {'en', 'es'}:
            return JsonResponse({'error': 'Unsupported audio format or language.'}, status=400)
        audio = request.body
        if len(audio) > MAX_AUDIO_BYTES:
            return JsonResponse({'error': 'Please record a shorter message.'}, status=413)
        extension, valid = FORMATS[mime]
        if len(audio) < 16 or not valid(audio):
            return JsonResponse({'error': 'No readable recording. Please try again or type.'}, status=400)
        from openai import OpenAI
        model = os.environ.get('TRANSCRIPTION_MODEL', 'gpt-transcribe')
        with OpenAI(timeout=20, max_retries=0) as client:
            options = {'extra_body': {'languages': [language]}} if model == 'gpt-transcribe' else {'language': language}
            result = client.audio.transcriptions.create(model=model, file=('speech.' + extension, audio, mime), **options)
        transcript = result.text.strip()
        if not transcript:
            return JsonResponse({'error': 'No words were detected. Please try again or type.'}, status=422)
        if len(transcript) > MAX_NEED_TEXT_LENGTH:
            return JsonResponse({'error': 'That recording is too long. Please record a shorter message.'}, status=422)
        return JsonResponse({'text': transcript})
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Please check the recording and try again.'}, status=400)
    except Exception:
        # SDK errors may contain input. Never return or log them.
        return JsonResponse({'error': 'Voice transcription is unavailable. Please type or try again later.'}, status=503)
