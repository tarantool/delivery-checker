import os
from dataclasses import dataclass
from typing import Optional

"""
Matches convenient distrib names to what we use in the JSON config.
Use for --dist resolving.
"""
distrib_to_json_name: dict = {
    'amazon': 'amazon-linux',
    'centos': 'rhel-centos',
    'macos': 'os-x',
    'osx': 'os-x',
}

"""
Nobody remembers the Debian release names
"""
debian_version_to_name: dict = {
    '11': 'bullseye',
    '10': 'buster',
    '9': 'stretch',
}


@dataclass
class CheckerConfig:
    """
    Delivery Checker configuration

    Sets configuration values in the following order:

    1. CLI arguments.
    2. Configuration values in a .json configuration file.
    3. Default values.
    """
    version: str
    build: str
    dist: str
    dist_version: str

    console_mode: bool
    debug_mode: bool
    ci_mode: bool

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

        self.version = cli_args.version or None
        self.build = cli_args.build or None

        assert not cli_args.dist_version or cli_args.dist, 'Argument --dist-version requires --dist'
        self.dist = distrib_to_json_name.get(cli_args.dist, cli_args.dist)
        if self.dist == 'debian':
            self.dist_version = \
                debian_version_to_name.get(cli_args.dist_version) or \
                cli_args.dist_version or None
        else:
            self.dist_version = cli_args.dist_version or None

        self.console_mode = cli_args.console_mode
        self.debug_mode = cli_args.debug_mode
        self.ci_mode = cli_args.ci_mode or os.environ.get('GITHUB_ENV') is not None

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
            if v.get('docker') is not None and (not self.dist or self.dist == k)
        }
        if self.dist_version:
            assert self.dist_version in self.docker_params[self.dist]['versions'], \
                f'version {self.dist_version} not found in the list of {self.dist} versions'
            self.docker_params[self.dist]['versions'] = [self.dist_version]

        self.virtual_box_params = {
            k: v['virtual_box']
            for k, v in os_params.items()
            if v.get('virtual_box') is not None and (not self.dist or self.dist == k)
        }
        self.json = config_json

        if self.debug_mode:
            print(self)

    def __str__(self):
        return ''.join([f'{k}: {v}\n' for k, v in self.__dict__.items()])
