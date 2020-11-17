import itertools
import json
import os
import re
from collections import namedtuple

from docker import from_env as docker_from_env
from docker.errors import APIError
from docker.utils.json_stream import json_stream

DockerInfo = namedtuple(
    typename='DockerInfo',
    field_names=('os_name', 'build_name', 'image', 'image_version', 'skip'),
)


class DockerBuilder:
    def __init__(self, build_info, log_func=print):
        self.log = log_func
        self.build_info = build_info
        self.__client = docker_from_env()
        self.__build_log = []

    @staticmethod
    def get_builds(config, os_name='docker', build_name='latest'):
        params = config.get(os_name)
        if params is None:
            return []

        return list(map(
            lambda version: DockerInfo(
                os_name=os_name,
                build_name=build_name,
                image=params.get('image', os_name),
                image_version=version,
                skip=build_name in params.get('skip', []),
            ),
            params.get('versions', ['latest']),
        ))

    @staticmethod
    def get_docker_builds(os_name, build_name, commands):
        builds = []

        for command in commands:
            match = re.search(r'docker (pull|run) ([\w/]+)(:([\w.]+))?', command, flags=re.I)
            if match:
                builds.append(DockerInfo(
                    os_name=os_name,
                    build_name=build_name,
                    image=match.group(2),
                    image_version=match.group(4) or 'latest',
                    skip=False,
                ))
                break

        return builds

    def rm(self, container_name):
        try:
            exists_containers = self.__client.containers.list(all=True)
            for container in exists_containers:
                if container.name == container_name:
                    container.remove(force=True)
                    break
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

    # Copy of self.__client.images.build() to get build logs on timeout
    def __build_image(self, **kwargs):
        self.__build_log = []
        resp = self.__client.api.build(**kwargs)
        if isinstance(resp, str):
            return resp
        self.__build_log, internal_stream = itertools.tee(json_stream(resp))

        image_id = None
        for chunk in internal_stream:
            if 'error' in chunk:
                raise Exception(chunk['error'])
            if 'stream' in chunk:
                match = re.search(
                    r'(^Successfully built |sha256:)([0-9a-f]+)$',
                    chunk['stream']
                )
                if match:
                    image_id = match.group(2)
        if image_id:
            return image_id
        raise Exception('No image id in logs!')

    def build(self, container_name, timeout=60 * 15):
        try:
            self.__build_image(
                path='.',
                tag=container_name,
                buildargs={
                    'IMAGE': self.build_info.image,
                    'VERSION': self.build_info.image_version,
                    'OS_NAME': self.build_info.os_name,
                    'BUILD_NAME': self.build_info.build_name,
                },
                timeout=timeout,
                rm=True,
            )
            return True

        except Exception as e:
            if 'Read timed out' in str(e):
                self.log('Timeout of building container!')
            else:
                self.log(f'Impossible to build container: {e}!')
            self.log('Docker build logs:')
            logs_string = ''
            for msg in self.__build_log:
                if 'stream' in msg:
                    logs_string += msg['stream']
                elif 'error' in msg:
                    logs_string += msg['error']
                elif 'message' in msg:
                    logs_string += msg['message']
                elif 'status' in msg:
                    continue
                else:
                    logs_string += json.dumps(msg) + '\n'
            for line in logs_string.splitlines():
                if line:
                    self.log(line)

        return False

    def run(self, container_name, timeout=60):
        try:
            container = self.__client.containers.run(
                image=container_name,
                name=container_name,
                ports={3301: 3301},
                volumes={f'{os.getcwd()}/local/results': {'bind': '/opt/tarantool/results'}},
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

    def deploy(self, container_name='tnt_builder'):
        is_success = True
        if not self.rm(container_name):
            is_success = False
        if is_success and not self.build(container_name):
            is_success = False
        if is_success and not self.run(container_name):
            is_success = False
        if not self.rm(container_name):
            is_success = False
        return is_success
