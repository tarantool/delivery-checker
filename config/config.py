import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CheckerConfig:
    """
    Delivery Checker configuration

    Sets configuration values in the following order:

    1. CLI arguments.
    2. Configuration values in a .json configuration file.
    3. Default values.
    """
    console_mode: bool
    debug_mode: bool

    commands_url: str
    commands_url_user: str
    commands_url_pass: str
    scripts_dir_path: str
    prepare_dir_name: str
    prepare_dir_path: str
    install_dir_name: str
    install_dir_path: str
    local_dir_path: str
    remote_dir_path: str
    archive_dir_path: str
    logs_dir_name: str
    logs_dir_path: str
    tests_dir_name: str
    tests_dir_path: str
    results_file_name: str
    results_file_path: str
    default_use_cache: str

    # remote configuration
    send_to_remote: dict
    use_remote_results: bool

    # large dicts
    docker_params: dict
    virtual_box_params: dict

    # the whole json config, stored for debug
    json: dict

    def __init__(self, cli_args, config_json):
        self.console_mode = cli_args.console_mode
        self.debug_mode = cli_args.debug_mode

        self.commands_url = \
            cli_args.commands_url or \
            config_json.get('commands_url') or \
            'https://www.tarantool.io/api/tarantool/info/versions/'
        self.commands_url_user = \
            cli_args.commands_url_user or \
            config_json.get('commands_url_user')
        self.commands_url_pass = \
            cli_args.commands_url_pass or \
            config_json.get('commands_url_pass')

        self.scripts_dir_path = config_json.get('scripts_dir_path', './scripts')

        self.prepare_dir_name = config_json.get('prepare_dir_name', 'prepare')
        self.prepare_dir_path = os.path.join(self.scripts_dir_path, self.prepare_dir_name)

        self.install_dir_name = config_json.get('install_dir_name', 'install')
        self.install_dir_path = os.path.join(self.scripts_dir_path, self.install_dir_name)

        self.local_dir_path = config_json.get('local_dir_path', './local')
        self.remote_dir_path = config_json.get('remote_dir_path', './remote')
        self.archive_dir_path = config_json.get('archive_dir_path', './archive')

        self.logs_dir_name = config_json.get('logs_dir_name', 'logs')
        self.logs_dir_path = os.path.join(self.local_dir_path, self.logs_dir_name)

        self.tests_dir_name = config_json.get('tests_dir_name', 'tests')
        self.tests_dir_path = os.path.join(self.local_dir_path, self.tests_dir_name)

        self.results_file_name = config_json.get('results_file_name', 'results.json')
        self.results_file_path = os.path.join(self.local_dir_path, self.results_file_name)

        self.default_use_cache = config_json.get('default_use_cache', False)

        os_params = config_json.get('os_params')
        assert config_json.get('os_params') is not None, 'No OS params in config!'

        self.send_to_remote = config_json.get('send_to_remote')
        self.use_remote_results = config_json.get('use_remote_results', False)

        self.docker_params = {
            k: v['docker']
            for k, v in os_params.items()
            if v.get('docker') is not None
        }
        self.virtual_box_params = {
            k: v['virtual_box']
            for k, v in os_params.items()
            if v.get('virtual_box') is not None
        }
        self.json = config_json

    def __str__(self):
        return ''.join([f'{k}: {v}\n' for k, v in self.__dict__.items()])
