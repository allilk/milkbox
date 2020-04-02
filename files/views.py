from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template import loader
from .models import cachedFile, cachedSharedDrive, UserProfile
from .utils import get_service, add, add_tds, convert_bytes, get_changes
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from requests_oauthlib import OAuth2Session
import json, datetime

client_id = '631412553786-5k8431814r6rcc7c17dttbrk9cd5ij5s.apps.googleusercontent.com'
client_secret = 'idp7icIrPCt3EF59n-fyV-7T'
redirect_uri = 'http://127.0.0.1:8000/oauth2callback'
authorization_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
token_url = "https://www.googleapis.com/oauth2/v4/token"
scope = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/drive.activity.readonly"]

def index(request):
    return render(request, 'main_index.html')
def profilePage(request, profile_id):
    return HttpResponse(f"Hello, {request.user.username}")
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
        'parent': parent_folder
    }
    return render(request, 'main_files.html', context)
def fileBrowserRefresh(request, folder_id):
    if folder_id == 'my-drive':
        add(current_user=request.user, folder_id="root", refresh=True)
    else:
        add(current_user=request.user, folder_id=folder_id, refresh=True)
    return redirect('/files/'+folder_id)    
def driveBrowser(request):
    driveList=cachedSharedDrive.objects.all().filter(users__contains=[request.user.id]).order_by('name')
    if not driveList: add_tds(current_user=request.user)
    driveList=cachedSharedDrive.objects.all().filter(users__contains=[request.user.id]).order_by('name')
    context = {
        'drive_list': driveList,
    }
    return render(request, 'main_drives.html', context)
def changeBrowser(request, folder_id):
    changeList=get_changes(current_user=request.user, folder_id=folder_id)
    context = {
        'change_list': changeList,
        'date':datetime.date.today()
    }
    return render(request, 'main_changes.html', context)
def OAuth2Callback(request):
    gdrive=OAuth2Session(client_id,scope=scope,redirect_uri=redirect_uri)
    auth_url, state=gdrive.authorization_url(authorization_base_url,access_type="offline",prompt="consent")
    if request.GET.get('code') is not None:
        print('test')
        auth_code=request.GET['code']
        token=gdrive.fetch_token(token_url,client_secret=client_secret,code=auth_code)
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
                authenticate(request, user_id=existing_user.id)
                print("LOG : User Logged in: " + existing_user.username)
            else:
                user=User.objects.create_user(username=display_name, email=email_address)
                user.set_unusable_password()
                user.save()
                print("LOG : New User Registered.")
                existing_user=User.objects.select_related('userprofile').get(email=email_address)
                existing_user.userprofile.gdrive_auth=token
                existing_user.userprofile.save()
                authenticate(request, id=existing_user.id)
            return HttpResponse("Hello! " + existing_user.username)
        else:
            request.user.userprofile.gdrive_auth=token
            request.user.userprofile.save()
            return redirect('/profile/'+str(request.user.id))
    else: return redirect(auth_url)
