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
    session_token = str(uuid.uuid4())
    cache.set(f"scrape_session_{session_token}", cookies_json, timeout=7200)

    return Response({'session_token': session_token})



@api_view(['GET'])
def fetch_category(request):
    token = request.query_params.get('session_token')
    cookie_json = cache.get(f"scrape_session_{token}")
    if not cookie_json:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)

    # Rebuild session
    session = requests.Session()
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
