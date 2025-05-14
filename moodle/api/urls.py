from django.urls import path
from .views import fetch_courses, login, fetch_chapters, fetch_category, fetch_resource, scrape_and_store_notifications

urlpatterns = [
    path("login/", login),
    path("categories/", fetch_category),
    path("courses/", fetch_courses),
    path("chapters/", fetch_chapters),
    path("resource/", fetch_resource),
    path('notifications/', scrape_and_store_notifications, name='notifications'),
]
