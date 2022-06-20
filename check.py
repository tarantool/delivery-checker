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
    args: argparse.Namespace = parser.parse_args()

    with open(args.config, 'r') as fs:
        config_json = json.load(fs)

    config = CheckerConfig(cli_args=args, config_json=config_json)

    tester = Tester(config=config)
    tester.test_builds()
    tester.sync_results()
    is_results_ok = tester.is_results_ok()

    results = tester.get_results()
    dir_name = tester.archive_results()

    bot = Bot(args.config, args.debug_mode)
    bot.send_out_builds_info(results, dir_name)

    return is_results_ok


if __name__ == '__main__':
    exit(not main())
