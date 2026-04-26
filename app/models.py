from django.db import models

class DisasterReport(models.Model):
    disaster_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=20)
    description = models.TextField()
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.disaster_type