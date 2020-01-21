#!/usr/bin/env python3

"""
This is convenience script to make life a bit easier when using
Google Drive programmatically. The intention is not to have a general
interface, but to model the expected behavior under some simple
assumptions.

This code does not use the rest api directly (https://developers.google.com/drive/api/v3/)
Instead it uses google-api-python-client (https://github.com/googleapis/google-api-python-client)
which in turn uses the rest API. The API documentation specific to Google Drive is here:
http://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.html

Before using:

    pip install google-api-python-client

Example usage:

    export GOOGLE_APPLICATION_CREDENTIALS=`pwd`/cxc-ska3-ci-cf8821da91e7.json
    pip install --user google-api-python-client
    ./gdrive.py ls ska-ci
    ./gdrive.py upload ska_builder.py ska-ci
    ./gdrive.py download ska-ci/ska_builder.py
    ./gdrive.py rm ska-ci/ska_builder.py

"""

import os
import logging
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import UnknownFileType, HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mimetypes

"""
Possible metadata fields:
    kind
    id
    name
    mimeType
    starred
    trashed
    explicitlyTrashed
    parents
    spaces
    version
    webContentLink
    webViewLink
    iconLink
    hasThumbnail
    thumbnailVersion
    viewedByMe
    createdTime
    modifiedTime
    modifiedByMeTime
    modifiedByMe
    owners
    lastModifyingUser
    shared
    ownedByMe
    capabilities
    viewersCanCopyContent
    copyRequiresWriterPermission
    writersCanShare
    permissions
    permissionIds
    originalFilename
    fullFileExtension
    fileExtension
    md5Checksum
    size
    quotaBytesUsed
    headRevisionId
    isAppAuthorized

"""

DRIVE = None

class InitException(Exception):
    pass


