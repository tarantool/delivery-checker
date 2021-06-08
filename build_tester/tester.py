import json
import os
import shutil
import time

import requests

from build_tester.builders.docker_builder import DockerBuilder, DockerInfo
from build_tester.builders.virtual_box import VirtualBoxBuilder, VirtualBoxInfo
from build_tester.results_sync import ResultsManager, Result


class Tester:
    def __init__(self, config_path='./config.json', console_mode=False, debug_mode=False):
        self.__console_mode = console_mode
        self.__debug_mode = debug_mode
        with open(config_path, 'r') as fs:
            config = json.load(fs)
            self.__parse_config(config)

        self.__logs = []
        self.__builds = None
        self.__all_builds = []

        self.__results_manager = ResultsManager(config)

    def __parse_config(self, config):
        self.commands_url = config.get('commands_url', 'https://www.tarantool.io/api/tarantool/info/versions/')

        self.__scripts_dir_path = config.get('scripts_dir_path', './scripts')

        self.__prepare_dir_name = config.get('prepare_dir_name', 'prepare')
        self.__prepare_dir_path = os.path.join(self.__scripts_dir_path, self.__prepare_dir_name)

        self.__install_dir_name = config.get('install_dir_name', 'install')
        self.__install_dir_path = os.path.join(self.__scripts_dir_path, self.__install_dir_name)

        self.__local_dir_path = config.get('local_dir_path', './local')
        self.__remote_dir_path = config.get('remote_dir_path', './remote')
        self.__archive_dir_path = config.get('archive_dir_path', './archive')

        self.__logs_dir_name = config.get('logs_dir_name', 'logs')
        self.__logs_dir_path = os.path.join(self.__local_dir_path, self.__logs_dir_name)

        self.__tests_dir_name = config.get('tests_dir_name', 'tests')
        self.__tests_dir_path = os.path.join(self.__local_dir_path, self.__tests_dir_name)

        self.__results_file_name = config.get('results_file_name', 'results.json')
        self.__results_file_path = os.path.join(self.__local_dir_path, self.__results_file_name)

        self.__default_use_cache = config.get('default_use_cache', False)

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

    def __log(self, msg):
        self.__logs.append(msg)

    def __save_logs(self, path=None):
        if path is None:
            path = os.path.join(self.__logs_dir_path, f'last.log')

        with open(path, mode='w') as fs:
            logs = '\n'.join(map(lambda x: str(x), self.__logs))
            fs.write(logs)

        return logs

    @staticmethod
    def __get_build_os_name(build):
        if isinstance(build, DockerInfo):
            os_name = f'{build.os_name}_{build.image_version}'
        elif isinstance(build, VirtualBoxInfo):
            os_name = f'{build.vm_name}'
        else:
            os_name = build.os_name

        return os_name

    def __download_scripts(self):
        site_commands = requests.get(self.commands_url).json()

        # Remove old scripts
        for file in os.listdir(self.__install_dir_path):
            if file != 'default.sh':
                os.remove(os.path.join(self.__install_dir_path, file))

        # Get base of install scripts
        with open(os.path.join(self.__install_dir_path, 'default.sh'), mode='r') as fs:
            default_script = fs.read()

        builds = []
        for os_name, versions in site_commands.items():
            for build_name, commands in versions.items():
                # Remove os name from build name (ubuntu_manual_2.4 -> manual_2.4)
                build_name = '_'.join(build_name.split('_')[1:])

                # Save to find not tested
                self.__all_builds.append((os_name, build_name))

                builds_count = len(builds)

                # This is to avoid running Docker in Docker or Docker in VirtualBox
                if 'docker' not in os_name:
                    builds += DockerBuilder.get_builds(
                        self.__docker_params,
                        os_name, build_name,
                        self.__default_use_cache,
                    )
                    builds += VirtualBoxBuilder.get_builds(
                        self.__virtual_box_params,
                        os_name, build_name,
                    )

                # Find name of image in commands and use it
                else:
                    builds += DockerBuilder.get_docker_builds(
                        self.__docker_params,
                        os_name, build_name,
                        commands, self.__default_use_cache,
                    )
                    commands = []

                if len(builds) == builds_count and self.__debug_mode:
                    print(f'OS: {os_name}. Build: {build_name}. {Result.NO_TEST.value}')

                path = os.path.join(self.__install_dir_path, f'{os_name}_{build_name}.sh')
                with open(path, mode='w') as fs:
                    fs.write(default_script)
                    fs.write('\n'.join(commands))
                    fs.write('\n')

        builds.sort(key=lambda build: f'{self.__get_build_os_name(build)}_{build.build_name}')
        return builds

    def test_builds(self):
        shutil.rmtree(self.__local_dir_path, ignore_errors=True)

        os.makedirs(self.__tests_dir_path)
        os.makedirs(self.__logs_dir_path)

        canceled = False
        self.__results = {}
        self.__builds = self.__builds or self.__download_scripts()
        for build in self.__builds:

            self.__logs.clear()

            os_name = self.__get_build_os_name(build)

            log_prefix = f'OS: {os_name}. Build: {build.build_name}.'
            if self.__console_mode:
                print(f'\r{log_prefix} Running...', end='')
            else:
                print(f'{log_prefix} ', end='')

            self.__results[os_name] = self.__results.get(os_name, {})
            install_logs_path = os.path.join(self.__logs_dir_path, f'{os_name}_{build.build_name}.log')
            start = time.time()

            try:
                if canceled:
                    raise KeyboardInterrupt

                if build.skip:
                    result = Result.SKIP
                else:
                    if isinstance(build, DockerInfo):
                        docker_builder = DockerBuilder(
                            build_info=build,
                            scripts_dir_path=self.__scripts_dir_path,
                            prepare_dir_path=self.__prepare_dir_path,
                            tests_dir_path=self.__tests_dir_path,
                            log_func=self.__log,
                        )
                        deploy_result = docker_builder.deploy()
                    elif isinstance(build, VirtualBoxInfo):
                        virtual_box_builder = VirtualBoxBuilder(
                            build_info=build,
                            scripts_dir_path=self.__scripts_dir_path,
                            prepare_dir_path=self.__prepare_dir_path,
                            install_dir_path=self.__install_dir_path,
                            tests_dir_path=self.__tests_dir_path,
                            log_func=self.__log,
                        )
                        deploy_result = virtual_box_builder.deploy()
                    else:
                        deploy_result = False

                    logs = self.__save_logs(install_logs_path)

                    if deploy_result:
                        result = Result.OK
                    else:
                        result = Result.ERROR
                        logs = logs.lower()
                        if 'timeout' in logs or 'timed out' in logs:
                            result = Result.TIMEOUT

                if result == Result.OK:
                    is_results_ok = False

                    path = os.path.join(self.__tests_dir_path, f'{os_name}_{build.build_name}.json')
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

            except KeyboardInterrupt:
                canceled = True
                result = Result.CANCELED
                self.__save_logs(install_logs_path)

            except Exception:
                result = Result.ERROR
                self.__save_logs(install_logs_path)

            if self.__console_mode:
                print(f'\r{log_prefix} ', end='')
            print(f'Elapsed time: {time.time() - start:.2f}. {result.value}')

            self.__results[os_name][build.build_name] = result

        with open(self.__results_file_path, mode='w') as fs:
            fs.write(json.dumps(self.__results))

    def find_lost_results(self):
        self.__builds = self.__builds or self.__download_scripts()
        return self.__results_manager.find_lost_results(self.__all_builds)

    def sync_results(self):
        self.__builds = self.__builds or self.__download_scripts()
        return self.__results_manager.sync_results(self.__all_builds)

    def get_results(self):
        return self.__results_manager.get_results()

    def archive_results(self):
        return self.__results_manager.archive_results()

    def is_results_ok(self):
        return self.__results_manager.is_results_ok()
