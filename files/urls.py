from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('files/<str:folder_id>/', views.fileBrowser),
    path('files/<str:folder_id>/changes', views.changeBrowser),
    path('files/<str:folder_id>/refresh', views.fileBrowserRefresh),
    path('shared_drives/', views.driveBrowser),
    path('profile/<int:profile_id>/', views.profilePage),
    path('oauth2callback/', views.OAuth2Callback)
]