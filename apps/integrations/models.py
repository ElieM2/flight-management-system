from django.db import models


class ApiSyncLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    provider_name = models.CharField(max_length=100)
    sync_type = models.CharField(max_length=100)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    records_received = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'API Sync Log'
        verbose_name_plural = 'API Sync Logs'

    def __str__(self):
        return f"{self.provider_name} - {self.sync_type} - {self.status}"