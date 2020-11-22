#!/usr/bin/env python3

from classes.tester import Tester


def main():
    tester = Tester()
    tester.test_builds()
    tester.sync_results()
    return tester.is_results_ok()


if __name__ == '__main__':
    exit(not main())
