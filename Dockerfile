ARG IMAGE="tarantool/tarantool"
ARG VERSION="latest"

FROM ${IMAGE}:${VERSION}

ENV WORK_DIR="/opt/tarantool"
ENV DEBIAN_FRONTEND="noninteractive"
ENV TZ="Europe/Moscow"

WORKDIR ${WORK_DIR}

ARG OS_NAME="docker"

COPY prepare/${OS_NAME}.sh prepare.sh
RUN chmod +x prepare.sh
RUN ./prepare.sh

ARG BUILD_NAME="latest"

COPY install/${OS_NAME}_${BUILD_NAME}.sh install.sh
RUN chmod +x install.sh
RUN ./install.sh

ARG VERSION
ENV RESULTS_DIR="${WORK_DIR}/results"
ENV RESULTS_FILE="${RESULTS_DIR}/${OS_NAME}_${VERSION}_${BUILD_NAME}.json"

RUN mkdir -p ${RESULTS_DIR}

EXPOSE 3301
COPY init.lua init.lua
CMD tarantool init.lua
