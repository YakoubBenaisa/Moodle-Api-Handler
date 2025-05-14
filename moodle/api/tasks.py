# api/tasks.py
from celery import shared_task
import requests
from django.conf import settings
from django.core.cache import cache
import logging
from .models import Notification
from services.notification import get_notifications

logger = logging.getLogger(__name__)

@shared_task
def scrape_notifications():
    """
    Task that scrapes notifications from Moodle and stores them in the database.
    This task is scheduled to run periodically via Celery Beat.
    """
    try:
        # We need an authenticated session to scrape notifications
        # This is a challenge for a scheduled task since we need user credentials
        # For now, we'll just log that this needs to be implemented
        logger.warning("Scheduled notification scraping needs an authenticated session - not implemented yet")

        # In a real implementation, you would:
        # 1. Use a service account or stored credentials to authenticate with Moodle
        # 2. Use the session to scrape notifications
        # 3. Store new notifications
        # 4. Trigger the webhook for new notifications

        # For testing purposes, you can manually trigger the webhook endpoint with a session token

        return "Scheduled notification scraping needs implementation"
    except Exception as e:
        logger.error(f"Error in scheduled notification scraping: {e}")
        raise e

@shared_task
def send_notification_to_webhook(notification_id):
    """
    Task that sends a specific notification to the webhook.
    """
    try:
        # Get the notification from the database
        notification = Notification.objects.get(notification_id=notification_id, sent=False)

        # Send it to the webhook
        response = requests.post(
            settings.NOTIFICATION_WEBHOOK_URL,
            json={
                'notification_id': notification.notification_id,
                'message': notification.message,
                'timestamp': notification.timestamp,
            },
            timeout=5
        )
        response.raise_for_status()

        # Mark as sent
        notification.sent = True
        notification.save()

        return f"Sent notification {notification_id} to webhook"
    except Notification.DoesNotExist:
        logger.warning(f"Notification {notification_id} not found or already sent")
        return f"Notification {notification_id} not found or already sent"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification {notification_id} to webhook: {e}")
        raise e
