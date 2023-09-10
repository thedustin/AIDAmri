#!/usr/bin/env bash

# unoffical bash strict mode
# see http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

# Some default constants
readonly DOCKER_REGISTRY=ghcr.io
readonly DOCKER_IMAGE_NAME=Aswendt-Lab/AIDAmri

readonly DEFAULT_DOCKER_CONTAINER_NAME=aidamri
readonly DEFAULT_DOCKER_IMAGE_NAME=${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}
readonly DEFAULT_DOCKER_IMAGE_TAG=latest

# Define default values for options
OPT_DOCKER_ATTACH=0
OPT_DOCKER_BUILD=0
OPT_SHOW_USAGE=0
OPT_DEBUG=0
OPT_DOCKER_CONTAINER_NAME=$DEFAULT_DOCKER_CONTAINER_NAME
OPT_DOCKER_IMAGE_NAME=$DEFAULT_DOCKER_IMAGE_NAME
OPT_DOCKER_IMAGE_TAG=$DEFAULT_DOCKER_IMAGE_TAG

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "  -a, --attach            Attach (log into) the container after starting it."
    echo "  -b, --build=[name]      Build the image before starting the container."
    echo "                          You can optionally specify an image name, otherwise"
    echo "                          the default image name \"${DEFAULT_DOCKER_IMAGE_NAME}\" will be used."
    echo "  -c, --container=[name]  Use the given name as the name for the container."
    echo "  -d, --debug             Enable the debug mode for the script."
    echo "  -t, --tag=[name]        Use the given name as the image tag to use."
    echo "  -h, --help              Display this help message."

    if [ $OPT_DEBUG -eq 0 ]; then
        return
    fi

    echo ""
    echo "Given options:"
    echo "  -a, --attach    = ${OPT_DOCKER_ATTACH}"
    echo "  -b, --build     = ${OPT_DOCKER_BUILD} (${OPT_DOCKER_IMAGE_NAME})"
    echo "  -c, --container = ${OPT_DOCKER_CONTAINER_NAME}"
    echo "  -d, --debug     = ${OPT_DEBUG}"
    echo "  -t, --tag       = ${OPT_DOCKER_IMAGE_TAG}"
    echo "  -h, --help      = ${OPT_SHOW_USAGE}"
}

# returns how many positions needs to be shifted
long_opt() {
    local val=$1
    local next_val=$2
    shift 2

    if [[ "$val" =~ "=" ]]; then
        while [[ $# -gt 0 ]]; do
            val=${val#"${1}"}

            shift
        done

        echo "$val"
        return 0
    fi

    if [ -n "$next_val" ] && [ "${next_val:0:1}" != "-" ]; then
        echo "$next_val"
        return 1
    fi
}

while [[ $# -gt 0 ]]; do
    # disable exit on error for the long_opt function
    set +e

    case $1 in
    -a | --attach)
        OPT_DOCKER_ATTACH=1
        shift # past option name
        ;;
    -b | --build | -b=* | --build=*)
        OPT_DOCKER_BUILD=1

        opt=$(long_opt "$1" "$2" "-b=" "--build=")
        shift $(($? + 1)) # past option name + value (if any)

        if [[ -n "$opt" ]]; then
            OPT_DOCKER_IMAGE_NAME=$opt
        fi
        ;;
    -c | --container | -c=* | --container=*)
        opt=$(long_opt "$1" "$2" "-c=" "--container=")
        shift $(($? + 1)) # past option name + value (if any)

        if [[ -z "$opt" ]]; then
            echo "Missing value for option $1" >&2
            usage >&2
            exit 1
        fi

        OPT_DOCKER_CONTAINER_NAME=$opt
        ;;
    -d | --debug)
        OPT_DEBUG=1
        shift # past option name
        ;;
    -h | --help)
        OPT_SHOW_USAGE=1
        shift # past option name
        ;;
    -t | --tag | -t=* | --tag=*)
        opt=$(long_opt "$1" "$2" "-t=" "--tag=")
        shift $(($? + 1)) # past option name + value (if any)

        if [[ -z "$opt" ]]; then
            echo "Missing value for option $1" >&2
            usage >&2
            exit 1
        fi

        OPT_DOCKER_IMAGE_TAG=$opt
        ;;
    -* | --*)
        echo "Unknown option $1" >&2
        usage >&2
        exit 1
        ;;
    *)
        echo "Unknown argument $1" >&2
        usage >&2
        exit 1
        ;;
    esac

    set -e
done

if [ $OPT_SHOW_USAGE -gt 0 ]; then
    usage
    exit
fi

if [ $OPT_DOCKER_BUILD -gt 0 ]; then
    docker build \
        --progress=plain \
        --tag="${OPT_DOCKER_IMAGE_NAME}:${OPT_DOCKER_IMAGE_TAG}" \
        .
fi

docker run \
    --detach \
    --interactive \
    --mount "type=bind,source=$(pwd),target=/aida/mountdata" \
    --name "${OPT_DOCKER_CONTAINER_NAME}" \
    --rm \
    --tty \
    "${OPT_DOCKER_IMAGE_NAME}:${OPT_DOCKER_IMAGE_TAG}"

if [ $OPT_DOCKER_ATTACH -gt 0 ]; then
    docker attach "${OPT_DOCKER_CONTAINER_NAME}"
fi
