#!/usr/bin/env python3

import argparse
import json

from build_tester.tester import Tester
from config.config import CheckerConfig
from telegram_bot.bot import Bot


def main():
    parser = argparse.ArgumentParser(description='Tarantool Delivery Checker')
    parser.add_argument(
        '-c', '--config', default='./config.json',
        help='Path to config',
    )
    parser.add_argument(
        '-v', '--console-mode', action='store_true',
        help='Use this flag to enable console mode',
    )
    parser.add_argument(
        '-d', '--debug-mode', action='store_true',
        help='Use this flag to enable debug mode',
    )
    parser.add_argument(
        '--ci-mode',
        action='store_true',
        help='Run a one-time test, skipping results archivation and Telegram bot'
    )
    parser.add_argument(
        '--version',
        help='Tarantool version, such as 1.10 or 2.10'
    )
    parser.add_argument(
        '--gc64',
        action='store_true',
        help='Check installation of GC64 packages'
    )
    parser.add_argument(
        '--build',
        help='Tarantool build: manual, script, or nightly',
    )
    parser.add_argument(
        '--dist',
        help='OS distribution to check, one of '
             'amazon, '
             'centos, '
             'debian, '
             'fedora, '
             'freebsd, '
             'macos, '
             'opensuse, '
             'redos, or '
             'ubuntu.'
    )
    parser.add_argument(
        '--dist-version',
        help='Exact version of the distribution to check'
    )
    parser.add_argument(
        '--commands-url',
        help='URL for fetching Tarantool build instructions'
    )
    parser.add_argument(
        '--commands-url-user',
        help='User for auth on the commands_url'
    )
    parser.add_argument(
        '--commands-url-pass',
        help='Password for auth on the commands_url'
    )
    parser.add_argument(
        '--host-mode',
        action='store_true',
        help='Start the check on the host without any virtualization'
    )

    args: argparse.Namespace = parser.parse_args()

    if not args.host_mode:
        with open(args.config, 'r') as fs:
            config_json = json.load(fs)
    else:
        config_json = {}

    config = CheckerConfig(cli_args=args, config_json=config_json)

    tester = Tester(config=config)
    tester.test_builds()
    if not config.ci_mode or not config.host_mode:
        tester.sync_results()
    is_results_ok = tester.is_results_ok()

    results = tester.get_results()
    dir_name = tester.archive_results()

    if config.ci_mode or config.host_mode:
        return is_results_ok

    bot = Bot(args.config, args.debug_mode)
    bot.send_out_builds_info(results, dir_name)

    return is_results_ok


if __name__ == '__main__':
    exit(not main())
