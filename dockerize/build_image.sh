#!/bin/bash

PKGS_FILE=$1
source ${PKGS_FILE}

UBUNTU_IMAGE=ubuntu
UBUNTU_TAG=trusty
DOCKER_IMAGE_TAG=${USER}_${DOCKER_IMAGE_BASE_TAG}

SUDO_CMD='sudo'

for grp in `groups`; do
    if [ "$grp" == "root" -o "$grp" == "docker" ]; then
        SUDO_CMD=''
    fi
done

# temp dir and file for dockerfile
TEMP_DIR=/tmp/pure_tools_docker_tmp_dir
if [ ! -e ${TEMP_DIR} ]; then
    mkdir ${TEMP_DIR}
fi
rm -rf ${TEMP_DIR}/*
TEMP_DOCKFILE=${TEMP_DIR}/Dockerfile

check_docker_service()
{
    # check docker service status
    ${SUDO_CMD} systemctl status docker.service 2>&1 | grep -q running
    if [ $? -ne 0 ]; then
        echo "Failed: docker service is not running"
        exit 1 
    fi
}

check_existing_user_image()
{
    # search for the image by DOCKER_IMAGE:DOCKER_IMAGE_TAG
    ${SUDO_CMD} docker images | grep -q ${DOCKER_IMAGE_TAG}
    if [ $? -eq 0 ]; then
        echo "Found the available docker images"
        exit 0
    fi
}

# Not found the correct runtest images
check_existing_base_image()
{
    # search for the base image
    ${SUDO_CMD} docker images | grep -q ${DOCKER_IMAGE_BASE_TAG}
    if [ $? -eq 0 ]; then
        echo "Found the available docker base images, starting to build the runtests docker image"
        build_user_image
        exit 0
    fi
}

clean_old_images()
{
    # search for all the out-of-date images
    imgs=`${SUDO_CMD} docker images | grep ${DOCKER_IMAGE} | grep -v ${DOCKER_IMAGE_BASE_TAG}`
    if [ ! "$imgs" ]; then
        return
    fi
    imgs=`echo "$imgs" | awk '{print $1":"$2}'`

    # clean up the out-of-date images
    ${SUDO_CMD} docker rmi -f $imgs
}


build_base_image()
{
    if [ -e ${TEMP_DOCKFILE} ]; then
        rm -f ${TEMP_DOCKFILE}
    fi
    ${SUDO_CMD} docker pull ${UBUNTU_IMAGE}:${UBUNTU_TAG}
    # generate the base image dockerfile
    echo "FROM ${UBUNTU_IMAGE}:${UBUNTU_TAG}" >> ${TEMP_DOCKFILE}
#    echo "RUN mkdir /etc/apt/sources.list.d 2>/dev/null || true" >> ${TEMP_DOCKFILE}
#    echo 'RUN echo "deb [arch=amd64] http://repo-trusty.dev.purestorage.com trusty main" > /etc/apt/sources.list.d/pure_internal.list' >> ${TEMP_DOCKFILE}
    echo "RUN apt-get update && apt-get install -y ${APT_PACKAGES}" >> ${TEMP_DOCKFILE}
    echo "RUN apt-get install -y --allow-unauthenticated libre2-dev || true" >> ${TEMP_DOCKFILE}
    # build the base image
    ${SUDO_CMD} docker build -t ${DOCKER_IMAGE}:${DOCKER_IMAGE_BASE_TAG} -f ${TEMP_DOCKFILE} ${TEMP_DIR}
}


build_user_image()
{
    if [ -e ${TEMP_DOCKFILE} ]; then
        rm -f ${TEMP_DOCKFILE}
    fi

    # generate the user image dockerfile
    echo "FROM ${DOCKER_IMAGE}:${DOCKER_IMAGE_BASE_TAG}" >> ${TEMP_DOCKFILE}
    if [ "$USER" != "root" ]; then
        echo "RUN groupadd -f -g ${GROUP_ID} $GROUP && useradd -s /bin/bash -m -u ${USER_ID} -g ${GROUP_ID} $USER && usermod -aG root $USER && usermod -aG sudo $USER" >> ${TEMP_DOCKFILE}
    fi
    echo "USER $USER" >> ${TEMP_DOCKFILE}
    pip_install_option=""
    if [ "$USER" != "root" ]; then
        pip_install_option="--user"
    fi
    echo "RUN python2 -m pip install ${pip_install_option} --upgrade pip setuptools" >> ${TEMP_DOCKFILE}
    echo "RUN python2 -m pip install ${pip_install_option} --ignore-installed ${PIP_PACKAGES}" >> ${TEMP_DOCKFILE}
    if [ "$USER" != "root" ]; then
        echo "ENV PATH /home/${USER}/.local/bin:\$PATH" >> ${TEMP_DOCKFILE}
    fi
    # build the user image
    ${SUDO_CMD} docker build -t ${DOCKER_IMAGE}:${DOCKER_IMAGE_TAG} -f ${TEMP_DOCKFILE} ${TEMP_DIR}
}

main()
{
    check_docker_service
    build_base_image
    build_user_image
    clean_old_images

    rm -f ${TEMP_DOCKFILE}
}

main

