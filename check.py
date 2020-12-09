#!/usr/bin/env python3

import argparse

from build_tester.tester import Tester
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
    args = parser.parse_args()

    tester = Tester(args.config, args.console_mode, args.debug_mode)
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
