#!/bin/sh

usage() {
    echo "Usage: ./run_testing.sh [options]"
    echo "Options:"
    echo "    -h, --help        Show this help message"
    echo "    -i, --image       Docker image name of base system (default: tarantool/tarantool)"
    echo "    -v, --version     Version of docker image (default: latest)"
    echo "    -s, --os          Name of OS (default: <image>)"
    echo "    -b, --build       Name of tarantool build (default: latest)"
    echo "    -n, --name        Name of docker container (default: tnt_builder)"
}

image="tarantool/tarantool"
version="latest"
os=""
build="latest"
name="tnt_builder"

while [ "${1}" != "" ]; do
    case "${1}" in
    -h | --help)
        usage
        exit
        ;;
    -i | --image)
        image="${2}"
        shift
        shift
        ;;
    -v | --version)
        version="${2}"
        shift
        shift
        ;;
    -s | --os)
        os="${2}"
        shift
        shift
        ;;
    -b | --build)
        build="${2}"
        shift
        shift
        ;;
    -n | --name)
        name="${2}"
        shift
        shift
        ;;
    *)
        echo "Unknown parameter '${1}'"
        usage
        exit 1
        ;;
    esac
done

if [ -z "${os}" ]; then
    os="$(basename "${image}")"
    if [ "${os}" = "tarantool" ]; then
        os="docker"
    fi
fi

docker rm -f "${name}"
docker build \
    --build-arg IMAGE=${image} \
    --build-arg VERSION=${version} \
    --build-arg OS_NAME=${os} \
    --build-arg BUILD_NAME=${build} \
    -t "${name}" . && \
docker run -d -p 3301:3301 --name "${name}" -v "$(pwd)/results":/opt/tarantool/results "${name}"
