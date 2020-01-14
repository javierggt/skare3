#!/usr/bin/env bash

echo setting credentials at $GOOGLE_APPLICATION_CREDENTIALS
echo "${GOOGLE_DRIVE_CREDENTIALS}" > $GOOGLE_APPLICATION_CREDENTIALS
echo uploading: $@
/home/ska/bin/gdrive.py upload $@
