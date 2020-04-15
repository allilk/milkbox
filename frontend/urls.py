from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('files/<str:folder_id>/', views.fileBrowser),
    path('files/<str:folder_id>/changes', views.changeBrowser),
    path('files/<str:folder_id>/refresh', views.fileBrowserRefresh),
    # path('files/<str:folder_id>/view', views.sharedFileBrowser),
    path('shared_drives/', views.driveBrowser),
    path('shared_drives/refresh', views.driveBrowserRefresh),
    # path('profile/<int:profile_id>/', views.profilePage),
    path('oauth2callback/', views.OAuth2Callback),
    path('privacy-policy/', views.privacyPolicy),
    path('about/', views.aboutPage),
    path('search/', views.searchBrowser),
    path('oauthcallback/', auth_views.LoginView.as_view()),
]