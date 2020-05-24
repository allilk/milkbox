from django.shortcuts import render, redirect
from django.template import loader
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector
from django.db.models import Q

from .models import cachedFile, cachedSharedDrive, UserProfile
from .tasks import fileManagement ,userManagement

from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_BASE_URL, TOKEN_URL, SCOPES, DEBUG, EXTERNAL_AUTH_ALLOWED, FALLBACK_AUTH

from requests_oauthlib import OAuth2Session
import json, datetime, time

# def condec(dec, condition):
#     def decorator(func):
#         if (condition ):
#             return func
#         return dec(func)
#     return decorator

def index(request):
    context = {'debug':DEBUG}
    if (request.user.is_authenticated == False):
        return render(request, 'public_index.html', context)
    elif (request.user.is_authenticated == True):
        return render(request, 'main_index.html', context)
def privacyPolicy(request):
    context = {'debug':DEBUG}
    return render(request, 'public_privacy_policy.html', context)
def aboutPage(request):
    context = {'debug':DEBUG}
    return render(request, 'public_about.html', context)
def OAuth2Callback(request):
    gdrive=OAuth2Session(CLIENT_ID,scope=SCOPES,redirect_uri=REDIRECT_URI)
    auth_url, state=gdrive.authorization_url(
        AUTH_BASE_URL, access_type="offline", prompt="consent")
    if (request.GET.get('code') != None):
        auth_code=request.GET['code']
        token=gdrive.fetch_token(TOKEN_URL,client_secret=CLIENT_SECRET,code=auth_code)
        gdrive=OAuth2Session(token=token)
        user=(gdrive.get('https://www.googleapis.com/drive/v3/about?fields=*')).json()['user']
        display_name=(user['displayName']).replace(' ', '_')
        email_address=user['emailAddress']
        if (request.user.id == None):
            passId = -1
        login(
            request,
            userManagement(email_address, passId).add_auth(display_name, token),
            backend='django.contrib.auth.backends.ModelBackend'
        )
        return redirect('/files/my-drive')
    else: return redirect(auth_url)
# def sharedFileBrowser(request, folder_id):

def fileBrowser(request, folder_id):
    context = fileManagement(request.user.id, folder_id).browse_files()
    return render(request, 'main_files.html', context)
@login_required
def fileBrowserRefresh(request, folder_id):
    fileManagement(request.user.id, folder_id).add_file(True)
    return redirect('/files/'+folder_id)
@login_required
def driveBrowser(request):
    context = fileManagement(request.user.id).browse_drives()
    return render(request, 'main_shared_drives.html', context)
@login_required
def driveBrowserRefresh(request):
    fileManagement(request.user.id).add_shared_drive(True)
    return redirect('/shared_drives')
@login_required
def searchBrowser(request):
    context={'debug':DEBUG}
    search_query = None
    if ('q' in request.GET):
        search_query = request.GET['q']
        if ('True' in request.GET.getlist('experimental')):
            context = fileManagement(request.user.id).search_files(search_query, False)
        else:
            context = fileManagement(request.user.id).search_files(search_query, False)
    return render(request, 'main_search.html', context)
@login_required
def changeBrowser(request, folder_id):
    # context = fileManagement(request.user.id, folder_id).get_changes()
    return render(request, 'main_changes.html', context)