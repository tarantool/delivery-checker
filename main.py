#!/usr/bin/env python3

import argparse

from classes.tester import Tester


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
    tester.archive_results()
    return tester.is_results_ok()


if __name__ == '__main__':
    exit(not main())