def init(interactive=True, save_credentials=False):
    global DRIVE


    default_credentials = os.path.join(os.path.expandvars('$HOME'), 'gdrive_credentials.json')
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ and os.path.exists(default_credentials):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_credentials

    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        DRIVE = build('drive', 'v3')

    if interactive and not DRIVE:
        # the following is a copy from https://developers.google.com/drive/api/v3/quickstart/python
        # see https://developers.google.com/identity/protocols/OAuth2
        SCOPES = ['https://www.googleapis.com/auth/drive',
                  'https://www.googleapis.com/auth/drive.metadata']
        creds = None
        credentials_file = os.path.join(os.environ['HOME'], '.gdrive_credentials.pkl')
        if os.path.exists(credentials_file):
            with open(credentials_file, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_config = os.path.join(os.path.dirname(__file__), 'client_config.json')
                flow = InstalledAppFlow.from_client_configs_file(client_config, SCOPES)
                creds = flow.run_local_server(authorization_prompt_message='', port=0)
            if save_credentials:
                # Save the credentials for the next run
                with open(credentials_file, 'wb') as out:
                    pickle.dump(creds, out)
        DRIVE = build('drive', 'v3', credentials=creds)

    if not DRIVE:
        msg = f"""Failed to initialize (interactive={interactive}).
        
        Authentication credentials are expected in one of these two ways:
        - a json file in $HOME/gdrive_credentials.json or pointed by the
          GOOGLE_APPLICATION_CREDENTIALS environment variable
        - interactive confirmation by navigating to a confirmation page. 
        """
        raise InitException(msg)



def get_drive_id(name):
    if name is None:
        return DRIVE.files().get(fileId='root').execute()['id']
    drives = [d for d in DRIVE.drives().list().execute()['drives'] if d['name'] == name]
    if len(drives) > 1:
        logging.warning(f'There are {len(drives)} with name {name}, returning the first one')
    if not drives:
        return None
    return drives[0]['id']


def get(file_id, fields=None):
    return DRIVE.files().get(fileId=file_id, fields=fields, supportsAllDrives=True).execute()


def get_ids(path, parent_id=None, drive=None, limit=None):
    """
    Split path and follow the parent-child relations to the end, returning the ID of the last child.

    With the following directory structure in My Drive (ids in parenthesis):
    - directory              (id_1)
      - directory_1          (id_2)
        - directory_1        (id_3)
          - directory_1      (id_4)
        - directory_2        (id_5)
      - directory_2          (id_6)

    This is the output from different calls:
    get_ids('/directory')
    ['id_1']

    get_ids('/directory/directory_1')
    ['id_2']

    get_ids('directory_1')
    ['id_2', 'id_3', 'id_4']

    get_ids('/directory/directory_1/directory_1')
    ['id_3']

    get_ids('directory_1/directory_1')
    ['id_3', 'id_4']

    get_ids('/ska3')
    []

    And with this structure in the cxc_ops shared drive:
    - ska3                     (id_1)
      - conda-test             (id_2)
      - ska3                   (id_3)

    get_ids('ska3', drive='cxc_ops')
    ['id_1', 'id_3']

    get_ids('/ska3', drive='cxc_ops')
    ['id_1']

    get_ids('/ska3/ska3', drive='cxc_ops')
    ['id_3']

    NOTES:
    - this does not handle pagination (google drive's results are actually paginated)

    :param path: str
    :param parent_id: str
    :param drive: str
    :param limit: str
    :returns: str
    """
    # assert os.path.isabs(path)
    if not path:
        return []
    folders = [p for p in path.strip('/').split('/') if p]
    root = get_drive_id(drive)
    if not folders:
        # path is ony forward slashes, so path is 'root'
        return [root]
    folder = folders[0]
    if path[0] == '/' and len(folders) == 1:
        parent_id = root

    args = {'q': f'name="{folder}"'}
    if parent_id:
        args['q'] += f' and "{parent_id}" in parents'
    if drive is not None:
        args.update({
            'corpora': 'drive',
            'includeItemsFromAllDrives': True,
            'supportsAllDrives': True,
            'driveId': get_drive_id(drive)
        })
    ids = [f['id'] for f in DRIVE.files().list(**args).execute()['files']]
    if len(folders) > 1:
        children = [get_ids('/'.join(folders[1:]), parent, drive=drive) for parent in ids]
        ids = sum(children, [])
    if limit is None:
        return ids
    elif limit == 1:
        return ids[0]
    return ids[:limit]


def ls(path, fields=('id, name, kind, version, mimeType, createdTime'
                     ', modifiedTime, headRevisionId, owners'), drive=None):
    """
    Get metadata for a given path.

    :param path: str
    :param fields: str, a comma-separated list of metadata fields.
    :param drive: str
    :returns: list of dict
    """
    res = []
    for file_id in get_ids(path, drive=drive):
        f = fields
        if 'mimeType' not in f:
            f += ', mimeType'
        metadata = DRIVE.files().get(fileId=file_id, fields=f, supportsAllDrives=True).execute()
        if metadata['mimeType'] == 'application/vnd.google-apps.folder':
            args = {'q': f'"{file_id}" in parents',
                    'fields': f'files({fields})'}
            if drive is not None:
                args.update({
                    'corpora': 'drive',
                    'includeItemsFromAllDrives': True,
                    'supportsAllDrives': True,
                    'driveId': get_drive_id(drive)
                })
            res += (DRIVE.files().list(**args).execute()['files'])
        else:
            res += ([DRIVE.files().get(fileId=file_id,
                                       fields=fields,
                                       supportsAllDrives=True).execute()])
    return res


def trash(path, drive=None):
    """
    Move file/folder to the trash.

    :param path: str
    :param drive: str
    """
    for path_id in get_ids(path, drive=drive):
        try:
            DRIVE.files().update(fileId=path_id,
                                 body={'trashed': True},
                                 supportsAllDrives=True).execute()
        except HttpError:
            raise


def delete(path, drive=None):
    """
    Remove file/folder without moving it to the trash.

    :param path: str
    :param drive: str
    """
    for path_id in get_ids(path, drive=drive):
        try:
            DRIVE.files().delete(fileId=path_id, supportsAllDrives=True).execute()
        except HttpError:
            raise


def upload(filename, destination=None, parent=None, drive=None, force=True):
    """
    Upload a file into a given folder in Google Drive.

    Strictly speaking, folders are not actual folders in Google Drive.
    The file is uploaded and its parent is set to the given folder.

    :param filename: str. Input file name.
    :param destination: str. Destination directory.
    :param drive: str
    """
    if parent is None:
        parent = get_ids(destination, drive=drive)
        if len(parent) > 1:
            raise Exception(f'Path is not unique: {destination}')
        parent = parent[0]

    filename = os.path.abspath(filename)

    if drive:
        drive_args = {
            'corpora': 'drive',
            'includeItemsFromAllDrives': True,
            'supportsAllDrives': True,
            'driveId': get_drive_id(drive)
        }
    else:
        drive_args = {}

    # check if file is there already
    q = f'"{parent}" in parents and name = "{os.path.basename(filename)}"'
    files = DRIVE.files().list(q=q, **drive_args).execute()['files']
    file_id = None
    if files:
        if files[0]['mimeType'] == 'application/vnd.google-apps.folder':
            # if it is there and is a directory, use it
            file_id = files[0]['id']
        else:
            if force:
                # it is there and is a file, remove it
                for file in files:
                    trash(file['id'])
            else:
                file_id = files[0]['id']

    # create if not there
    if file_id is None:
        metadata = {'name': os.path.basename(filename),
                    'parents': [parent]}
        if os.path.isdir(filename):
            metadata['mimeType'] = 'application/vnd.google-apps.folder'
            file_id = DRIVE.files().create(body=metadata,
                                           media_body=None,
                                           fields='id',
                                           supportsAllDrives=True).execute()['id']
        else:
            file_type, _ = mimetypes.guess_type(filename)
            mime_type = file_type if file_type else 'application/octet-stream'
            media = MediaFileUpload(filename, mimetype=mime_type)
            file_id = DRIVE.files().create(body=metadata,
                                           media_body=media,
                                           fields='id',
                                           supportsAllDrives=True).execute()
    return file_id


def upload_recursive(filename, destination, drive=None, force=False):
    """
    Upload a file to a given folder in Google Drive.

    If argument is a directory, traverse the tree, uploading everything
    while keeping the hierarchy. This removes and replaces existing files.

    :param filename: str. Input file name.
    :param destination: Destination directory.
    :param drive: str
    :param force: str
    :return:
    """
    filename = os.path.abspath(filename)
    file_id = {filename: upload(filename, destination, drive=drive, force=force)}
    destinations = {filename: os.path.join(destination, os.path.basename(filename))}
    logging.info(f'{filename} -> {destination}')

    # traverse the tree
    for root, d_names, f_names in os.walk(filename,
                                          topdown=True, onerror=None, followlinks=False):
        parent = file_id[root]  # its is already there by construction
        for directory in d_names:
            name = os.path.join(root, directory)
            file_id[name] = upload(name, parent=parent, drive=drive, force=force)
            destinations[name] = os.path.join(destinations[root], directory)
            logging.info(f'{name} -> {destinations[root]}')

        for filename in f_names:
            name = os.path.join(root, filename)
            file_id[name] = upload(name, parent=parent, drive=drive, force=force)
            destinations[name] = os.path.join(destinations[root], filename)
            logging.info(f'{name} -> {destinations[root]}')


def _walk(path=None, file_id=None, fields='', drive=None, max_depth=None, _depth=0):
    """
    Generator to descend on a directory hierarchy starting at a given path.

    :param path: str
        If it is not provided, file_id must be provided
    :param file_id: str
        If not provided, it is found from path
    :param fields: str
        comma-separated list of fields to return in dictionary
    :param drive: str
        name of shareddrive
    :param max_depth: int
        maximum number of levels to descend on the hierarchy
    :param _depth: int
        Private. Do not use. It is used in recursive calls.
    :yields: dict
    """
    if max_depth is not None and _depth > max_depth:
        return

    # path is only set at the top-level call, all recursive calls use file_id
    if file_id is None:
        ids = get_ids(path, drive=drive)
        if len(ids) > 1:
            raise Exception(f'{path} is not a unique path')
        if not ids:
            return
        file_id = ids[0]

    if drive:
        drive_args = {
            'corpora': 'drive',
            'includeItemsFromAllDrives': True,
            'supportsAllDrives': True,
            'driveId': get_drive_id(drive)
        }
    else:
        drive_args = {}

    # fields passed to the drive API should not include our own custom fields
    # and should include at least the file name and ID.
    _fields = list(set([f.strip() for f in fields.split(',') if f]))
    _fields = [field for field in _fields + ['id', 'name'] if field not in ['path', 'depth']]
    metadata = DRIVE.files().get(fileId=file_id,
                                 fields=','.join(_fields),
                                 supportsAllDrives=True).execute()
    metadata['depth'] = _depth
    metadata['path'] = path if path else metadata['name']

    # this needs to be copied, because it can be modified in the outer scope (loop below)
    yield metadata.copy()

    children = DRIVE.files().list(q=f'"{file_id}" in parents', **drive_args).execute()['files']
    for child in children:
        for node in _walk(file_id=child['id'], fields=fields, drive=drive, max_depth=max_depth,
                         _depth=_depth + 1):
            node['path'] = os.path.join(metadata['path'], node['path'])
            yield node


def walk(path=None, fields='', drive=None, max_depth=None):
    """
    Generator to descend on a directory hierarchy starting at a given path.

    With this hierarchy:
    - gdrive-test
      - directory
        - directory
          - directory_2
        - file_3
      - file
      - file_1
      - file_2

    One gets this:
    for path, in gdrive.walk('gdrive-test', fields='path'):
        print(path)
     gdrive-test
     gdrive-test/file_2
     gdrive-test/file_1
     gdrive-test/file
     gdrive-test/directory
     gdrive-test/directory/file_3
     gdrive-test/directory/directory
     gdrive-test/directory/directory/directory_2

    :param path: str
        path where to start on Google drive
    :param fields: str
        comma-separated list of fields
    :param drive: str (optional)
        name of shared drive
    :param max_depth: int
        maximum number of levels to descend on the hierarchy
    :yields: tuple
        a tuple corresponding to the fields argument
    """
    field_list = [f.strip() for f in fields.split(',') if f]
    for node in _walk(path=path, fields=fields, drive=drive, max_depth=max_depth):
        yield tuple([node[field] for field in field_list])


def download(path, destination=None, drive=None):
    """
    Download a file and save it into a file.

    :param path: str
    :param filename: str, optional. Destination file name.
    :param drive: str
    :returns: dict
    """
    result = []
    if destination is None:
        destination = os.path.basename(path)
    for file_id, filename, mime_type in walk('gdrive-test', fields='id,path,mimeType'):
        if mime_type == 'application/vnd.google-apps.folder':
            directory = os.path.join(destination, filename)
            os.makedirs(directory, exist_ok=True)
        else:
            link = ls(filename, fields='webContentLink', drive=drive)[0]['webContentLink']
            filename = os.path.join(destination, *filename.split('/'))
            res, data = DRIVE._http.request(link)
            with open(filename, 'wb') as out:
                out.write(data)
            result.append(res)
    return result

def main():
    actions = ['ls', 'rm', 'delete', 'upload', 'download', 'id']
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', choices=actions)
    parser.add_argument('path', nargs='*')
    parser.add_argument('--drive', default=None)
    parser.add_argument('--batch', dest='interactive', action='store_false')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--save-credentials', action='store_true')
    args = parser.parse_args()

    try:
        init(interactive=args.interactive, save_credentials=args.save_credentials)
    except InitException as e:
        print(e)
        parser.print_usage()
        parser.exit(1)
    logging.basicConfig()

    if args.cmd == 'ls':
        if not args.path:
            args.path = '/'
        for d in args.path:
            print(d)
            print('  ' + '\n  '.join([f['name'] for f in ls(d, drive=args.drive)]))
    elif args.cmd == 'rm':
        for d in args.path:
            rm(d, drive=args.drive)
    elif args.cmd == 'delete':
        for d in args.path:
            delete(d, drive=args.drive)
    elif args.cmd == 'upload':
        for file in args.path[:-1]:
            if os.path.exists(file):
                upload_recursive(file, args.path[-1], drive=args.drive)
            else:
                print(f'no such file {file}')
    elif args.cmd == 'download':
        for f in args.path:
            download(f, drive=args.drive)
    elif args.cmd == 'id':
        for f in args.path:
            print(get_ids(f, drive=args.drive))


if __name__ == '__main__':
    main()
