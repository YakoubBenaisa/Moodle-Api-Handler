# api/tasks.py
from celery import shared_task
import requests
import json
from django.conf import settings
from django.core.cache import cache
import logging
from datetime import datetime
from .models import Notification
from services.notification import get_notifications

logger = logging.getLogger(__name__)

@shared_task
def scrape_notifications():
    """
    Task that scrapes notifications from Moodle and stores them in the database.
    This task is scheduled to run periodically via Celery Beat.

    Note: This task requires valid session cookies to be stored in the cache.
    """
    try:
        # Get all active session tokens from cache
        # This is a simplified approach - in production, you might want to use a more robust method
        # to store and retrieve session credentials

        # For now, we'll check if there's a stored session in settings
        if hasattr(settings, 'MOODLE_SESSION_COOKIES') and settings.MOODLE_SESSION_COOKIES:
            session_cookies = settings.MOODLE_SESSION_COOKIES
            logger.info("Using session cookies from settings")
        else:
            # Try to find any active session in cache
            # This is just a fallback and not reliable for production
            active_sessions = []
            for key in cache.keys("scrape_session_*"):
                cookie_json = cache.get(key)
                if cookie_json:
                    active_sessions.append(json.loads(cookie_json))

            if not active_sessions:
                logger.warning("No active sessions found in cache")
                return "No active sessions found"

            # Use the first active session
            session_cookies = active_sessions[0]
            logger.info("Using session cookies from cache")

        # Use the MoodleTerminator to get notifications
        notifications = get_notifications(session_cookies)

        if not notifications:
            logger.info("No notifications found")
            return "No notifications found"

        # Process notifications
        new_notifications = []
        for notif in notifications:
            # Extract notification details
            notif_id = notif.get("id", "")
            message = notif.get("fullmessage", "")
            subject = notif.get("subject", "")

            # Use fullmessagehtml as a fallback if fullmessage is empty
            if not message and notif.get("fullmessagehtml"):
                message = notif.get("fullmessagehtml")

            # Use subject as aria_label if available
            aria_label = subject or message[:50]

            # Get timestamp
            timestamp_str = notif.get("timecreated")
            try:
                # Convert Unix timestamp to datetime if available
                timestamp = datetime.fromtimestamp(int(timestamp_str)) if timestamp_str else datetime.now()
            except (ValueError, TypeError):
                # If parsing fails, use current time
                timestamp = datetime.now()

            # Store new notifications in the database
            notification, created = Notification.objects.get_or_create(
                notification_id=notif_id,
                defaults={
                    'message': message,
                    'aria_label': aria_label,
                    'timestamp': timestamp
                }
            )

            if created:
                new_notifications.append(notification)
                # Trigger the webhook for each new notification
                send_notification_to_webhook.delay(notification.notification_id)

        return f"Scraped {len(notifications)} notifications, {len(new_notifications)} new"
    except Exception as e:
        logger.error(f"Error in scheduled notification scraping: {e}")
        raise e

@shared_task
def send_notification_to_webhook(notification_id):
    """
    Task that sends a notification to the webhook.
    """
    logger.info(f"Starting webhook task for notification {notification_id}")
    try:
        # Get the notification from the database
        notification = Notification.objects.get(notification_id=notification_id, sent=False)
        logger.info(f"Found notification: {notification.notification_id}, message: {notification.message[:50]}...")

        # Log the webhook URL
        webhook_url = settings.NOTIFICATION_WEBHOOK_URL
        logger.info(f"Sending to webhook URL: {webhook_url}")

        # Prepare payload
        payload = {
            'notification_id': notification.notification_id,
            'message': notification.message,
            'aria_label': notification.aria_label,
            'timestamp': notification.timestamp.isoformat(),
            'token': settings.WEBHOOK_SECRET_TOKEN  # Simple authentication
        }
        logger.debug(f"Payload: {payload}")

        # Send it to the webhook with simple token authentication
        logger.info("Sending POST request to webhook...")
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=5
        )

        # Log response details
        logger.info(f"Webhook response status: {response.status_code}")
        logger.debug(f"Webhook response content: {response.text[:200]}")

        # Check for success
        response.raise_for_status()

        # Mark as sent
        notification.sent = True
        notification.save()
        logger.info(f"Successfully sent notification {notification_id} to webhook and marked as sent")

        return f"Sent notification {notification_id} to webhook"
    except Notification.DoesNotExist:
        logger.warning(f"Notification {notification_id} not found or already sent")
        return f"Notification {notification_id} not found or already sent"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification {notification_id} to webhook: {e}")
        return f"Error sending notification: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error sending notification {notification_id}: {e}")
        return f"Unexpected error: {str(e)}"
