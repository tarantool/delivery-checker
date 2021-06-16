#!/usr/bin/env bash

set -e

if ! grep -q '"telegram_token"' "config.json"; then
    echo "You don't have 'telegram_token' in configuration, please add it before using the service."
    exit 0
fi

SERVICES_DIR="telegram_bot/service_files/"
COMMAND="${1}"

if [ "$(uname -s)" = "Linux" ]; then
    SRV_NAME="delivery_checker_tg_bot"
    SERVICE_FILE="${SERVICES_DIR}/${SRV_NAME}.service"
    TMP_SERVICE_FILE="/tmp/${SRV_NAME}.service"

    if [ "${COMMAND}" = "install" ]; then
        if [ -f "/etc/systemd/system/${SRV_NAME}.service" ]; then
            echo "The service is already installed!"
            exit 0
        fi

        awk """{gsub(/WORK_DIR/, \"$(pwd)\")}1""" "${SERVICE_FILE}" >"${TMP_SERVICE_FILE}"

        echo "Installing '${SRV_NAME}' service"
        sudo mv "${TMP_SERVICE_FILE}" "/etc/systemd/system/${SRV_NAME}.service"
        sudo systemctl daemon-reload

        echo "Starting '${SRV_NAME}' service"
        sudo systemctl start ${SRV_NAME}
        sudo systemctl enable ${SRV_NAME}

    elif [ "${COMMAND}" = "uninstall" ]; then
        if [ ! -f "/etc/systemd/system/${SRV_NAME}.service" ]; then
            echo "The service is already uninstalled!"
            exit 0
        fi

        echo "Stopping '${SRV_NAME}' service"
        sudo systemctl stop ${SRV_NAME}
        sudo systemctl disable ${SRV_NAME}

        echo "Uninstalling '${SRV_NAME}' service"
        sudo rm -f "/etc/systemd/system/${SRV_NAME}.service"
        sudo systemctl daemon-reload

    else
        if [ ! -f "/etc/systemd/system/${SRV_NAME}.service" ]; then
            echo "The service not installed!"
            exit 1
        fi

        echo "Service '${SRV_NAME}' ${COMMAND}ing"
        sudo systemctl "${COMMAND}" ${SRV_NAME}
    fi
fi

if [ "$(uname -s)" = "Darwin" ]; then
    SRV_NAME="tg-bot.tarantool-delivery-checker.mac-mini"
    SERVICE_FILE="${SERVICES_DIR}/${SRV_NAME}.plist"
    TMP_SERVICE_FILE="/tmp/${SRV_NAME}.plist"

    LAUNCH_DIR="${HOME}/Library/LaunchAgents"
    LOG_DIR="${HOME}/Library/Logs"

    if [ "${COMMAND}" = "install" ]; then
        if [ -f "${LAUNCH_DIR}/${SRV_NAME}.plist" ]; then
            echo "The service is already installed!"
            exit 0
        fi

        awk """{gsub(/WORK_DIR/, \"$(pwd)\")}1""" "${SERVICE_FILE}" >"${TMP_SERVICE_FILE}.1"
        awk """{gsub(/HOME_DIR/, \"${HOME}\")}1""" "${TMP_SERVICE_FILE}.1" >"${TMP_SERVICE_FILE}.2"
        awk """{gsub(/USER_NAME/, \"${USER}\")}1""" "${TMP_SERVICE_FILE}.2" >"${TMP_SERVICE_FILE}"

        echo "Installing '${SRV_NAME}' service"
        mkdir -p "${LAUNCH_DIR}"
        mkdir -p "${LOG_DIR}"
        mv "${TMP_SERVICE_FILE}" "${LAUNCH_DIR}/${SRV_NAME}.plist"

        echo "Starting '${SRV_NAME}' Launch Agent"
        launchctl load "${LAUNCH_DIR}/${SRV_NAME}.plist"
        launchctl start "${SRV_NAME}"

    elif [ "${COMMAND}" = "uninstall" ]; then
        if [ ! -f "${LAUNCH_DIR}/${SRV_NAME}.plist" ]; then
            echo "Service is already uninstalled!"
            exit 0
        fi

        echo "Stopping '${SRV_NAME}' service"
        launchctl stop ${SRV_NAME}
        launchctl unload "${LAUNCH_DIR}/${SRV_NAME}.plist"

        echo "Uninstalling '${SRV_NAME}' service"
        rm -f "${LAUNCH_DIR}/${SRV_NAME}.plist"

    else
        if [ ! -f "${LAUNCH_DIR}/${SRV_NAME}.plist" ]; then
            echo "The service not installed!"
            exit 1
        fi

        echo "Service '${SRV_NAME}' ${COMMAND}ing"
        launchctl "${COMMAND}" ${SRV_NAME}
    fi
fi
