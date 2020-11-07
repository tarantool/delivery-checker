#!/usr/bin/env python3

import os
import shutil

import requests

from docker_builder import DockerBuilder, DockerInfo
from vm_builder import VmBuilder, VmInfo


class Tester:
    def __init__(self):
        self.__logs = []
        self.__docker = DockerBuilder(log_func=lambda msg: self.__logs.append(msg))
        self.__vm = VmBuilder(log_func=lambda msg: self.__logs.append(msg))
        self.__builds = self.download_scripts()

    @staticmethod
    def download_scripts(commands_url='https://www.tarantool.io/api/tarantool/info/versions/', scripts_dir='./install'):
        site_commands = requests.get(commands_url).json()

        with open(os.path.join(scripts_dir, 'default.sh'), mode='r') as fs:
            default_script = fs.read()

        builds = []
        for os_name, versions in site_commands.items():
            for build_name, commands in versions.items():
                if os_name == 'docker':
                    commands = []

                build_name = '_'.join(build_name.split('_')[1:])

                docker_builds = DockerBuilder.get_builds(os_name, build_name)
                if docker_builds:
                    builds += docker_builds

                vm_builds = VmBuilder.get_builds(os_name, build_name)
                if vm_builds:
                    builds += vm_builds

                path = os.path.join(scripts_dir, f'{os_name}_{build_name}.sh')
                with open(path, mode='w') as fs:
                    fs.write(default_script)
                    fs.write('\n'.join(commands))
                    fs.write('\n')

        return builds

    def test_builds(self, results_dir='./results'):
        shutil.rmtree(results_dir, ignore_errors=True)
        os.makedirs(results_dir)

        for build in self.__builds:
            self.__logs.clear()

            if isinstance(build, DockerInfo):
                print(f'OS: {build.os_name} {build.image_version}. Build: {build.build_name}. Deploying... ', end='')
                deploy_result = self.__docker.deploy(build)
            elif isinstance(build, VmInfo):
                print(f'OS: {build.vm_name}. Build: {build.build_name}. Deploying... ', end='')
                deploy_result = self.__vm.deploy(build)
            else:
                deploy_result = False

            if deploy_result:
                print('OK')
            else:
                print('ERROR')
                print('\n'.join(map(lambda x: str(x), self.__logs)))


def main():
    tester = Tester()
    return tester.test_builds()


if __name__ == '__main__':
    exit(not main())
