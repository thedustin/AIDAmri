FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

ENV VERSION_NIFTYREG=83d8d1182ed4c227ce4764f1fdab3b1797eecd8d \
    VERSION_DSI_STUDIO=2022.08.03 \
    VERSION_FSL=5.0.11 \
    \
    VIRTUAL_ENV=/opt/env \
    PATH="$VIRTUAL_ENV/bin:$PATH" \
    \
    DIR_FSL=/usr/local/fsl \
    PATH=${DIR_FSL}/bin:${PATH} \
    FSLOUTPUTTYPE=NIFTI_GZ \
    \
    NIFTYREG_INSTALL=/aida/NiftyReg/niftyreg_source/niftyreg_install \
    PATH=${PATH}:${NIFTYREG_INSTALL}/bin \
    LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${NIFTYREG_INSTALL}/lib

# ubuntu environment setup
RUN apt-get update -y && apt-get install -y \
        build-essential \
        ca-certificates \
        checkinstall \
        dc \
        ffmpeg \
        gpg \
        git \
        libsm6 \
        libssl-dev \
        libxext6 \
        python3 \
        python3-pip \
        python3-venv \
        python3-wheel \
        unzip \
        wget \
        zlib1g-dev \
    \
    && wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null \
    && echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ bionic main' | tee /etc/apt/sources.list.d/kitware.list >/dev/null \
    && apt-get update -y && apt-get install -y \
        cmake \
    \
    && apt -y autoremove && apt clean && apt autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# create and switch to working directory
WORKDIR /aida/

# Python setup
RUN python3 -m pip install --user --upgrade pip \
    && python3 -m venv $VIRTUAL_ENV \
    && python3 -m pip install --upgrade setuptools \
    && python3 -m pip install wheel \
    && python3 -m pip install --upgrade pip

COPY requirements.txt requirements.txt

RUN python3 -m pip install -r requirements.txt

# installation of FSL 5.0.11 with modified installer 
# (disabling interactive allocation query)
COPY fslinstaller_mod.py ./

RUN python3 fslinstaller_mod.py -V ${VERSION_FSL} \
    && . ${DIR_FSL}/etc/fslconf/fsl.sh

# Niftyreg preparation and installation
WORKDIR /aida/NiftyReg/

RUN git clone https://github.com/KCL-BMEIS/niftyreg niftyreg_source  &&\
    cd niftyreg_source &&\
    git reset --hard ${VERSION_NIFTYREG} &&\
     	mkdir niftyreg_install niftyreg_build && cd .. &&\
     	cmake niftyreg_source &&\
     	cmake -D CMAKE_BUILD_TYPE=Release niftyreg_source &&\
     	cmake -D CMAKE_INSTALL_PREFIX=niftyreg_source/niftyreg_build niftyreg_source &&\
     	cmake -D CMAKE_C_COMPILER=/usr/bin/gcc-7 niftyreg_source &&\
     	make && make install

WORKDIR /aida

# download DSI studio
RUN wget https://github.com/frankyeh/DSI-Studio/releases/download/${VERSION_DSI_STUDIO}/dsi_studio_ubuntu1804.zip \
    && unzip dsi_studio_ubuntu1804.zip -d dsi_studio_ubuntu1804 \
    && rm dsi_studio_ubuntu1804.zip

# copy bin/ and lib/ from AIDAmri into image
COPY bin/ bin/
COPY lib/ lib/

RUN echo "/aida/bin/dsi_studio_ubuntu_1804/dsi-studio/dsi_studio" > bin/3.2_DTIConnectivity/dsi_studioPath.txt
