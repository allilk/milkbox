from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from .models import cachedFile, cachedSharedDrive
from .config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from requests_oauthlib import OAuth2Session

import json, datetime
from dateutil.parser import isoparse

def convert_bytes(num):
    step_unit=1000.0
    for x in ['byte','KB','MB','GB','TB']:
        if num < step_unit:
            return "%3.1f %s" % (num, x)
        num /= step_unit
def get_folder_size(current_user, folder_id, bytes_return=False):
    try:
        file_list=cachedFile.objects.all().filter(parents=folder_id)
    except:
        pass
        # add(current_user, folder_id)
    total_size=0
    for item in file_list:
        total_size+=int(item.byte_size)
    if bytes_return is True:
        final_size=total_size
    else:
        final_size=convert_bytes(int(total_size))
    return final_size
def get_service(current_user, user_id=None, activity=False):
    credentials=None
    if user_id is None:
        g_auth=json.loads(current_user.userprofile.gdrive_auth)
    else:
        g_auth=json.loads(User.objects.select_related('userprofile').get(id=user_id).userprofile.gdrive_auth)

    credentials=Credentials(token=g_auth['access_token'],refresh_token=g_auth['refresh_token'],
    token_uri=TOKEN_URL,client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    if activity is False:
        service=build('drive','v3',credentials=credentials)
    elif activity is True:
        service=build('driveactivity','v2',credentials=credentials)
    return service
def add(current_user, folder_id, refresh=False):
    print('LOG : Running cache load.')
    all_files=[]
    service=get_service(current_user)
    user_list=[current_user.id]
    if refresh is True:
        if folder_id == 'shared-with-me' or folder_id == 'favourites':
            file_list=cachedFile.objects.all().filter(tags__contains=[folder_id], users__contains=[current_user.id])
        elif folder_id =='root':
            file_list=cachedFile.objects.all().filter(tags__contains=['mydrive'], users__contains=[current_user.id])
        else:
            file_list=cachedFile.objects.all().filter(parents=folder_id)
        for item in file_list:
            user_list+=list(dict.fromkeys(item.users))
        file_list.delete()
    file_list={'nextPageToken':None}
    user_list=list(dict.fromkeys(user_list))
    query=f"'{folder_id}' in parents and trashed=false"
    tags=[]
    if folder_id == 'shared-with-me':
        query='sharedWithMe and trashed=false'
    elif folder_id == 'favourites':
        query='starred=True and trashed=false'
    while 'nextPageToken' in file_list:
        file_list=service.files().list(q=query,
        fields="nextPageToken, files(id, name, parents, size, mimeType, modifiedTime)",pageSize=1000,
        supportsAllDrives=True,includeItemsFromAllDrives=True,
        pageToken=file_list['nextPageToken']).execute()
        all_files+=file_list['files']
    for item in all_files:
        if 'size' not in item:
            item_size='0 MB'
            byte_size='0'
            # item_size=get_folder_size(current_user=current_user, folder_id=item['id'])
            # byte_size=get_folder_size(current_user=current_user, folder_id=item['id'], bytes_return=True)
        else:
            item_size=convert_bytes(int(item['size']))
            byte_size=item['size']
        moddatetime = isoparse(item['modifiedTime'])
        mod_date=moddatetime.strftime("%Y-%m-%d")
        mod_time=moddatetime.strftime("%H:%M:%S.%f%z")
        if folder_id == 'shared-with-me':
            tags=['shared-with-me']
            parent_folder='null'
        elif folder_id == 'root':
            tags=['mydrive']
            parent_folder=item['parents'][0]
        elif folder_id == 'favourites':
            tags=['favourites']
            parent_folder=item['parents'][0]
        else:
            parent_folder=item['parents'][0]
        newFile=cachedFile(
            name=item['name'],
            file_id=item['id'],
            parents=parent_folder,
            mimetype=item['mimeType'],
            file_size=item_size,
            byte_size=str(byte_size),
            modified_date=mod_date,
            modified_time=mod_time,
            users=user_list,
            tags=tags,
            shared_with=user_list
            )
        newFile.save()
        print(f"LOG : '{item['name']}' successfully cached.")
def add_tds(current_user, refresh=False):
    service=get_service(current_user) 
    user_list=[current_user.id]
    if refresh is True:
        drive_list=cachedSharedDrive.objects.all().filter(users__contains=[current_user.id])
        for item in drive_list:
            user_list+=list(dict.fromkeys(item.users))
        drive_list.delete()
    user_list=list(dict.fromkeys(user_list))
    drive_list=[]
    shared_drives={'nextPageToken':None}
    while 'nextPageToken' in shared_drives:
        shared_drives = service.drives().list(pageSize=100,pageToken=shared_drives['nextPageToken']).execute()
        drive_list+=shared_drives['drives']
    for drive in drive_list:
        newDrive=cachedSharedDrive(
            name=drive['name'],
            drive_id=drive['id'],
            users=user_list
            )
        newDrive.save()
        print(f"LOG : '{drive['name']}' successfully cached.")
def get_changes(current_user, folder_id):
    service=get_service(current_user=current_user, activity=True)
    act_name=""
    item=cachedFile.objects.filter(file_id=folder_id)[0]
    if not item:
        add(current_user, folder_id=folder_id)
        item=cachedFile.objects.get(file_id=folder_id)
    if 'apps.folder' in item.mimetype: act_name='ancestorName'
    else: act_name='itemName'
    result_list=service.activity().query(body={
        'pageSize':500,
        f'{act_name}':f'items/{folder_id}'}).execute()['activities']
    change_list=[]
    for activity in result_list:
        timestamp=activity['timestamp']
        targets=activity['targets'][0]
        changed_id=""
        if 'teamDrive' in targets:
            new_target=targets['teamDrive']
            changed_id=(new_target['name']).split('teamDrives/')[1]
        elif 'driveItem' in targets:
            new_target=targets['driveItem']
            changed_id=(new_target['name']).split('items/')[1]
            actions=activity['actions'][0]
        file_action=''
        if 'create' in actions['detail']: file_action='Created'
        elif 'delete' in actions['detail']: file_action='Deleted'
        elif 'move' in actions['detail']: file_action='Moved'
        elif 'rename' in actions['detail']: file_action='Renamed'
        elif 'permissionChange' in actions['detail']: file_action='Permissions updated.'
        elif 'restore' in actions['detail']: file_action='Restored from Trash.'
        elif 'edit' in actions['detail']: file_action='Edited.'
        moddatetime = isoparse(timestamp)
        mod_date=moddatetime.strftime("%B  %d, %Y")
        mod_time=moddatetime.strftime("%H:%M:%S.%f%z")
        if file_action is not None:
            newobj={
                'change':f'File {file_action}',
                'file':new_target['title'],
                'file_id':changed_id,
                'date':mod_date,
                'time':mod_time
            }
            change_list.append(newobj) 
    return change_list