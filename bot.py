#!/usr/bin/env python3

import argparse

from telegram_bot.bot import Bot


def main():
    parser = argparse.ArgumentParser(description='Tarantool Delivery Checker')
    parser.add_argument(
        '-c', '--config', default='./config.json',
        help='Path to config',
    )
    parser.add_argument(
        '-d', '--debug-mode', action='store_true',
        help='Use this flag to enable debug mode',
    )
    args = parser.parse_args()

    bot = Bot(args.config, args.debug_mode)
    return bot.start()


if __name__ == '__main__':
    exit(not main())
