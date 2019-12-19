FROM astj/centos5-vault:latest

RUN yum -y install gcc gcc-c++ gcc-gfortran \
                   perl \
                   curl \
                   sudo \
                   bzip2 \
                   nano \
                   emacs \
                   openssh-server \
                   openssh-clients \
                   mesa-libGL


RUN useradd -ms /bin/bash ska
RUN echo "ska:ska" | chpasswd && \
    usermod -aG wheel ska && \
    echo "%wheel        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers

USER ska
ENV PS1=' \u \w>'
WORKDIR /home/ska

COPY --chown=ska:ska files/condarc /home/ska/.condarc
ENV PATH="/home/ska/miniconda3/bin:$PATH"
RUN curl -O https://repo.continuum.io/miniconda/Miniconda3-4.3.21-Linux-x86_64.sh && \
    bash Miniconda3-4.3.21-Linux-x86_64.sh -b && \
    rm Miniconda3-4.3.21-Linux-x86_64.sh


RUN conda install --yes python=3.6.2 conda=4.3.21 && \
    conda install --yes ska3_builder

RUN conda install --yes pytables \
                        matplotlib \
                        Cython \
                        numexpr \
                        numba

RUN conda create -n ska3-flight && \
    source activate ska3-flight && \
    conda install --yes ska3-flight && \
    source deactivate

RUN git clone --single-branch --branch docker https://github.com/sot/skare3.git

#RUN dbus-uuidgen --ensure=/etc/machine-id


ENTRYPOINT ["bash"]
