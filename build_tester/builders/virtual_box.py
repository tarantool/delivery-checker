import os
from collections import namedtuple

from paramiko import SFTPClient
from paramiko.common import o777

from build_tester.helpers.common import wait_until
from build_tester.helpers.shell import ShellClient
from build_tester.helpers.ssh import Credentials, SshClient

VirtualBoxInfo = namedtuple(
    typename='VirtualBoxInfo',
    field_names=(
        'os_name', 'build_name', 'vm_name', 'credentials', 'remote_dir',
        'skip_prepare', 'prepare_timeout', 'run_timeout', 'skip',
    ),
)


class VirtualBoxBuilder:
    def __init__(
        self, build_info: VirtualBoxInfo,
        scripts_dir_path='.',
        prepare_dir_path='./prepare',
        install_dir_path='./install',
        tests_dir_path='./tests',
        log_func=print
    ):
        self.build_info = build_info
        self.scripts_dir_path = scripts_dir_path
        self.prepare_dir_path = prepare_dir_path
        self.install_dir_path = install_dir_path
        self.tests_dir_path = tests_dir_path
        self.log = log_func

        self.__shell_client = ShellClient(log_func=log_func)
        self.__ssh_client = SshClient(self.build_info.credentials, log_func=self.log)

    @staticmethod
    def get_builds(config, os_name, build_name):
        params = config.get(os_name)
        if params is None:
            return []

        return list(map(
            lambda vm_params: VirtualBoxInfo(
                os_name=os_name,
                build_name=build_name,
                vm_name=vm_params[0],
                credentials=Credentials(
                    login=vm_params[1].get('login', 'root'),
                    password=vm_params[1].get('password', 'toor'),
                    host=vm_params[1].get('host', '127.0.0.1'),
                    port=vm_params[1].get('port', 10022),
                ),
                remote_dir=vm_params[1].get('remote_dir', '/opt/tarantool'),
                skip_prepare=vm_params[1].get('skip_prepare'),
                prepare_timeout=vm_params[1].get('prepare_timeout'),
                run_timeout=vm_params[1].get('run_timeout'),
                skip=build_name in vm_params[1].get('skip', []),
            ),
            params.items(),
        ))

    def restore(self, timeout=60):
        try:
            vm_name = self.build_info.vm_name
            if self.__shell_client.exec_commands(
                commands=[
                    f'VBoxManage controlvm {vm_name} poweroff',
                    'sleep 3',  # Wait for full poweroff
                    f'VBoxManage snapshot {vm_name} restorecurrent',
                ],
                good_errors=[
                    'not currently running',
                    'does not have any snapshots',
                ],
                timeout=timeout,
            ) is not None:
                return False

            return True

        except Exception as e:
            self.log(f'Impossible to restore virtual machine:\n{e}')

        return False

    def start(self, timeout=60 * 5):
        try:
            vm_name = self.build_info.vm_name

            if self.__shell_client.exec_commands(
                commands=[
                    f'VBoxManage snapshot {vm_name} showvminfo base || VBoxManage snapshot {vm_name} take base',
                    f'VBoxManage startvm --type headless {vm_name}',
                ],
                timeout=timeout,
            ) is not None:
                return False

            if not self.__ssh_client.wait_ssh(timeout, reconnect=True):
                return False

            return True

        except Exception as e:
            self.log(f'Impossible to start virtual machine:\n{e}')

        return False

    def prepare(self, timeout=60 * 5):
        if self.build_info.skip_prepare:
            return True

        if self.build_info.prepare_timeout is not None:
            timeout = self.build_info.prepare_timeout

        try:
            vm_name = self.build_info.vm_name
            remote_dir = self.build_info.remote_dir

            if self.__ssh_client.exec_ssh_commands(
                commands=[f'mkdir -p {remote_dir}'],
                timeout=timeout,
            ) is not None:
                return False

            sftp: SFTPClient = self.__ssh_client.get_sftp()
            sftp.chdir(remote_dir)
            sftp.put(os.path.join(self.prepare_dir_path, f'{self.build_info.os_name}.sh'), 'prepare.sh')
            sftp.chmod('prepare.sh', o777)

            if self.__ssh_client.exec_ssh_commands(
                commands=[os.path.join(remote_dir, 'prepare.sh')],
                good_errors=['shutdown'],
                timeout=timeout,
            ) is not None:
                return False

            if not wait_until(
                lambda: self.__shell_client.exec_commands([f'VBoxManage showvminfo {vm_name} | grep "powered off"']),
                timeout=60,
                error_msg=f'Impossible to shutdown {vm_name}',
                log=self.log,
            ):
                return False

            if self.__shell_client.exec_commands(
                commands=[
                    'sleep 3',  # Wait for full poweroff
                    f'VBoxManage snapshot {vm_name} delete base',
                    'sleep 3',  # Wait for full snapshot delete
                ],
                timeout=120,
            ) is not None:
                return False

            return self.start()

        except Exception as e:
            self.log(f'Impossible to prepare virtual machine:\n{e}')

        return False

    def run(self, timeout=60 * 5):
        if self.build_info.run_timeout is not None:
            timeout = self.build_info.run_timeout

        try:
            remote_dir = self.build_info.remote_dir
            remote_results_dir = os.path.join(remote_dir, 'results')
            results_file = f'{self.build_info.vm_name}_{self.build_info.build_name}.json'

            if self.__ssh_client.exec_ssh_commands(
                commands=[f'mkdir -p {remote_results_dir}'],
                timeout=timeout,
            ) is not None:
                return False

            sftp: SFTPClient = self.__ssh_client.get_sftp()
            sftp.chdir(remote_dir)
            sftp.put(
                os.path.join(self.install_dir_path, f'{self.build_info.os_name}_{self.build_info.build_name}.sh'),
                'install.sh',
            )
            sftp.chmod('install.sh', o777)
            sftp.put(os.path.join(self.scripts_dir_path, 'init.lua'), f'init.lua')

            if self.__ssh_client.exec_ssh_commands(
                commands=[
                    os.path.join(remote_dir, 'install.sh'),
                    f'cd {remote_dir} && '
                    f'export RESULTS_FILE="{os.path.join(remote_results_dir, results_file)}" && '
                    f'export TNT_VERSION="{self.build_info.build_name.split("_")[-1]}" && '
                    f'tarantool init.lua',
                ],
                timeout=timeout,
            ) is not None:
                return False

            sftp.get(
                os.path.join(remote_results_dir, results_file),
                os.path.join(self.tests_dir_path, results_file),
            )

            return True

        except Exception as e:
            self.log(f'Impossible to run tarantool on virtual machine:\n{e}')

        return False

    def deploy(self):
        is_success = True
        if not self.restore():
            is_success = False
        if is_success and not self.start():
            is_success = False
        if is_success and not self.prepare():
            is_success = False
        if is_success and not self.run():
            is_success = False
        self.restore()
        return is_success
