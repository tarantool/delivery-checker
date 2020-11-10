#!/usr/bin/env python3
import json
import os
import shutil

import requests

from builders.docker import DockerBuilder, DockerInfo
from builders.virtual_box import VirtualBoxBuilder, VirtualBoxInfo


class Tester:
    def __init__(
        self,
        config_path='./config.json',
        commands_url='https://www.tarantool.io/api/tarantool/info/versions/',
    ):
        with open(config_path, 'r') as fs:
            config = json.load(fs)

        self.__logs = []

        def log_func(msg): self.__logs.append(msg)

        docker_config = {k: v['docker'] for k, v in config.items() if v.get('docker') is not None}
        self.__docker = DockerBuilder(config=docker_config, log_func=log_func)

        virtual_box_config = {k: v['virtual_box'] for k, v in config.items() if v.get('virtual_box') is not None}
        self.__virtual_box = VirtualBoxBuilder(config=virtual_box_config, log_func=log_func)

        self.__builds = self.download_scripts(commands_url)

    def download_scripts(self, commands_url, scripts_dir='./install'):
        site_commands = requests.get(commands_url).json()

        with open(os.path.join(scripts_dir, 'default.sh'), mode='r') as fs:
            default_script = fs.read()

        builds = []
        for os_name, versions in site_commands.items():
            for build_name, commands in versions.items():
                # Remove os name from build name (ubuntu_manual_2.4 -> manual_2.4)
                build_name = '_'.join(build_name.split('_')[1:])

                # This is to avoid running Docker in Docker or Docker in VirtualBox
                if os_name != 'docker':
                    builds += self.__docker.get_builds(os_name, build_name)
                    builds += self.__virtual_box.get_builds(os_name, build_name)

                # Find name of image in commands and use it
                else:
                    builds += self.__docker.get_docker_builds(os_name, build_name, commands)
                    commands = []

                path = os.path.join(scripts_dir, f'{os_name}_{build_name}.sh')
                with open(path, mode='w') as fs:
                    fs.write(default_script)
                    fs.write('\n'.join(commands))
                    fs.write('\n')

        return builds

    def test_builds(self, results_dir='./results', logs_dir='./logs'):
        shutil.rmtree(results_dir, ignore_errors=True)
        shutil.rmtree(logs_dir, ignore_errors=True)

        os.makedirs(results_dir)
        os.makedirs(logs_dir)

        results = {}
        is_all_ok = True

        for build in self.__builds:
            self.__logs.clear()

            if isinstance(build, DockerInfo):
                os_name = f'{build.os_name}_{build.image_version}'
            elif isinstance(build, VirtualBoxInfo):
                os_name = f'{build.vm_name}'
            else:
                os_name = build.os_name

            print(f'OS: {os_name}. Build: {build.build_name}. ', end='')
            results[os_name] = results.get(os_name, {})

            if build.skip:
                result = 'SKIP'
            else:
                if isinstance(build, DockerInfo):
                    deploy_result = self.__docker.deploy(build)
                elif isinstance(build, VirtualBoxInfo):
                    deploy_result = self.__virtual_box.deploy(build)
                else:
                    deploy_result = False

                if deploy_result:
                    result = 'OK'
                else:
                    result = 'ERROR'
                    is_all_ok = False
                    path = os.path.join(logs_dir, f'{os_name}_{build.build_name}.log')
                    with open(path, mode='w') as fs:
                        logs = '\n'.join(map(lambda x: str(x), self.__logs))
                        fs.write(logs)
                        logs = logs.lower()
                        if 'timeout' in logs or 'timed out' in logs:
                            result = 'TIMEOUT'

            if result == 'OK':
                path = os.path.join(results_dir, f'{os_name}_{build.build_name}.json')
                if os.path.exists(path):
                    with open(path) as fs:
                        build_results = json.load(fs)
                        is_results_ok = True
                        for build_result in build_results.values():
                            if build_result != 'OK':
                                is_results_ok = False
                                break
                else:
                    is_results_ok = False

                if not is_results_ok:
                    result = 'FAIL'
                    is_all_ok = False

            print(result)
            results[os_name][build.build_name] = result

        with open('results.json', mode='w') as fs:
            fs.write(json.dumps(results))

        return is_all_ok


def main():
    tester = Tester()
    return tester.test_builds()


if __name__ == '__main__':
    exit(not main())
