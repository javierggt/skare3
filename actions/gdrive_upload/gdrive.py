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


import os
from googleapiclient.discovery import build
from googleapiclient.errors import UnknownFileType
import mimetypes


if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.path.expandvars('$HOME'),
                                                                'gdrive_credentials.json')
if not os.path.exists(os.environ['GOOGLE_APPLICATION_CREDENTIALS']):
    raise Exception(f"Expected credentials at {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")


DRIVE = build('drive', 'v3')


def get_id(path):
    """
    Split path and follow the parent-child relations to the end, returning the ID of the last child.

    :param path: str
    :returns: str
    """
    # assert os.path.isabs(path)
    folders = path.split('/')
    folder = folders[0]
    gfolder = DRIVE.files().list(q=f'name="{folder}"').execute()
    if not gfolder['files']:
        raise Exception(f'"{folder}" folder not found.')
    if len(gfolder['files']) > 1:
        raise Exception(f'More than one {folder} folder found.')
    gfolder = gfolder['files'][0]['id']
    for i, child in enumerate(folders[1:]):
        gchild = DRIVE.files().list(q=f'"{gfolder}" in parents and name="{child}"').execute()
        if not gchild['files']:
            raise Exception(f'"{child}" folder not found.')
        if i < len(folders) - 2 and len(gchild['files']) > 1:
            raise Exception(f'More than one {child} folder under {folder} found.')
        gfolder = gchild['files'][0]['id']
        folder = child
    return gfolder


def ls(path, fields=('id, name, kind, version, mimeType, createdTime'
                     ', modifiedTime, headRevisionId, owners')):
    """
    Get metadata for a given path.

    :param path: str
    :param fields: str, a comma-separated list of metadata fields.
    :returns: list of dict
    """
    folder = get_id(path)
    f = fields
    if 'mimeType' not in f:
        f += ', mimeType'
    metadata = DRIVE.files().get(fileId=folder, fields=f).execute()
    if metadata['mimeType'] == 'application/vnd.google-apps.folder':
        res = DRIVE.files().list(q=f'"{folder}" in parents',
                                 fields=f'files({fields})').execute()['files']
    else:
        res = [DRIVE.files().get(fileId=folder, fields=fields).execute()]
    return res


def rm(path):
    """
    Remove file/folder without moving it to the trash (how does one move it to the trash? BTW).

    :param path: str
    """
    DRIVE.files().delete(fileId=get_id(path)).execute()


def upload(filename, path):
    """
    Upload a file to a given folder in Google Drive.

    Strictly speaking, folders are not actual folders in Google Drive.
    The file is uploaded and its parent is set to the given folder.

    :param filename: str. Input file name.
    :param path: str. Destination directory.
    """
    metadata = {'name': os.path.basename(filename),
                'parents': [get_id(path)]}
    if os.path.isdir(filename):
        metadata['mimeType'] = 'application/vnd.google-apps.folder'

    media_body = None if os.path.isdir(filename) else filename
    return DRIVE.files().create(body=metadata, media_body=media_body, fields='id').execute()


def upload_recursive(filename, destination):
    """
    Upload a file to a given folder in Google Drive.

    If argument is a directory, traverse the tree, uploading everything
    while keeping the hierarchy. This removes and replaces existing files.

    :param filename: str. Input file name.
    :param destination: Destination directory.
    :return:
    """
    parent = get_id(destination)
    filename = os.path.abspath(filename)
    file_id = {}

    # check if file is there already
    q = f'"{parent}" in parents and name = "{os.path.basename(filename)}"'
    files = DRIVE.files().list(q=q).execute()['files']
    if files:
        if files[0]['mimeType'] == 'application/vnd.google-apps.folder':
            # if it is there and is a directory, use this id
            file_id[filename] = files[0]['id']
        else:
            # if it is there and is a file, remove it
            for file in files:
                DRIVE.files().delete(fileId=file['id']).execute()

    if filename not in file_id:
        metadata = {'name': os.path.basename(filename),
                    'parents': [parent]}
        if os.path.isdir(filename):
            metadata['mimeType'] = 'application/vnd.google-apps.folder'
        file_id = {filename: DRIVE.files().create(body=metadata, fields='id').execute()['id']}

    # traverse the tree
    for root, d_names, f_names in os.walk(filename,
                                          topdown=True, onerror=None, followlinks=False):
        parent = file_id[root]  # its is already there by construction

        for dir in d_names:
            # check if directory is there already
            files = DRIVE.files().\
                list(q=f'"{parent}" in parents and name = "{dir}"').execute()['files']
            if files:
                # if it is, use it
                file_id[os.path.join(root, dir)] = files[0]['id']
            else:
                # otherwise create it
                metadata = {'name': dir, 'parents': [file_id[root]],
                            'mimeType': 'application/vnd.google-apps.folder'}
                file_id[os.path.join(root, dir)] = DRIVE.files(). \
                    create(body=metadata, media_body=None, fields='id').execute()['id']

        for filename in f_names:
            # check if file is there already
            files = DRIVE.files(). \
                list(q=f'"{parent}" in parents and name = "{filename}"').execute()['files']
            if files:
                # if it is, remove it
                for file in files:
                    DRIVE.files().delete(fileId=file['id']).execute()
            try:
                # now create it
                metadata = {'name': filename,
                            'parents': [parent]}
                file_id[os.path.join(root, filename)] = \
                    DRIVE.files().create(body=metadata,
                                         media_body=os.path.join(root, filename),
                                         fields='id').execute()
            except UnknownFileType as e:
                # maybe we can be better at determining the type
                print(f'{filename} failed to upload (unknown file type)')


def download(path, filename=None):
    """
    Download a file and save it into a file.

    :param path: str
    :param filename: str, optional. Destination file name.
    :returns: dict
    """
    if filename is None:
        filename = os.path.basename(path)
    link = ls(path, fields='webContentLink')[0]['webContentLink']
    res, data = DRIVE._http.request(link)
    with open(filename, 'wb') as out:
        out.write(data)
    return res


if __name__ == '__main__':
    actions = ['ls', 'rm', 'upload', 'download']
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', choices=actions, nargs='?')
    args, argv = parser.parse_known_args()
    if args.cmd == 'ls':
        for d in argv:
            print('\n'.join([f['name'] for f in ls(d)]))
    elif args.cmd == 'rm':
        for d in argv:
            rm(d)
    elif args.cmd == 'upload':
        for file in argv[:-1]:
            if os.path.exists(file):
                upload_recursive(file, argv[-1])
            else:
                print(f'no such file {file}')
    elif args.cmd == 'download':
        for f in argv:
            download(f)
