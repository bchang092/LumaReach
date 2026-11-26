from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.template.response import TemplateResponse

from .activity import PAGES, today
from .models import CommunityFeedback, PageActivity, RecommendationFeedback, ResourceTagReview


@admin.register(CommunityFeedback)
class CommunityFeedbackAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "name", "approved", "created_at")
    list_filter = ("approved", "category", "created_at")
    search_fields = ("title", "body", "name")
    ordering = ("-created_at",)
    actions = ("approve_feedback", "hide_feedback")

    @admin.action(description="Approve selected feedback (publish)")
    def approve_feedback(self, request, queryset):
        count = queryset.update(approved=True)
        self.message_user(request, f"Published {count} feedback post(s).")

    @admin.action(description="Hide selected feedback (mark unapproved)")
    def hide_feedback(self, request, queryset):
        count = queryset.update(approved=False)
        self.message_user(request, f"Hidden {count} feedback post(s).")


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = ('resource_id','helpful','created_at')
    list_filter = ('helpful',)
    readonly_fields = ('resource_id','helpful','created_at')
    def has_add_permission(self,request): return False

@admin.register(ResourceTagReview)
class ResourceTagReviewAdmin(admin.ModelAdmin):
    list_display = ('resource_id','proposed_tag','status','created_at')
    list_filter = ('status','proposed_tag')
    readonly_fields = ('resource_id','proposed_tag','evidence','record_sha256','created_at')


@admin.register(PageActivity)
class PageActivityAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise PermissionDenied
        days = {"1": 1, "7": 7, "30": 30}.get(request.GET.get("days"), 7)
        end = today()
        start = end - timedelta(days=days - 1)
        metrics = ("views", "clicks", "helpful", "unhelpful")
        counts = PageActivity.objects.filter(day__range=(start, end)).values("page").annotate(
            **{f"total_{field}": Sum(field) for field in metrics}
        )
        by_page = {record["page"]: record for record in counts}
        rows = []
        totals = dict.fromkeys(metrics, 0)
        for page, label in PAGES.items():
            record = by_page.get(page, {})
            row = {field: record.get(f"total_{field}", 0) for field in metrics}
            for field in metrics:
                totals[field] += row[field]
            rows.append({"label": label, **row})
        rows.sort(key=lambda row: (-row["views"], -row["clicks"], row["label"]))
        return TemplateResponse(request, "admin/map/pageactivity/report.html", {
            **self.admin_site.each_context(request), "title": "Page activity",
            "opts": self.model._meta, "days": days, "periods": (1, 7, 30),
            "start": start, "end": end, "rows": rows, "totals": totals,
        })
