import os
import platform
from dataclasses import dataclass

"""
Matches convenient distrib names to what we use in the JSON config.
Use for --dist resolving.
"""
distrib_to_json_name: dict = {
    'amazon': 'amazon-linux',
    'centos': 'rhel-centos',
}

"""
Nobody remembers the Debian release names
"""
debian_version_to_name: dict = {
    '11': 'bullseye',
    '10': 'buster',
    '9': 'stretch',
}


def get_host_os_info():
    """Gets the current OS version in the case of '--host-mode'.

    For macOS, the system is defined as 'Darwin'. Module 'platform' has 'mac_ver'
    method to get the version.
    For Linux versions, we need 'distro' package to get exact linux distribution
    and version.
    """
    # TODO: write the getting OS info if the host OS is Linux
    os_name = platform.system()
    os_version = 'unknown'
    if os_name == 'Darwin':
        os_name = 'macos'
        os_version = platform.mac_ver()[0]
    return os_name, os_version


@dataclass
class CheckerConfig:
    """
    Delivery Checker configuration

    Sets configuration values in the following order:

    1. CLI arguments.
    2. Configuration values in a .json configuration file.
    3. Default values.
    """
    # Parameters to choose the exact installation instruction
    version: str  # Tarantool version from CLI args, such as 2.11 or 3.0
    gc64: bool  # Check installation of GC64 packages
    build: str  # A build type from CLI args: script or manual
    dist: str  # OS for check from CLI args (for docker or VM) or from the host
    dist_version: str  # OS version from CLI args (for docker or VM) or from the host

    # Parameters to choose the check modes
    console_mode: bool  # Run in the console
    debug_mode: bool  # Run with the verbose messages
    host_mode: bool  # Run tests without any virtualization, right on the host

    # Parameters to get installation commands and paths for auxiliary files
    commands_url: str  # URL to download installation instructions (config file/CLI)
    commands_url_user: str  # User, if URL needs authorisation (config file/CLI)
    commands_url_pass: str  # Password, if URL needs authorisation (config file/CLI)
    scripts_dir_path: str  # Path to the dir with installation scripts (config file or './scripts')
    prepare_dir_name: str  # Dir name for bash scripts to prepare OS (config file or 'prepare')
    prepare_dir_path: str  # Path to the dir with preparation scripts (config file or './scripts/prepare')
    install_dir_name: str  # Dir name for installation instructions (config file or 'install')
    install_dir_path: str  # Path to the installation dir (config file or './scripts/install')
    local_dir_path: str  # Path to the archive dir in VM or container (config file or './local')
    remote_dir_path: str  # Path to the remote server dir if `use_remote_results` is True (config file or './remote')
    archive_dir_path: str  # Path to save check logs and test result (config file or './archive')
    logs_dir_name: str  # Name for the check log dir (config file or 'logs')
    logs_dir_path: str  # Path to the check log dir in VM or container (config file or './local/logs')
    tests_dir_name: str  # Name for the tests results dir in VM or container (config file or 'tests')
    tests_dir_path: str  # Path to tests results dir in VM or container (config file or './local/tests')
    results_file_name: str  # Name of the file with check results (config file or 'result.json')
    results_file_path: str  # Path to the result file (config file or './local/results.json')
    default_use_cache: bool  # Whether to use Docker cache or not (config file or 'False')

    # Parameters for the remote configuration
    send_to_remote: dict  # Params for connection to remote server for the check (config file)
    send_to_bot: bool  # Send results to bot (config file)
    use_remote_results: bool  # True, if we use remote server (config file or 'False')

    # Parameters for the VM and Docker setup
    docker_params: dict  # Params for Docker container (config file)
    virtual_box_params: dict  # Params for VM (config file)

    # The whole json config file, stored for debug
    json: dict

    def __init__(self, cli_args, config_json=None):

        self.version = cli_args.version or None
        self.gc64 = cli_args.gc64 or False
        self.build = cli_args.build or None
        self.host_mode = cli_args.host_mode or False

        if self.gc64 and self.build == 'manual':
            raise NotImplementedError(
                'Manual instruction for the installation of GC64 packages is not implemented '
                'on the site'
            )

        if self.host_mode:
            assert self.version, 'Version must be set when --host-mode is used'
            self.dist, self.dist_version = get_host_os_info()
            os.makedirs('./local', exist_ok=True)
        else:
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

        self.send_to_remote = config_json.get('send_to_remote', {})
        self.send_to_bot = config_json.get('send_to_bot', False)
        self.use_remote_results = config_json.get('use_remote_results', False)

        if not self.host_mode:
            os_params = config_json.get('os_params')
            assert config_json.get('os_params'), 'No OS params in config!'

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
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])
