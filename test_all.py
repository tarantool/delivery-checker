import os
import shutil
from collections import namedtuple

import requests
from docker import from_env as docker_from_env
from docker.errors import DockerException, BuildError, APIError

Build = namedtuple(
    typename='Build',
    field_names=('image', 'image_version', 'os_name', 'build_name'),
)

IMAGES = {
    'docker': 'tarantool/tarantool',
    'freebsd': 'auchida/freebsd',
    'amazon-linux': 'amazonlinux',
    'macos': 'sickcodes/docker-osx',
}

VERSIONS = {
    'tarantool/tarantool': ['tnt_version'],
    'ubuntu': ['18.04'],
    'fedora': ['31'],
    'centos': ['7'],
    'amazonlinux': ['1', '2'],
}


def get_builds(os_name='docker', build_name='latest'):
    image = IMAGES.get(os_name, os_name)

    tnt_version = build_name.split('_')[-1]
    image_versions = map(
        lambda version: tnt_version if version == 'tnt_version' else version,
        VERSIONS.get(image, ['latest']),
    )

    builds = list(map(
        lambda version: Build(image, version, os_name, build_name),
        image_versions,
    ))

    return builds


class TarantoolDocker:
    def __init__(self, log_func=print):
        self.log = log_func
        self.__client = docker_from_env()

    def rm(self, container_name):
        try:
            exists_container = self.__client.containers.get(container_name)
            exists_container.remove(force=True)
            return True

        except APIError as e:
            if e.status_code == 404:
                return True
            elif e.explanation:
                self.log(e.explanation)
            else:
                self.log(e)

        except DockerException as e:
            self.log(e)

        return False

    def build(self, container_name, build, timeout=60 * 30):
        try:
            self.__client.images.build(
                path='.',
                tag=container_name,
                buildargs={
                    'IMAGE': build.image,
                    'VERSION': build.image_version,
                    'OS_NAME': build.os_name,
                    'BUILD_NAME': build.build_name,
                },
                timeout=timeout,
            )
            return True

        except BuildError as e:
            self.log('Impossible to build container!')
            self.log('Build logs:')
            logs_string = ''
            for msg in e.build_log:
                if 'stream' in msg:
                    logs_string += msg['stream']
                elif 'error' in msg:
                    logs_string += msg['error']
                elif 'status' in msg:
                    continue
                else:
                    logs_string += msg
            for line in logs_string.splitlines():
                if line:
                    self.log(line)

        except Exception as e:
            if 'Read timed out' in str(e):
                self.log('Timeout of building container')
            else:
                self.log('Impossible to build container:', e)

        return False

    def run(self, container_name, timeout=30):
        try:
            container = self.__client.containers.run(
                image=container_name,
                name=container_name,
                ports={3301: 3301},
                volumes={f'{os.getcwd()}/results': {'bind': '/opt/tarantool/results'}},
                detach=True,
            )

            try:
                res = container.wait(timeout=timeout)
            except Exception as e:
                if 'Read timed out' in str(e):
                    res = {'Error': 'Timeout of tarantool script execution', 'StatusCode': 1}
                else:
                    res = {'Error': e, 'StatusCode': 1}

            if res['StatusCode'] == 0:
                return True

            self.log(f'Error code: {res["StatusCode"]}, Error message: {res["Error"]}')
            self.log('Runtime logs:')
            for line in container.logs().decode().splitlines():
                if line:
                    self.log(line)

        except DockerException as e:
            self.log('Impossible to run container:', e)

        return False

    def deploy(self, build, container_name='tnt_builder'):
        if not self.rm(container_name):
            return False
        if not self.build(container_name, build):
            return False
        if not self.run(container_name):
            return False
        return True


class Tester:
    def __init__(self):
        self.__logs = []
        self.__docker = TarantoolDocker(log_func=lambda msg: self.__logs.append(msg))
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
                builds += get_builds(os_name, build_name)

                path = os.path.join(scripts_dir, f'{os_name}_{build_name}.sh')
                with open(path, mode='w') as fs:
                    fs.write(default_script)
                    fs.write('\n'.join(commands))
                    fs.write('\n')

        return builds

    def test_builds(self, results_dir='./results'):
        shutil.rmtree(results_dir, ignore_errors=True)
        for build in self.__builds:
            self.__logs.clear()
            print(f'OS: {build.os_name} {build.image_version}. Build: {build.build_name}. Deploying... ', end='')
            if self.__docker.deploy(build):
                print('OK')
            else:
                print('ERROR')
                print('\n'.join(map(lambda x: str(x), self.__logs)))


def main():
    tester = Tester()
    return tester.test_builds()


if __name__ == '__main__':
    exit(not main())
