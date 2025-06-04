# tasks.py
from celery import shared_task
import requests
from django.conf import settings
from .models import Notification

@shared_task
def send_notifications_to_webhook():
    """
    Task that fetches unsent notifications from the database and sends them to the webhook.
    """
    try:
        # Get unsent notifications
        notifications = Notification.objects.filter(sent=False)

        if not notifications:
            return "No new notifications to send."

        # Send notifications to the webhook
        for notif in notifications:
            try:
                response = requests.post(
                    settings.NOTIFICATION_WEBHOOK_URL,  # Webhook URL from settings
                    json={
                        'aria_label': notif.aria_label,
                        'message': notif.message,
                        'timestamp': notif.timestamp,
                    },
                    timeout=5
                )
                response.raise_for_status()

                # mark the notification as sent
                notif.sent = True
                notif.save()

            except requests.exceptions.RequestException as e:
                # Log error if sending fails
                logger.error(f"Failed to send notification {notif.notification_id}: {e}")

        return f"Sent {len(notifications)} notification(s)"

    except Exception as e:
        logger.error(f"Error in sending notifications: {e}")
        raise e
