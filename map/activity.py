from zoneinfo import ZoneInfo

from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .intake_api import limited
from .models import PageActivity

PAGES = {
    "home": "Home", "map": "Resource map", "guided": "Guided help",
    "mcp-search": "MCP resource search", "questionnaire": "Questionnaire", "plan": "Help plan", "crisis": "Immediate support",
    "about": "About", "actions": "Choose your path", "community": "Community feedback",
    "mobile-first": "Mobile-first", "community-led": "Community-led",
    "review": "Resource review",
}


def today():
    return timezone.localdate(timezone=ZoneInfo("America/New_York"))


@require_POST
def record_activity(request):
    if int(request.META.get("CONTENT_LENGTH") or 0) > 1024:
        return HttpResponse(status=413)
    if request.content_type != "application/x-www-form-urlencoded":
        return HttpResponse(status=415)
    data = request.POST
    if set(data) != {"page", "event", "count"}:
        return HttpResponse(status=400)
    page, event, count = data["page"], data["event"], data["count"]
    if page not in PAGES or event not in {"views", "clicks", "helpful", "unhelpful"}:
        return HttpResponse(status=400)
    if not count.isascii() or not count.isdecimal() or not 1 <= int(count) <= (100 if event == "clicks" else 1):
        return HttpResponse(status=400)
    if limited(request, 120, namespace="activity"):
        return HttpResponse(status=429)
    # Unique daily bucket and database-side arithmetic preserve simultaneous increments.
    bucket, _ = PageActivity.objects.get_or_create(day=today(), page=page)
    PageActivity.objects.filter(pk=bucket.pk).update(**{event: F(event) + int(count)})
    return HttpResponse(status=204)
