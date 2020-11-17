#!/usr/bin/env python3
import glob
import json
import os
import shutil
import zipfile
from collections import namedtuple
from enum import Enum

import requests

from builders.docker import DockerBuilder, DockerInfo
from builders.ssh import SshClient, Credentials
from builders.virtual_box import VirtualBoxBuilder, VirtualBoxInfo

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


OK_RESULTS = [
    Result.NO_TEST,
    Result.SKIP,
    Result.OK,
]

RESULTS_PRIORITY = {
    Result.NO_TEST: 1,
    Result.SKIP: 2,
    Result.TIMEOUT: 3,
    Result.ERROR: 4,
    Result.FAIL: 5,
    Result.OK: 6,
}


class Tester:
    def __init__(self, config_path='./config.json'):
        with open(config_path, 'r') as fs:
            config = json.load(fs)
            self.__parse_config(config)

        self.__logs = []
        self.__builds = None
        self.__all_builds = []

    def __parse_config(self, config):
        self.commands_url = config.get('commands_url', 'https://www.tarantool.io/api/tarantool/info/versions/')

        self.__install_dir = './install'
        self.__local_dir = './local'
        self.__remote_dir = './remote'
        self.__logs_dir = f'{self.__local_dir}/logs'
        self.__results_dir = f'{self.__local_dir}/results'
        self.__results_file = f'{self.__local_dir}/results.json'

        os_params = config.get('os_params')
        assert config.get('os_params') is not None, 'No OS params in config!'

        self.__docker_params = {
            k: v['docker']
            for k, v in os_params.items()
            if v.get('docker') is not None
        }
        self.__virtual_box_params = {
            k: v['virtual_box']
            for k, v in os_params.items()
            if v.get('virtual_box') is not None
        }

        self.__send_to_remote = None
        if config.get('send_to_remote') is not None:
            credentials = config['send_to_remote'].get('credentials')
            assert credentials is not None, 'Credentials is required in send_to_remote section'
            login = credentials.get('login')
            assert login is not None, 'Login is required in send_to_remote section'
            password = credentials.get('password')
            assert password is not None, 'Password is required in send_to_remote section'
            host = credentials.get('host')
            assert host is not None, 'Host is required in send_to_remote section'

            archive = config['send_to_remote'].get('archive')
            assert archive is not None, 'Archive name is required in send_to_remote section'

            self.__send_to_remote = RemoteInfo(
                credentials=Credentials(
                    login=login,
                    password=password,
                    host=host,
                    port=credentials.get('port', 22),
                ),
                archive=archive,
                remote_dir=config['send_to_remote'].get('remote_dir', '/opt/delivery_checker/remote')
            )

        self.__load_remote_cache = config.get('load_remote_cache', False)

    def __log(self, msg):
        self.__logs.append(msg)

    def __download_scripts(self, debug=False):
        site_commands = requests.get(self.commands_url).json()

        with open(os.path.join(self.__install_dir, 'default.sh'), mode='r') as fs:
            default_script = fs.read()

        builds = []
        for os_name, versions in site_commands.items():
            for build_name, commands in versions.items():
                # Remove os name from build name (ubuntu_manual_2.4 -> manual_2.4)
                build_name = '_'.join(build_name.split('_')[1:])

                # Save to find not tested
                self.__all_builds.append((os_name, build_name))

                # This is to avoid running Docker in Docker or Docker in VirtualBox
                if 'docker' not in os_name:
                    builds_count = len(builds)
                    builds += DockerBuilder.get_builds(self.__docker_params, os_name, build_name)
                    builds += VirtualBoxBuilder.get_builds(self.__virtual_box_params, os_name, build_name)
                    if len(builds) == builds_count and debug:
                        print(f'OS: {os_name}. Build: {build_name}. {Result.NO_TEST.value}')

                # Find name of image in commands and use it
                else:
                    builds += DockerBuilder.get_docker_builds(os_name, build_name, commands)
                    commands = []

                path = os.path.join(self.__install_dir, f'{os_name}_{build_name}.sh')
                with open(path, mode='w') as fs:
                    fs.write(default_script)
                    fs.write('\n'.join(commands))
                    fs.write('\n')

        return builds

    def test_builds(self):
        shutil.rmtree(self.__local_dir, ignore_errors=True)

        os.makedirs(self.__results_dir)
        os.makedirs(self.__logs_dir)

        self.__results = {}
        self.__builds = self.__builds or self.__download_scripts()
        for build in self.__builds:
            self.__logs.clear()

            if isinstance(build, DockerInfo):
                os_name = f'{build.os_name}_{build.image_version}'
            elif isinstance(build, VirtualBoxInfo):
                os_name = f'{build.vm_name}'
            else:
                os_name = build.os_name

            print(f'OS: {os_name}. Build: {build.build_name}. ', end='')
            self.__results[os_name] = self.__results.get(os_name, {})

            if build.skip:
                result = Result.SKIP
            else:
                if isinstance(build, DockerInfo):
                    docker_builder = DockerBuilder(build, log_func=self.__log)
                    deploy_result = docker_builder.deploy()
                elif isinstance(build, VirtualBoxInfo):
                    virtual_box_builder = VirtualBoxBuilder(build, log_func=self.__log)
                    deploy_result = virtual_box_builder.deploy()
                else:
                    deploy_result = False

                if deploy_result:
                    result = Result.OK
                else:
                    result = Result.ERROR
                    path = os.path.join(self.__logs_dir, f'{os_name}_{build.build_name}.log')
                    with open(path, mode='w') as fs:
                        logs = '\n'.join(map(lambda x: str(x), self.__logs))
                        fs.write(logs)
                        logs = logs.lower()
                        if 'timeout' in logs or 'timed out' in logs:
                            result = Result.TIMEOUT

            if result == Result.OK:
                is_results_ok = False

                path = os.path.join(self.__results_dir, f'{os_name}_{build.build_name}.json')
                if os.path.exists(path):
                    with open(path) as fs:
                        try:
                            build_results = json.load(fs)
                            is_results_ok = all(map(
                                lambda build_res: build_res == 'OK',
                                build_results.values(),
                            ))
                        except Exception:
                            pass

                if not is_results_ok:
                    result = Result.FAIL

            print(result.value)
            self.__results[os_name][build.build_name] = result

        with open(self.__results_file, mode='w') as fs:
            fs.write(json.dumps(self.__results))

    def send_results(self, timeout=3 * 60):
        if self.__send_to_remote is None:
            return True

        try:
            ssh = SshClient(self.__send_to_remote.credentials, log_func=self.__log)
            ssh.send_files_as_zip(
                paths=[self.__local_dir],
                rel_dir=self.__local_dir,
                zip_name=f'{self.__send_to_remote.archive}.zip',
                remote_dir=f'{self.__send_to_remote.remote_dir}',
                timeout=timeout,
            )
            return True

        except Exception as e:
            print(f'Impossible to send results to remote server:\n{e}')

        return False

    def __merge_results(self, remote_path):
        with open(self.__results_file, mode='r') as fs:
            local_results = json.load(fs)

        with open(remote_path, mode='r') as fs:
            remote_results = json.load(fs)

        for os_name, builds in remote_results.items():
            local_results[os_name] = local_results.get(os_name, {})
            for build_name, remote_result in builds.items():
                local_result = local_results[os_name].get(build_name, Result.NO_TEST)
                if RESULTS_PRIORITY[remote_result] >= RESULTS_PRIORITY[local_result]:
                    local_results[os_name][build_name] = remote_result

        with open(self.__results_file, mode='w') as fs:
            fs.write(json.dumps(local_results))

    def get_results(self, temp_dir='./temp'):
        if not self.__load_remote_cache:
            return

        for archive in glob.glob(f'{self.__remote_dir}/*.zip'):
            with zipfile.ZipFile(archive, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, _, files in os.walk(f'{temp_dir}/logs'):
                for file in files:
                    shutil.move(os.path.join(root, file), f'{self.__local_dir}/logs')

            for root, _, files in os.walk(f'{temp_dir}/results'):
                for file in files:
                    shutil.move(os.path.join(root, file), f'{self.__local_dir}/results')

            self.__merge_results(f'{temp_dir}/results.json')

            shutil.rmtree(temp_dir, ignore_errors=True)
            os.remove(archive)

    def find_lost_results(self):
        self.__builds = self.__builds or self.__download_scripts()

        with open(self.__results_file, mode='r') as fs:
            results = json.load(fs)

        new_results = {}
        for build in self.__all_builds:
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

        with open(self.__results_file, mode='w') as fs:
            fs.write(json.dumps(results))

    def sync_results(self):
        self.send_results()
        self.get_results()
        self.find_lost_results()

    def is_results_ok(self):
        with open(self.__results_file, mode='r') as fs:
            results = json.load(fs)
        return all(map(
            lambda builds: all(map(
                lambda build_res: build_res in OK_RESULTS,
                builds.values(),
            )),
            results.values(),
        ))


def main():
    tester = Tester()
    tester.test_builds()
    tester.sync_results()
    return tester.is_results_ok()


if __name__ == '__main__':
    exit(not main())
