# views.py
import json, uuid
import requests
import logging
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from bs4 import BeautifulSoup

from services.login import login as login_service
from services.categories import get_categories as get_categories
from services.courses import get_courses
from services.chapters import get_chapters as get_chapters
from services.resources import get_resource
from services.notification import get_notifications
from .models import Notification
from .tasks import send_notification_to_webhook

logger = logging.getLogger(__name__)

@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'Missing credentials'}, status=status.HTTP_400_BAD_REQUEST)

    cookies_json = login_service(username, password, "bba")

    if cookies_json == "Login failed":
        return Response({'error': 'Login failed'}, status=status.HTTP_401_UNAUTHORIZED)

    session_token = str(uuid.uuid4())
    cache.set(f"scrape_session_{session_token}", cookies_json, timeout=7200)

    # Immediately scrape notifications after successful login
    try:
        logger.info(f"Starting notification scraping after login for session {session_token}")

        # Get session cookies
        session_cookies = json.loads(cookies_json)
        logger.debug("Successfully parsed session cookies")

        '''# Scrape notifications using MoodleTerminator
        logger.info("Calling get_notifications...")
        notifications = get_notifications(session_cookies)
        logger.info(f"Retrieved {len(notifications) if notifications else 0} notifications")

        # Process and store notifications
        new_notifications = []
        if notifications:
            for notif in notifications:
                # Extract notification details
                # Make sure notif is a dictionary before using get()
                if not isinstance(notif, dict):
                    logger.warning(f"Unexpected notification format: {notif}")
                    continue

                notif_id = str(notif.get("id", ""))
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
                    # Trigger the task for each new notification
                    logger.info(f"Queueing webhook task for notification {notification.notification_id}")
                    try:
                        # Use the simpler delay method
                        task_result = send_notification_to_webhook.delay(notification.notification_id)
                        logger.info(f"Task queued with ID: {task_result.id}")
                    except Exception as task_error:
                        logger.error(f"Error queueing task: {task_error}")
                        # Try direct execution as fallback
                        try:
                            logger.info("Attempting direct task execution...")
                            result = send_notification_to_webhook(notification.notification_id)
                            logger.info(f"Direct execution result: {result}")
                        except Exception as direct_error:
                            logger.error(f"Error in direct execution: {direct_error}")
'''
        # Return login response with notification info
        return Response({
            'session_token': session_token,
            'cookies': cookies_json,
            'notifications': {
                #'total': len(notifications) if notifications else 0,
                #'new': len(new_notifications)
            }
        })
    except Exception as e:
        # If notification scraping fails, still return the login info
        # but log the error and include it in the response
        logger.error(f"Error scraping notifications during login: {e}")
        return Response({
            'session_token': session_token,
            'cookies': cookies_json,
            'notifications_error': str(e)
        })



@api_view(['GET'])
def fetch_category(request):
    token = request.query_params.get('session_token')

    # Rebuild session
    session = requests.Session()

    cookie_json = cache.get(f"scrape_session_{token}")
    if  cookie_json:
        #return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
        session.cookies.update(json.loads(cookie_json))




    courses = get_categories(session, 'bba')


    return Response({'data': courses})



@api_view(['GET'])
def fetch_courses(request):
    token = request.query_params.get('session_token')
    cookie_json = cache.get(f"scrape_session_{token}")
    if not cookie_json:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)

    # Rebuild session
    session = requests.Session()
    session.cookies.update(json.loads(cookie_json))

    id = request.query_params.get('id')
    data = get_courses(session, id, 'bba')


    return Response({'data': data})


@api_view(['GET'])
def fetch_chapters(request):

    token = request.query_params.get('session_token')
    cookie_json = cache.get(f"scrape_session_{token}")
    if not cookie_json:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)

    # Rebuild session
    session = requests.Session()
    session.cookies.update(json.loads(cookie_json))

    id = request.query_params.get('id')
    data = get_chapters(session, id, 'bba')

    return Response({'data': data})

@api_view(['GET'])
def fetch_resource(request):
    token = request.query_params.get('session_token')
    resource_id = request.query_params.get('id')

    if not token or not resource_id:
        return Response({'error': 'Missing session token or resource ID'}, status=status.HTTP_400_BAD_REQUEST)

    cookie_json = cache.get(f"scrape_session_{token}")
    if not cookie_json:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)

    # Rebuild session
    session = requests.Session()
    session.cookies.update(json.loads(cookie_json))

    # Use the service to get the resource
    result = get_resource(session, resource_id, 'bba')

    if 'error' in result:
        return Response({'error': result['error']}, status=status.HTTP_404_NOT_FOUND)

    # Create a response with the file content
    response = HttpResponse(result['content'], content_type=result['content_type'])
    response['Content-Disposition'] = f'inline; filename="{result["filename"]}"'
    return response





# Notification views

@api_view(['GET'])
def scrape_and_store_notifications(request):
    """
    View that scrapes notifications, stores them in the database,
    and triggers the webhook to send new notifications.
    """
    try:
        # Step 1: Get the session token from query params
        token = request.query_params.get('session_token')
        if not token:
            return Response({'error': 'Session token missing'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve session cookies from cache using the token
        cookie_json = cache.get(f"scrape_session_{token}")
        if not cookie_json:
            return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get session cookies
        session_cookies = json.loads(cookie_json)
    except Exception as e:
        return Response({'error': f'Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 2: Scrape notifications using MoodleTerminator
    try:
        notifications = get_notifications(session_cookies, 'bba')

        if not notifications:
            return JsonResponse({'status': 'No notifications found'})

        new_notifications = []
        for notif in notifications:
            # Extract notification details
            # Make sure notif is a dictionary before using get()
            if not isinstance(notif, dict):
                logger.warning(f"Unexpected notification format: {notif}")
                continue

            notif_id = str(notif.get("id", ""))
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

            # Step 3: Store new notifications in the database
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
                # Trigger the task for each new notification
                logger.info(f"Queueing webhook task for notification {notification.notification_id}")
                try:
                    # Use the simpler delay method
                    task_result = send_notification_to_webhook.delay(notification.notification_id)
                    logger.info(f"Task queued with ID: {task_result.id}")
                except Exception as task_error:
                    logger.error(f"Error queueing task: {task_error}")
                    # Try direct execution as fallback
                    try:
                        logger.info("Attempting direct task execution...")
                        result = send_notification_to_webhook(notification.notification_id)
                        logger.info(f"Direct execution result: {result}")
                    except Exception as direct_error:
                        logger.error(f"Error in direct execution: {direct_error}")

        return JsonResponse({
            'status': 'Notifications scraped and stored',
            'notifications_count': len(new_notifications),
            'total_notifications': len(notifications)
        })

    except Exception as e:
        logger.error(f"Error scraping notifications: {e}")
        return Response({'error': f'Error scraping notifications: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def webhook_receiver(request):
    """
    Webhook endpoint to receive notifications from external sources.
    """
    try:
        data = request.data

        # Validate required fields
        if not data.get('message'):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique ID if not provided
        notification_id = data.get('notification_id', str(uuid.uuid4()))

        # Create notification in database
        notification, created = Notification.objects.get_or_create(
            notification_id=notification_id,
            defaults={
                'message': data.get('message'),
                'aria_label': data.get('aria_label', data.get('message')[:50]),
                'timestamp': datetime.now()
            }
        )

        return JsonResponse({
            'status': 'success',
            'created': created,
            'notification_id': notification.notification_id
        })

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return Response({'error': f'Error processing webhook: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

