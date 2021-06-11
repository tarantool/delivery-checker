# Delivery Checker

This is a program that downloads Tarantool's installation commands and tries to
run them on different OS.

## How to run

### Prepare

1. Install Python 3.6 or higher;
2. Install Docker or/and VirtualBox;
3. Change `config.json` if necessary (e.g. to add TG token).

### Run

1. Run `run_check.py` to check installation;
2. Run `run_bot.py` to run Telegram bot.

### Configure automatic runs

To run checks and bot automatically, you can use cron like this:

```shell
crontab -e
# Put this to crontab config (replace working directory with yours):
# 0 9,19 * * * /bin/bash ${DELIVERY_CHECKER_WORKDIR}/run_check.sh -f
# TG bot sometimes freezes, so you can add this (replace bot name with yours):
# */15 * * * * sudo systemctl restart ${DELIVERY_CHECKER_BOT_NAME}
# OR
# */15 * * * * sudo launchctl restart ${DELIVERY_CHECKER_BOT_NAME}
```

## Config with all available options

You can find all available config options in
file [config-full.json](/config-full.json).

## Example of output

For example, you can have output like this:

```
OS: freebsd_12.2. Build: pkg_2.4. Elapsed time: 95.85. OK
OS: freebsd_12.2. Build: ports_2.4. Elapsed time: 355.99. TIMEOUT
OS: amazon-linux_2. Build: script_2.5. Elapsed time: 85.43. ERROR
OS: amazon-linux_2. Build: script_1.10. Elapsed time: 88.83. ERROR
OS: os-x_10.12. Build: 2.5. SKIP
OS: os-x_10.12. Build: 2.6. Elapsed time: 521.86. OK
OS: docker-hub_2.5. Build: 2.5. Elapsed time: 122.72. OK
```

In this case, the process finished with exit code 1 because there are some
errors.
