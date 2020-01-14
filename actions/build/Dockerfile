FROM astj/centos5-vault:latest

RUN yum -y install gcc \
                   perl \
                   curl \
                   sudo \
                   bzip2 \
                   nano \
                   emacs \
                   openssh-server \
                   openssh-clients

# this user ID matches github's VM user uid.
RUN useradd -ms /bin/bash ska -u 1001
RUN echo "ska:ska" | chpasswd && usermod -aG wheel ska && echo "%wheel        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers && echo "Defaults:ska        !requiretty" >> /etc/sudoers

USER ska
ENV PS1=' \u \w>'
WORKDIR /home/ska

COPY --chown=ska:ska files/condarc /home/ska/.condarc
COPY --chown=ska:ska files/git_pass.py /home/ska/git_pass.py
ENV GIT_ASKPASS="/home/ska/git_pass.py"
ENV PATH="/home/ska/miniconda3/bin:$PATH"
RUN curl -O https://repo.continuum.io/miniconda/Miniconda3-4.3.21-Linux-x86_64.sh && \
    bash Miniconda3-4.3.21-Linux-x86_64.sh -b && \
    rm Miniconda3-4.3.21-Linux-x86_64.sh && \
    conda install python=3.6.2 conda=4.3.21 -q --yes

RUN conda install -q --yes ska3_builder

RUN git clone --single-branch --branch scm_version https://github.com/sot/skare3.git

COPY files/build.sh /home/ska/build-pkg.sh
COPY files/gdrive.py /home/ska/gdrive.py

ENTRYPOINT ["/home/ska/build-pkg.sh"]
