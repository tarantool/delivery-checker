import itertools
import json
import os
import re
from collections import namedtuple

from docker import from_env as docker_from_env
from docker.errors import APIError
from docker.utils.json_stream import json_stream

from build_tester.helpers.common import print_logs, get_header_str, get_subheader_str, get_best_prepare_script

DockerInfo = namedtuple(
    typename='DockerInfo',
    field_names=('os_name', 'build_name', 'tnt_version', 'image', 'image_version', 'skip', 'use_cache'),
)


class DockerBuilder:
    def __init__(
        self, build_info,
        scripts_dir_path='.',
        prepare_dir_path='./prepare',
        tests_dir_path='./local/tests',
        log_func=print
    ):
        self.build_info = build_info
        self.scripts_dir_path = os.path.abspath(scripts_dir_path)
        self.prepare_dir_path = os.path.abspath(prepare_dir_path)
        self.tests_dir_path = os.path.abspath(tests_dir_path)
        self.log = log_func

        self.__client = docker_from_env()
        self.__build_log = []
        self.__image_id = None

    @staticmethod
    def get_builds(config, os_name='docker', build_name='latest', tnt_version=None, default_use_cache=False):
        params = config.get(os_name)
        if params is None:
            return []
        build_list = []
        for version in params.get('versions', ['latest']):
            skip = False
            if params.get("skip_os_versions"):
                for tnt_version in params["skip_os_versions"].get(version, []):
                    if build_name.endswith(tnt_version):
                        skip = True
            image = params.get('image', os_name)
            if 'tarantool/delivery-checker:' in version:
                image, version = version.partition(':')[::2]
            build_list.append(DockerInfo(
                os_name=os_name,
                build_name=build_name,
                tnt_version=tnt_version,
                image=image,
                image_version=version,
                skip=build_name in params.get('skip', []) or skip,
                use_cache=params.get('use_cache', default_use_cache),
            ))
        return build_list

    @staticmethod
    def get_docker_builds(config, os_name, build_name, tnt_version, commands, default_use_cache=False):
        params = config.get(os_name)
        if params is None:
            return []

        builds = []
        for command in commands:
            match = re.search(r'docker (pull|run).* ([\w/]+)(:([\w.]+))?', command, flags=re.I)
            if match:
                builds.append(DockerInfo(
                    os_name=os_name,
                    build_name=build_name,
                    tnt_version=tnt_version,
                    image=match.group(2),
                    image_version=match.group(4) or 'latest',
                    skip=build_name in params.get('skip', []),
                    use_cache=params.get('use_cache', default_use_cache),
                ))
                break

        return builds

    def rm(self, container_name):
        self.log(get_header_str('REMOVE STEP'))

        try:
            try:
                exists_containers = self.__client.containers.list(all=True)
                for container in exists_containers:
                    if container.name == container_name:
                        container.remove(force=True)
                        break

                self.__client.containers.prune()
                self.__client.images.prune(filters={'dangling': True})

            except APIError as e:
                if e.status_code == 404:
                    pass
                elif e.explanation:
                    raise Exception(e.explanation)
                else:
                    raise Exception(e)

        except Exception as e:
            self.log(f'Impossible to remove container: {e}\n')
            return False

        self.log(f'Container {container_name} removed.\n')
        return True

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

    def __get_build_logs(self):
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
        return logs_string

    def __get_best_prepare_script(self):
        os_prefix = f'{self.build_info.os_name}_{self.build_info.image_version}_{self.build_info.build_name}'
        os_prefix = set(os_prefix.split('_'))

        image_prefix = f'{self.build_info.image}_{self.build_info.image_version}_{self.build_info.build_name}'
        image_prefix = set(image_prefix.split('_'))

        best_script_path = get_best_prepare_script(self.prepare_dir_path, os_prefix, image_prefix)
        if best_script_path is not None:
            return os.path.basename(best_script_path)

        return 'empty.sh'

    def build(self, container_name, timeout=60 * 15):
        self.log(get_header_str('BUILD STEP'))

        result = False

        try:
            tnt_version = self.build_info.tnt_version
            gc64 = self.build_info.build_name.endswith('_gc64')
            if not tnt_version:
                if gc64:
                    tnt_version = self.build_info.build_name.split('_')[-2]
                else:
                    tnt_version = self.build_info.build_name.split('_')[-1]
            self.__image_id = self.__build_image(
                path=self.scripts_dir_path,
                tag=container_name,
                buildargs={
                    'IMAGE': self.build_info.image,
                    'VERSION': self.build_info.image_version,
                    'OS_NAME': self.build_info.os_name,
                    'PREPARE_SCRIPT_NAME': self.__get_best_prepare_script(),
                    'BUILD_NAME': self.build_info.build_name,
                    'TNT_VERSION': tnt_version,
                    'GC64': str(gc64).lower(),
                },
                timeout=timeout,
                nocache=not self.build_info.use_cache,
            )
            result = True

        except Exception as e:
            if 'Read timed out' in str(e):
                self.log('Timeout of building container!\n')
            else:
                self.log(f'Impossible to build container: {e}!\n')

        self.log(get_subheader_str('BUILD LOGS'))
        print_logs(out_data=self.__get_build_logs(), log=self.log)

        return result

    def run(self, container_name, timeout=60):
        self.log(get_header_str('RUN STEP'))

        result = False

        try:
            container = self.__client.containers.run(
                image=container_name,
                name=container_name,
                ports={3301: 3301},
                volumes={self.tests_dir_path: {'bind': '/opt/tarantool/results'}},
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
                result = True
            else:
                self.log(f'Error code: {res["StatusCode"]}, Error message: {res["Error"]}\n')

            self.log(get_subheader_str('RUNTIME LOGS'))
            print_logs(out_data=container.logs().decode(), log=self.log)

        except Exception as e:
            self.log(f'Impossible to run container: {e}\n')

        return result

    def deploy(self, container_name='tnt_builder'):
        try:
            is_success = True
            if not self.rm(container_name):
                is_success = False
            if is_success and not self.build(container_name):
                is_success = False
            if is_success and not self.run(container_name):
                is_success = False
        finally:
            self.rm(container_name)

        return is_success
