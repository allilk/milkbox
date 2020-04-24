from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from .models import cachedFile, cachedSharedDrive
from .config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL, DEBUG
from django.shortcuts import get_object_or_404

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from requests_oauthlib import OAuth2Session

import json, datetime
from dateutil.parser import isoparse


class fileManagement:
    def __init__(self, current_user_id, folder_id=None):
        activity=False
        self.current_user = User.objects.get(
                id=int(current_user_id)
            )
        self.folder_id = folder_id
        self.refresh = False
        self.userList = [current_user_id]
        credentials = None
        if (current_user_id == None):
            g_auth=json.loads(self.current_user.userprofile.gdrive_auth)
        else:
            g_auth=json.loads(User.objects.select_related('userprofile').get(id=current_user_id).userprofile.gdrive_auth)
        credentials=Credentials(token=g_auth['access_token'],refresh_token=g_auth['refresh_token'],
        token_uri=TOKEN_URL,client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
        if (not credentials) or (not credentials.valid):
            if (credentials and credentials.expired and credentials.refresh_token):
                credentials.refresh(Request())
        if (activity == False):
            self.service=build('drive','v3',credentials=credentials)
        elif (activity == True):
            self.service=build('driveactivity','v2',credentials=credentials)
    def add_file(self, refresh=False):
        if (refresh == True):
            self.userList = self.purge_file(False)
        query_tag = f"'{self.folder_id}' in parents"
        tags = []
        if (self.folder_id == 'shared-with-me'):
            query_tag="sharedWithMe"
            tags=['shared-with-me']
        elif (self.folder_id == 'favourites'):
            query_tag="starred=True"
            tags=['favourites']
        elif (self.folder_id == 'root') or (self.folder_id == 'my-drive'):
            query_tag="'root' in parents"
            tags=['my-drive']
        query=f"{query_tag} and trashed=false"
        print(query)
        completeList = []
        fileList={'nextPageToken':None}
        while 'nextPageToken' in fileList:
            fileList=self.service.files().list(
                q=query,
                fields="nextPageToken, files(name, id, parents, size, mimeType, modifiedTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
                pageToken=fileList['nextPageToken']
            ).execute()
            completeList+=fileList['files']
        for item in completeList:
            if (self.folder_id == 'shared-with-me'):
                parentFolder='null'
            else:
                parentFolder=item['parents'][0]
            if ('size' not in item):
                itemSize = '0 MB'
                byteSize = '0'
            else:
                itemSize = self.convert_bytes(int(item['size']))
                byteSize = item['size']
            dateTime=isoparse(item['modifiedTime'])
            cachedFile(
                name=item['name'],
                file_id=item['id'],
                parents=parentFolder,
                mimetype=item['mimeType'],
                file_size=itemSize,
                byte_size=str(byteSize),
                modified_date=dateTime.strftime("%Y-%m-%d"),
                modified_time=dateTime.strftime("%H:%M:%S.%f%z"),
                users=self.userList,
                tags=tags,
                shared_with=self.userList
            ).save()

            print(f"LOG : '{item['name']}' successfully cached by '{self.current_user.username}'.")
    def purge_file(self, sd):
        if (sd == False):
            if (self.folder_id == 'shared-with-me') or (self.folder_id == 'favourites'):
                fileList=cachedFile.objects.all().filter(
                    tags__contains=[folder_id], users__contains=self.userList)
            elif (self.folder_id == 'my-drive'):
                fileList=cachedFile.objects.all().filter(tags__contains=['my-drive'],
                    users__contains=self.userList)
            else:
                fileList=cachedFile.objects.all().filter(parents=self.folder_id)
        elif (sd == True):
            fileList=cachedSharedDrive.objects.all().filter(
                users__contains=self.userList)
        for item in fileList:
            self.userList += list(dict.fromkeys(item.users))
        fileList.delete()
        return list(dict.fromkeys(self.userList))
    def clean_cache(self):
        fileList=cachedFile.objects.all().filter(users__contains=self.userList)
        for item in fileList:
            if (len(item.users) > 1):
                fileList.remove(item)
            elif (len(item.users) == 1):
                cachedFile.objects.get(file_id=item.file_id).delete()       
    def convert_bytes(self, num):
        step_unit=1000.0
        for x in ['byte','KB','MB','GB','TB']:
            if (num < step_unit):
                return ("%3.1f %s" % (num, x))
            num /= step_unit
    def add_shared_drive(self, refresh=False):
        if (refresh == True):
            self.userList = self.purge_file(True)
        completeList=[]
        driveList={'nextPageToken':None}
        while 'nextPageToken' in driveList:
            driveList=self.service.drives().list(
                pageSize=100,
                pageToken=driveList['nextPageToken']
            ).execute()
            completeList+=driveList['drives']
        for drive in completeList:
            cachedSharedDrive(
                name=drive['name'],
                drive_id=drive['id'],
                users=self.userList
            ).save()
            print(f"LOG : '{drive['name']}' successflly cached by '{self.current_user.username}'")
    def get_changes(self):
        target=None

        if not (cachedFile.objects.get(file_id=self.folder_id)):
            self.add_file()
        item = cachedFile.objects.get(file_id=self.folder_id)

        if ('folder' in item.mimetype): target='ancestorName'
        else: target='itemName'

        resultList=self.service.activity().query(body={
            'pageSize':500,
            f'{target}':f'items/{self.folder_id}'
        }).execute()['activities']

        changeList=[]
        for activ in resultList:
            timestamp=activ['timestamp']
            targets=activ['targets'][0]

            split_value=None
            if ('teamDrive' in targets): split_value='teamDrive'
            elif ('driveItem' in targets): split_value='items'
            new_target=targets[split_value]
            changed_id=(new_target['name']).split(f'{split_value}/')[1]

            action=None
            if ('create' in actions['detail']): file_action='Created'
            elif ('delete' in actions['detail']): file_action='Deleted'
            elif ('move' in actions['detail']): file_action='Moved'
            elif ('rename' in actions['detail']): file_action='Renamed'
            elif ('permissionChange' in actions['detail']): file_action='Permissions updated.'
            elif ('restore' in actions['detail']): file_action='Restored from Trash.'
            elif ('edit' in actions['detail']): file_action='Edited.'

            dateTime=isoparse(item['modifiedTime'])

            if (action != None):
                changeList.append({
                    'change':f'File {action}',
                    'file':new_target['title'],
                    'file_id':changed_id,
                    'date':dateTime.strftime("%Y-%m-%d"),
                    'time':dataTime.strftime("%H:%M:%S.%f%z")
                })
            context = {
                'change_list': changeList,
                'date':datetime.date.today(),
                'debug': DEBUG
            }
        return context
    def search_files(self, query, exp=False):
        if (exp == True):
            resultList=self.service.files().list(
                q=f"fullText contains '{query}' or name contains '{query}'",
                fields="nextPageToken, files(id, name, parents, size, mimeType)",
                pageSize=250,
                corpora='allDrives',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                supportsTeamDrives=True,
                includeTeamDriveItems=True).execute()
            for item in resultList['files']:
                itemExists=None
                try:
                    itemExists=get_object_or_404(cachedFile, parents=item['parents'][0])
                    break
                except:
                    self.folder_id = item['parents'][0]
                    self.add_file(True)
            resultList=None
        resultList=cachedFile.objects.annotate(
            search=SearchVector('name')).filter(Q(
                search=query)|Q(search__icontains=query),
                users__contains=[request.user.id])
        fileList = { i.file_id : i for i in resultList }.values()
        context = {
            'file_list': fileList,
            'date':datetime.date.today(),
            'debug': DEBUG
        }
        return context
    def browse_files(self):
        parentFolder = None
        fileList = []
        while (fileList == []):
            if (self.folder_id in ['my-drive','shared-with-me','favourites']):
                fileList = cachedFile.objects.all().filter(
                    tags__contains=[self.folder_id],
                    users__contains=self.userList
                ).order_by('name')
                parentFolder = 'my-drive'
            else:
                fileList = cachedFile.objects.all().filter(
                    parents=self.folder_id,
                    users__contains=self.userList
                ).order_by('name')
                try:
                    parentFolder = cachedFile.objects.get(file_id=self.folder_id).parents
                except:
                    parentFolder = 'my-drive'
            if (fileList == []): self.add_file()
        file_list=[]
        folder_list=[]
        for item in fileList:
            if ('folder' in item.mimetype): folder_list.append(item)
            else: file_list.append(item)
        fileList=folder_list+file_list
        context={
            'file_list': fileList,
            'date': datetime.date.today(),
            'parent': parentFolder,
            'debug': DEBUG
        }
        return context
    def browse_drives(self):
        driveList = []
        while (driveList == []):
            driveList = cachedSharedDrive.objects.all().filter(
                users__contains=self.userList
            )
            if (driveList == []): self.add_shared_drive()
        context = {
            'driveList': driveList,
            'debug': DEBUG
        }
        return context
      
class userManagement:
    def __init__(self, email, current_user_id):
        self.email = email
        self.current_user = current_user_id

        print(f"Email: {self.email}")
        print(f"ID: {self.current_user}")
        # print(self.current_user)
    def find_existing(self):
        try:
            existingUser = User.objects.select_related('userprofile').get(
                email=self.email
            )
        except:
            existingUser = None
        return existingUser
    def add_auth(self, display_name, token=None):
        
        if (token != None):
            token=json.dumps(token)
        if (self.current_user != '-1'):
            existingUser = self.find_existing()
            if (existingUser != None):
                existingUser.userprofile.gdrive_auth = token
                existingUser.userprofile.save()
                print(f"LOG : User Logged in: '{existingUser.username}'")
            elif (existingUser == None):
                newUser = User.objects.create_user(
                    username=display_name,
                    email=self.email)
                newUser.set_unusuable_password()
                newUser.save()
                existingUser = self.find_existing()
                existingUser.userprofile.gdrive_auth=token
                existingUser.userprofile.save()
                print(f"LOG : New User Registered. '{display_name}'")
        else:
            existingUser = self.find_existing()
            existingUser.userprofile.gdrive_auth = token
            existingUser.userprofile.save()
            print(f"LOG : User: '{existingUser.username}' auth updated.")
        return existingUser
