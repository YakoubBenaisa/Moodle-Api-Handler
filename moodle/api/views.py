# views.py
import json, uuid
import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from bs4 import BeautifulSoup
from django.http import HttpResponse

from services.login import login as login_service
from services.categories import get_categories as get_categories
from services.courses import get_courses
from services.chapters import get_chapters as get_chapters
from services.resources import get_resource

@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'Missing credentials'}, status=status.HTTP_400_BAD_REQUEST)

    cookies_json = login_service(username, password)

    if cookies_json == "Login failed":
        return Response({'error': 'Login failed'}, status=status.HTTP_401_UNAUTHORIZED)

    session_token = str(uuid.uuid4())
    cache.set(f"scrape_session_{session_token}", cookies_json, timeout=7200)

    return Response({'session_token': session_token, 'cookies': cookies_json})



@api_view(['GET'])
def fetch_category(request):
    token = request.query_params.get('session_token')

    # Rebuild session
    session = requests.Session()

    cookie_json = cache.get(f"scrape_session_{token}")
    if  cookie_json:
        #return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
        session.cookies.update(json.loads(cookie_json))




    courses = get_categories(session)


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
    data = get_courses(session, id)


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
    data = get_chapters(session, id)

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
    result = get_resource(session, resource_id)

    if 'error' in result:
        return Response({'error': result['error']}, status=status.HTTP_404_NOT_FOUND)

    # Create a response with the file content
    response = HttpResponse(result['content'], content_type=result['content_type'])
    response['Content-Disposition'] = f'inline; filename="{result["filename"]}"'
    return response





# views.py
from django.http import JsonResponse
from .models import Notification
from services.notification import get_notifications
from .tasks import send_notification_to_webhook
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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

        # Rebuild session from cookies
        session = requests.Session()
        session.cookies.update(json.loads(cookie_json))
    except Exception as e:
        return Response({'error': f'Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 2: Scrape notifications
    try:
        notifications_data = get_notifications(session)

        if not notifications_data.get('notifications'):
            return JsonResponse({'status': 'No new notifications'})

        new_notifications = []
        for notif in notifications_data['notifications']:
            notif_id = notif.get("aria_label")
            message = notif.get("message")
            timestamp_str = notif.get("timestamp")

            # Convert timestamp string to datetime object
            # This is a simplified example - adjust the format as needed
            try:
                timestamp = datetime.strptime(timestamp_str, "%d %b, %H:%M") if timestamp_str else datetime.now()
            except ValueError:
                # If parsing fails, use current time
                timestamp = datetime.now()

            # Step 3: Store new notifications in the database
            notification, created = Notification.objects.get_or_create(
                notification_id=notif_id,
                defaults={
                    'message': message,
                    'aria_label': notif_id,  # Store aria_label in the correct field
                    'timestamp': timestamp
                }
            )

            if created:
                new_notifications.append(notification)
                # Trigger the task for each new notification
                send_notification_to_webhook.delay(notification.notification_id)

        return JsonResponse({
            'status': 'New notifications scraped and stored',
            'notifications_count': len(new_notifications)
        })

    except requests.RequestException as e:
        return Response({'error': f'Error scraping notifications: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

