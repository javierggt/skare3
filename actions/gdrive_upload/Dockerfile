FROM ubuntu:latest

RUN apt-get update && \
    apt-get install python3 python3-pip -y && \
    pip3 install google-api-python-client

# this user ID matches github's VM user uid.
RUN useradd -ms /bin/bash ska -u 1001
USER ska
WORKDIR /home/ska


# Add two scripts, because the process is split in two steps:
#   1. set the credentials from secret
#   2. do the actual upload
COPY --chown=ska:ska upload.sh /home/ska/bin/upload.sh
RUN chmod +x /home/ska/bin/upload.sh
COPY --chown=ska:ska gdrive.py /home/ska/bin/gdrive.py
RUN chmod +x /home/ska/bin/gdrive.py

ENV GOOGLE_APPLICATION_CREDENTIALS="/github/workspace/gdrive_credentials.json"

ENTRYPOINT ["/home/ska/bin/upload.sh"]