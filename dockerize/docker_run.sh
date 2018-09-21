#!/bin/bash

function cleanup {
    echo "cleanup the runtests"
    ${SUDO_CMD} docker stop runtests-$$
    exit 1
}
trap cleanup SIGTERM SIGINT

PKGS_FILE=$1
source ${PKGS_FILE}

WORK_DIR=$(pwd)
PURE_TOOLS_REPO_DIR=$(dirname "$(pwd)")

if [ ! -e ${PURE_TOOLS_REPO_DIR} ]; then
    echo "Can't find the git repo: ${PURE_TOOLS_REPO_DIR}"
    echo "Please make sure it successfuly checked out!"
    exit 1
fi

SUDO_CMD='sudo'
for grp in `groups`; do
    if [ "$grp" == "root" -o "$grp" == "docker" ]; then
        SUDO_CMD=''
    fi
done

${SUDO_CMD} docker run \
        --name=runtests-$$ \
        --rm=true \
        --net=host \
        -v ${PURE_TOOLS_REPO_DIR}:${PURE_TOOLS_REPO_DIR}:rw \
        -w ${WORK_DIR} \
        --privileged=true \
        -e PYTHONPATH=${PYTHONPATH_CONTAINER} \
        ${DOCKER_IMAGE}:${DOCKER_IMAGE_TAG} \
        ${CMDS_IN_CONTAINER} \ &
        
wait $!