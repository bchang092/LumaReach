from django.db import models


class CommunityFeedback(models.Model):
    CATEGORY_SUGGESTION = "suggestion"
    CATEGORY_CORRECTION = "correction"
    CATEGORY_BUG = "bug"
    CATEGORY_EXPERIENCE = "experience"

    CATEGORY_CHOICES = [
        (CATEGORY_SUGGESTION, "Suggestion"),
        (CATEGORY_CORRECTION, "Resource correction"),
        (CATEGORY_BUG, "Bug report"),
        (CATEGORY_EXPERIENCE, "Service experience"),
    ]

    name = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=160)
    body = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class FeedbackRateLimit(models.Model):
    # HMAC of IP + hourly window; do not persist the raw IP address.
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


class RecommendationFeedback(models.Model):
    """Private outcome counts only. Free-text comments are intentionally discarded."""
    resource_id = models.PositiveIntegerField(db_index=True)
    helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)


class ResourceTagReview(models.Model):
    """Crowd proposals never auto-publish or overwrite source reliability."""
    resource_id = models.PositiveIntegerField(db_index=True)
    proposed_tag = models.CharField(max_length=100)
    evidence = models.TextField()
    record_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='pending', choices=[('pending','Pending'),('accepted','Accepted for audit'),('rejected','Rejected')])
    created_at = models.DateTimeField(auto_now_add=True)


class PageActivity(models.Model):
    day = models.DateField()
    page = models.CharField(max_length=40)
    views = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)
    helpful = models.PositiveBigIntegerField(default=0)
    unhelpful = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Page activity"
        constraints = [
            models.UniqueConstraint(fields=["day", "page"], name="activity_day_page")
        ]
