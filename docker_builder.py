import os
from collections import namedtuple

from docker import from_env as docker_from_env
from docker.errors import BuildError, APIError

DockerInfo = namedtuple(
    typename='DockerInfo',
    field_names=('os_name', 'build_name', 'image', 'image_version'),
)

IMAGES = {
    'docker': 'tarantool/tarantool',
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


class DockerBuilder:
    def __init__(self, log_func=print):
        self.log = log_func
        self.__client = docker_from_env()

    @staticmethod
    def get_builds(os_name='docker', build_name='latest'):
        if os_name not in IMAGES:
            return None

        image = IMAGES[os_name]

        tnt_version = build_name.split('_')[-1]
        image_versions = map(
            lambda version: tnt_version if version == 'tnt_version' else version,
            VERSIONS.get(image, ['latest']),
        )

        builds = list(map(
            lambda version: DockerInfo(os_name, build_name, image, version),
            image_versions,
        ))

        return builds

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

        except Exception as e:
            self.log(f'Impossible to remove container: {e}')

        return False

    def build(self, container_name, build_info, timeout=60 * 30):
        try:
            self.__client.images.build(
                path='.',
                tag=container_name,
                buildargs={
                    'IMAGE': build_info.image,
                    'VERSION': build_info.image_version,
                    'OS_NAME': build_info.os_name,
                    'BUILD_NAME': build_info.build_name,
                },
                timeout=timeout,
            )
            return True

        except BuildError as e:
            self.log('Impossible to build container!')
            self.log('DockerInfo logs:')
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
                self.log(f'Impossible to build container: {e}')

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

        except Exception as e:
            self.log(f'Impossible to run container: {e}')

        return False

    def deploy(self, build_info, container_name='tnt_builder'):
        if not self.rm(container_name):
            return False
        if not self.build(container_name, build_info):
            return False
        if not self.run(container_name):
            return False
        return True
