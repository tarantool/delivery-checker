import datetime
import glob
import json
import os
import shutil
import zipfile
from collections import namedtuple
from enum import Enum

from build_tester.helpers.ssh import SshClient, Credentials
from build_tester.helpers.zip import Zip
from config.config import CheckerConfig

RemoteInfo = namedtuple(
    typename='RemoteInfo',
    field_names=('credentials', 'archive', 'remote_dir'),
)


class Result(str, Enum):
    NO_TEST = 'NO TEST'
    SKIP = 'SKIP'
    OK = 'OK'
    TIMEOUT = 'TIMEOUT'
    ERROR = 'ERROR'
    FAIL = 'FAIL'
    CANCELED = 'CANCELED'


RESULTS_PRIORITY = {
    Result.NO_TEST: 1,
    Result.SKIP: 2,
    Result.CANCELED: 3,
    Result.OK: 4,
    Result.TIMEOUT: 5,
    Result.ERROR: 6,
    Result.FAIL: 7,
}

SUCCESS_RESULTS = [
    Result.NO_TEST,
    Result.SKIP,
    Result.OK,
]


class ResultsManager:
    def __init__(self, config: CheckerConfig, log_func=print):
        self.config = config
        self.__parse_config()

        self.log = log_func

        self.__zip = Zip()

    def __parse_config(self):
        config = self.config
        self.__send_to_remote = None

        if config.send_to_remote:
            login = config.send_to_remote.get('login')
            assert login is not None, 'Login is required in send_to_remote section'
            password = config.send_to_remote.get('password')
            assert password is not None, 'Password is required in send_to_remote section'
            host = config.send_to_remote.get('host')
            assert host is not None, 'Host is required in send_to_remote section'

            archive = config.send_to_remote.get('archive')
            assert archive is not None, 'Archive name is required in send_to_remote section'

            self.__send_to_remote = RemoteInfo(
                credentials=Credentials(
                    login=login,
                    password=password,
                    host=host,
                    port=config.send_to_remote.get('port', 22),
                ),
                archive=archive,
                remote_dir=config.send_to_remote.get('remote_dir', '/opt/delivery_checker/remote')
            )

    def send_results(self, timeout=3 * 60):
        if self.__send_to_remote is None:
            return True

        zip_name = f'{self.__send_to_remote.archive}.zip'

        try:
            self.__zip.zip_path(
                path=self.config.local_dir_path,
                rel_dir=self.config.local_dir_path,
                zip_name=zip_name,
            )

            ssh = SshClient(self.__send_to_remote.credentials, log_func=self.log)
            ssh.send_file(
                zip_name=zip_name,
                remote_dir=f'{self.__send_to_remote.remote_dir}',
                timeout=timeout,
            )
            return True

        except Exception as e:
            self.log(f'Impossible to send results to remote server:\n{e}')

        finally:
            os.remove(zip_name)

        return False

    def __merge_results(self, remote_path):
        with open(self.config.results_file_path, mode='r') as fs:
            local_results = json.load(fs)

        with open(remote_path, mode='r') as fs:
            remote_results = json.load(fs)

        for os_name, builds in remote_results.items():
            local_results[os_name] = local_results.get(os_name, {})
            for build_name, remote_result in builds.items():
                local_result = local_results[os_name].get(build_name, Result.NO_TEST)
                if RESULTS_PRIORITY[remote_result] >= RESULTS_PRIORITY[local_result]:
                    local_results[os_name][build_name] = remote_result

        with open(self.config.results_file_path, mode='w') as fs:
            fs.write(json.dumps(local_results))

    def use_remote_results(self, temp_dir='./temp'):


        for archive in glob.glob(os.path.join(self.config.remote_dir_path, '*.zip')):
            with zipfile.ZipFile(archive, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, _, files in os.walk(os.path.join(temp_dir, self.config.logs_dir_name)):
                for file in files:
                    shutil.move(
                        os.path.join(root, file),
                        os.path.join(self.config.local_dir_path, self.config.logs_dir_name),
                    )

            for root, _, files in os.walk(os.path.join(temp_dir, self.config.tests_dir_name)):
                for file in files:
                    shutil.move(
                        os.path.join(root, file),
                        os.path.join(self.config.local_dir_path, self.config.tests_dir_name),
                    )

            self.__merge_results(os.path.join(temp_dir, self.config.results_file_name))

            shutil.rmtree(temp_dir, ignore_errors=True)

    def find_lost_results(self, all_builds):
        with open(self.config.results_file_path, mode='r') as fs:
            results = json.load(fs)

        new_results = {}
        for build in all_builds:
            os_name = build[0]
            build_name = build[1]
            if not any(map(
                lambda os_name_version: os_name in os_name_version,
                results.keys(),
            )):
                new_results[os_name] = new_results.get(os_name, {})
                new_results[os_name][build_name] = Result.NO_TEST.value

        for os_name, builds in new_results.items():
            results[os_name] = builds

        with open(self.config.results_file_path, mode='w') as fs:
            fs.write(json.dumps(results, sort_keys=True, indent=4))

    def sync_results(self, all_builds):
        self.send_results()
        if self.config.use_remote_results:
            self.use_remote_results()
        self.find_lost_results(all_builds)

    def get_results(self):
        with open(self.config.results_file_path, mode='r') as fs:
            return json.load(fs)

    def archive_results(self):
        os.makedirs(self.config.archive_dir_path, exist_ok=True)
        dir_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.move(self.config.local_dir_path, os.path.join(self.config.archive_dir_path, dir_name))
        return dir_name

    def is_results_ok(self):
        with open(self.config.results_file_path, mode='r') as fs:
            results = json.load(fs)
        return all(map(
            lambda builds: all(map(
                lambda build_res: build_res in SUCCESS_RESULTS,
                builds.values(),
            )),
            results.values(),
        ))
