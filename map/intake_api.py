import json
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.utils.crypto import salted_hmac
from pydantic import ValidationError
from lifeline_core.schemas import Intake, FeedbackInput, MAX_INTAKE_BODY_BYTES, MAX_NEED_TEXT_LENGTH
from asgiref.sync import async_to_sync
from mcp_server.web_client import search_resources
from .recommendation_feedback import submit_feedback


def limited(request, limit, namespace="triage"):
    # No transcripts or raw IPs in the cache. Production should configure a shared
    # cache or edge rate limit for multiple workers; local cache is process-scoped.
    address=request.META.get('REMOTE_ADDR','unknown')
    if settings.FEEDBACK_TRUST_HEROKU_PROXY:
        address=request.META.get('HTTP_X_FORWARDED_FOR',address).split(',')[-1].strip()
    import time
    key=namespace+':'+salted_hmac(namespace+'-rate',address+str(int(time.time())//60)).hexdigest()
    if cache.add(key,1,timeout=65): return False
    try: return cache.incr(key)>limit
    except ValueError: return False


def safe_json(view):
    @wraps(view)
    @never_cache
    @sensitive_post_parameters()
    @sensitive_variables()
    def wrapped(request):
        if request.content_type!='application/json':
            return JsonResponse({'error':'Send JSON in the request body.'},status=415)
        body_limit = MAX_INTAKE_BODY_BYTES if view.__name__ == "triage_api" else 20000
        try:
            if int(request.META.get('CONTENT_LENGTH') or 0) > body_limit:
                return JsonResponse({'error':'Request is too large.'},status=413)
            body=request.body
            if len(body) > body_limit: return JsonResponse({'error':'Request is too large.'},status=413)
            data=json.loads(body)
            if limited(request,30):
                if view.__name__=='triage_api':
                    from lifeline_core.safety import safety_status
                    from lifeline_core.service import crisis_result
                    from lifeline_core.repository import SafetyDirectory
                    intake=Intake.model_validate(data)
                    safety_text=intake.need_text+' '+(intake.location or '')+' '+' '.join(c.value for c in intake.constraints)
                    if safety_status(safety_text)=='crisis':
                        return JsonResponse(crisis_result(SafetyDirectory()))
                return JsonResponse({'error':'Please wait a minute before trying again.'},status=429)
            return JsonResponse(view(data))
        except (ValueError,ValidationError,TypeError):
            return JsonResponse({'error':'Please check the input and try again.'},status=400)
        except Exception:
            # No raw request/error reporting, including with DEBUG enabled.
            return JsonResponse({'error':'Guided help is temporarily unavailable. Try the map or contact a caseworker.'},status=503)
    return wrapped


@require_POST
@safe_json
def triage_api(data):
    request=Intake.model_validate(data)
    return async_to_sync(search_resources)(request)


@require_POST
@safe_json
def outcome_api(data):
    request=FeedbackInput.model_validate(data)
    return submit_feedback(**request.model_dump())


@never_cache
@ensure_csrf_cookie
def intake_page(request):
    return render(request, 'guided_help.html')


@never_cache
@ensure_csrf_cookie
def mcp_search_page(request):
    from .voice_api import voice_enabled
    return render(request,'intake.html',{'max_need_text_length': MAX_NEED_TEXT_LENGTH, 'voice_api_enabled':voice_enabled()})
