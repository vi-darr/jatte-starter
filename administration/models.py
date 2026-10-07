import uuid

from django.db import models

from account.models import User


class Report(models.Model):
    """A generated administration report capturing key metrics."""

    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

    PERIOD_CHOICES = (
        (DAILY, 'Daily'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default=DAILY)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports'
    )

    # Snapshot metrics stored at generation time
    total_rooms = models.PositiveIntegerField(default=0)
    active_rooms = models.PositiveIntegerField(default=0)
    closed_rooms = models.PositiveIntegerField(default=0)
    waiting_rooms = models.PositiveIntegerField(default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    avg_overall_rating = models.FloatField(null=True, blank=True)
    avg_responsiveness = models.FloatField(null=True, blank=True)
    avg_helpfulness = models.FloatField(null=True, blank=True)

    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.title} ({self.get_period_display()}) – {self.period_start:%Y-%m-%d}'
