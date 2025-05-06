from django.urls import path
from .views import fetch_courses, login, fetch_chapters, fetch_category

urlpatterns = [
    path("login/", login),
    path("categories/", fetch_category),
    path("courses/", fetch_courses),
    path("chapters/", fetch_chapters),
]
