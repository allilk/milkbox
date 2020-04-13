from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.models import User

urlpatterns = [
    path('', include('frontend.urls')),
    path('admin/', admin.site.urls)
]
