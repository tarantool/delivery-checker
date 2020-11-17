import subprocess
from collections import namedtuple

from paramiko import SFTPClient
from paramiko.common import o777

from builders.ssh import Credentials, SshClient

VirtualBoxInfo = namedtuple(
    typename='VirtualBoxInfo',
    field_names=('os_name', 'build_name', 'vm_name', 'credentials', 'remote_dir', 'run_timeout', 'skip'),
)


class VirtualBoxBuilder:
    def __init__(self, build_info: VirtualBoxInfo, log_func=print):
        self.log = log_func
        self.build_info = build_info
        self.__ssh_client = None

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
                    login=vm_params[1].get('credentials', {}).get('login', 'root'),
                    password=vm_params[1].get('credentials', {}).get('password', 'toor'),
                    host=vm_params[1].get('credentials', {}).get('host', '127.0.0.1'),
                    port=vm_params[1].get('credentials', {}).get('port', 10022),
                ),
                remote_dir=vm_params[1].get('remote_dir', '/opt/tarantool'),
                run_timeout=vm_params[1].get('run_timeout'),
                skip=build_name in vm_params[1].get('skip', []),
            ),
            params.items(),
        ))

    @staticmethod
    def exec_command(command, timeout=60, input_data=None):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        output, error = process.communicate(input=input_data, timeout=timeout)
        output = output.decode()
        error = error.decode()

        if process.returncode != 0:
            return output + error

        return None

    def exec_commands(self, commands, timeout=60, good_errors=None):
        good_errors = good_errors or []

        for command in commands:
            error = self.exec_command(command, timeout)
            if error:
                is_good = False
                for good_error in good_errors:
                    if good_error in error:
                        is_good = True
                        break

                if not is_good:
                    raise Exception(f'Impossible to execute command "{command}":\n{error}')

    def rm(self, timeout=60):
        try:
            vm_name = self.build_info.vm_name
            self.exec_commands(
                commands=[
                    f'VBoxManage controlvm {vm_name} poweroff',
                    'sleep 3',  # Wait for poweroff
                    f'VBoxManage unregistervm {vm_name} --delete',
                    f'VBoxManage closemedium $HOME/VMs/{vm_name}/{vm_name}.vdi',
                    f'rm -rf $HOME/VMs/{vm_name}',
                ],
                good_errors=[
                    'not currently running',
                    'Could not find a registered machine',
                    'Could not find file',
                ],
                timeout=timeout,
            )
            return True

        except Exception as e:
            self.log(f'Impossible to remove virtual machine:\n{e}')
            return False

    def build(self, timeout=60 * 10):
        try:
            vm_name = self.build_info.vm_name
            self.exec_commands(
                commands=[
                    f'vboxmanage clonevm {vm_name}_base --name {vm_name} --mode all --register',
                    f'vboxmanage startvm --type headless {vm_name}',
                ],
                timeout=timeout,
            )

            self.__ssh_client = SshClient(self.build_info.credentials, log_func=self.log)
            return self.__ssh_client.wait_ssh(timeout)

        except Exception as e:
            self.log(f'Impossible to clone virtual machine:\n{e}')
            return False

    def run(self, timeout=60 * 3):
        if self.build_info.run_timeout is not None:
            timeout = self.build_info.run_timeout

        try:
            if self.__ssh_client is None:
                self.__ssh_client = SshClient(self.build_info.credentials, log_func=self.log)

            remote_dir = self.build_info.remote_dir
            results_dir = f'{remote_dir}/results'
            results_file = f'{self.build_info.vm_name}_{self.build_info.build_name}.json'

            self.__ssh_client.exec_ssh_commands(
                commands=[
                    f'mkdir -p {remote_dir}',
                    f'mkdir -p {results_dir}',
                ],
                timeout=timeout,
            )

            sftp: SFTPClient = self.__ssh_client.get_sftp()
            sftp.chdir(remote_dir)
            sftp.put(f'prepare/{self.build_info.os_name}.sh', 'prepare.sh')
            sftp.chmod('prepare.sh', o777)
            sftp.put(f'install/{self.build_info.os_name}_{self.build_info.build_name}.sh', 'install.sh')
            sftp.chmod('install.sh', o777)
            sftp.put('init.lua', f'init.lua')

            self.__ssh_client.exec_ssh_commands(
                commands=[
                    f'{remote_dir}/prepare.sh',
                    f'{remote_dir}/install.sh',
                    f'cd {remote_dir} && '
                    f'export RESULTS_FILE="{results_dir}/{results_file}" && '
                    f'tarantool init.lua',
                ],
                timeout=timeout,
            )

            sftp.get(f'{results_dir}/{results_file}', f'./local/results/{results_file}')

            return True

        except Exception as e:
            self.log(f'Impossible to run tarantool on virtual machine:\n{e}')

        return False

    def deploy(self):
        is_success = True
        if not self.rm():
            is_success = False
        if is_success and not self.build():
            is_success = False
        if is_success and not self.run():
            is_success = False
        if not self.rm():
            is_success = False
        return is_success
