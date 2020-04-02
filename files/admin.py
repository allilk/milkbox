from django.contrib import admin
from .models import cachedFile, cachedSharedDrive, UserProfile

admin.site.register(cachedFile)
admin.site.register(cachedSharedDrive)
admin.site.register(UserProfile)