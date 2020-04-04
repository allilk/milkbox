from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector
from django.db.models import Q

from .models import cachedFile, cachedSharedDrive, UserProfile
from .utils import get_service, add, add_tds, convert_bytes, get_changes
from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_BASE_URL, TOKEN_URL, SCOPES, DEBUG

from requests_oauthlib import OAuth2Session
import json, datetime


def index(request):
    context = {
        'debug': DEBUG
    }
    if request.user.is_authenticated is False:
        return render(request, 'public_index.html', context)
    elif request.user.is_authenticated is True:
        return render(request, 'main_index.html', context)
def privacyPolicy(request):
    return render(request, 'public_privacy_policy.html')
@login_required(login_url='/oauth2callback')
def profilePage(request, profile_id):
    # PLACEHOLDER
    return HttpResponse(f"Hello, {request.user.username}")
@login_required(login_url='/oauth2callback')
def fileBrowser(request, folder_id):
    if folder_id == 'my-drive':
        fileList=cachedFile.objects.all().filter(tags__contains=['mydrive'], users__contains=[request.user.id]).order_by('name')
        if not fileList: add(current_user=request.user, folder_id="root")
        fileList=cachedFile.objects.all().filter(tags__contains=['mydrive'], users__contains=[request.user.id]).order_by('name')
    elif folder_id == 'shared-with-me' or folder_id == 'favourites':
        fileList=cachedFile.objects.all().filter(tags__contains=[folder_id], users__contains=[request.user.id]).order_by('name')
        if not fileList: add(current_user=request.user, folder_id=folder_id)
        fileList=cachedFile.objects.all().filter(tags__contains=[folder_id], users__contains=[request.user.id]).order_by('name')
    else:
        fileList=cachedFile.objects.all().filter(parents=folder_id, users__contains=[request.user.id]).order_by('name')
        if not fileList: add(current_user=request.user, folder_id=folder_id)
        fileList=cachedFile.objects.all().filter(parents=folder_id, users__contains=[request.user.id]).order_by('name')
    folder_list=[]
    file_list=[]
    for item in fileList:
        if 'folder' in item.mimetype:
            folder_list.append(item)
        else:
            file_list.append(item)
    fileList=folder_list+file_list
    try:
        parent_folder=cachedFile.objects.get(file_id=folder_id)
        parent_folder=parent_folder.parents
        if parent_folder == 'null':
            parent_folder="my-drive"
    except:
        parent_folder="my-drive"
    context = {
        'file_list': fileList,
        'date':datetime.date.today(),
        'parent': parent_folder,
        'debug': DEBUG
    }
    return render(request, 'main_files.html', context)
@login_required(login_url='/oauth2callback')
def fileBrowserRefresh(request, folder_id):
    if folder_id == 'my-drive':
        add(current_user=request.user, folder_id="root", refresh=True)
    else:
        add(current_user=request.user, folder_id=folder_id, refresh=True)
    return redirect('/files/'+folder_id)    
def sharedFileBrowser(request, folder_id):
    current_user=request.user
    if current_user.is_authenticated:
        fileList=cachedFile.objects.all().filter(parents=folder_id, shared_with__contains=[int(current_user.id)], is_shared=True).order_by('name')
    else:
        fileList=cachedFile.objects.all().filter(parents=folder_id, shared_with__contains=[0], is_shared=True).order_by('name')
    if not fileList:
        fileList=cachedFile.objects.all().filter(parents=folder_id, shared_with__contains=[0], is_shared=True).order_by('name')
    folder_list=[]
    file_list=[]
    for item in fileList:
        if 'folder' in item.mimetype:
            folder_list.append(item)
        else:
            file_list.append(item)
    fileList=folder_list+file_list
    try:
        parent_folder=cachedFile.objects.get(file_id=folder_id)
        parent_folder=parent_folder.parents
        if parent_folder == 'null':
            parent_folder="my-drive"
    except:
        parent_folder="my-drive"
    context = {
        'file_list': fileList,
        'date':datetime.date.today(),
        'parent': parent_folder,
        'debug': DEBUG
    }
    return render(request, 'main_files.html', context)
@login_required(login_url='/oauth2callback')
def driveBrowser(request):
    driveList=cachedSharedDrive.objects.all().filter(users__contains=[request.user.id]).order_by('name')
    if not driveList: add_tds(current_user=request.user)
    driveList=cachedSharedDrive.objects.all().filter(users__contains=[request.user.id]).order_by('name')
    context = {
        'driveList': driveList,
        'debug': DEBUG
    }
    return render(request, 'main_shared_drives.html', context)
@login_required(login_url='/oauth2callback')
def searchBrowser(request):
    search_query=None
    if 'q' in request.GET:
        search_query = request.GET['q']
    if search_query is not None:
        print("Running search..")
        fileList=[]
        resultList=cachedFile.objects.annotate(search=SearchVector('name')).filter(Q(search=search_query)|Q(search__icontains=search_query),users__contains=[request.user.id])
        fileList = { i.file_id : i for i in resultList }.values()
        try:
            parent_folder=cachedFile.objects.get(file_id=folder_id)
            parent_folder=parent_folder.parents
            if parent_folder == 'null':
                parent_folder="my-drive"
        except:
            parent_folder="my-drive"
        context = {
            'file_list': fileList,
            'date':datetime.date.today(),
            'parent': parent_folder,
            'debug': DEBUG
        }
        return render(request, 'main_search.html', context)
    else:
        return render(request, 'main_search.html')
@login_required(login_url='/oauth2callback')
def changeBrowser(request, folder_id):
    changeList=get_changes(current_user=request.user, folder_id=folder_id)
    context = {
        'change_list': changeList,
        'date':datetime.date.today(),
        'debug': DEBUG
    }
    return render(request, 'main_changes.html', context)
def OAuth2Callback(request):
    gdrive=OAuth2Session(CLIENT_ID,scope=SCOPES,redirect_uri=REDIRECT_URI)
    auth_url, state=gdrive.authorization_url(AUTH_BASE_URL,access_type="offline",prompt="consent")
    if request.GET.get('code') is not None:
        auth_code=request.GET['code']
        token=gdrive.fetch_token(TOKEN_URL,client_secret=CLIENT_SECRET,code=auth_code)
        gdrive=OAuth2Session(token=token)
        user=gdrive.get("https://www.googleapis.com/drive/v3/about?fields=*")
        user=user.json()
        display_name=(user['user']['displayName']).replace(' ', '_')
        email_address=user['user']['emailAddress']
        token=json.dumps(token)
        if request.user.is_authenticated is False:
            try:
                existing_user=User.objects.select_related('userprofile').get(email=email_address)
            except:
                existing_user=None
            if existing_user is not None:
                existing_user.userprofile.gdrive_auth=token
                existing_user.userprofile.save()
                login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
                print("LOG : User Logged in: " + existing_user.username)
            else:
                user=User.objects.create_user(username=display_name, email=email_address)
                user.set_unusable_password()
                user.save()
                print("LOG : New User Registered. "+ display_name)
                existing_user=User.objects.select_related('userprofile').get(email=email_address)
                existing_user.userprofile.gdrive_auth=token
                existing_user.userprofile.save()
                login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
            return HttpResponse("Hello! " + existing_user.username)
        else:
            request.user.userprofile.gdrive_auth=token
            request.user.userprofile.save()
            return redirect('/files/my-drive')
    else: return redirect(auth_url)
