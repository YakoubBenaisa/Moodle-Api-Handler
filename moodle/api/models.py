from django.db import models

# Create your models here.

class Notification(models.Model):
    notification_id = models.CharField(max_length=255, unique=True)
    message = models.TextField()
    aria_label = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    sent = models.BooleanField(default=False)  # Whether the notification was sent to the webhook

    def __str__(self):
        return self.message
