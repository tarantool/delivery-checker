import logging
import subprocess
import time
from collections import namedtuple

from paramiko import SSHClient, AutoAddPolicy, SFTPClient
from paramiko.common import o777

Credentials = namedtuple(
    typename='Credentials',
    field_names=('login', 'password', 'host', 'port', 'work_dir'),
)

VirtualBoxInfo = namedtuple(
    typename='VirtualBoxInfo',
    field_names=('os_name', 'build_name', 'vm_name', 'credentials', 'skip'),
)


class VirtualBoxBuilder:
    def __init__(self, config, log_func=print):
        self.log = log_func
        self.config = config

    def get_builds(self, os_name, build_name):
        params = self.config.get(os_name)
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
                    work_dir=vm_params[1].get('credentials', {}).get('work_dir', '/opt/tarantool'),
                ),
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

    def wait_until(self, func, excepted=None, timeout=30, period=1, error_msg='Impossible to wait', *args, **kwargs):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if func(*args, **kwargs) == excepted:
                    return True
            except Exception as e:
                self.log(f'{error_msg}: {e}')
            time.sleep(period)

        return False

    def wait_ssh(self, vm_info: VirtualBoxInfo, timeout=60 * 10):
        with SSHClient() as client:
            client.set_missing_host_key_policy(AutoAddPolicy())

            old_level = logging.getLogger().level
            logging.getLogger().setLevel(logging.CRITICAL)

            connected = self.wait_until(
                lambda: client.connect(
                    hostname=vm_info.credentials.host, port=vm_info.credentials.port,
                    timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
                    username=vm_info.credentials.login, password=vm_info.credentials.password,
                ),
                timeout=timeout,
                period=5,
                error_msg='Impossible to connect to virtual machine',
            )

            logging.getLogger().setLevel(old_level)

            return connected

    def exec_ssh_command(self, client, command, timeout=60, input_data=None):
        with client.get_transport().open_session() as channel:
            channel.get_pty()
            channel.settimeout(timeout)

            channel.exec_command(command)
            if input_data is not None:
                channel.send(input_data)

            if self.wait_until(
                channel.exit_status_ready,
                excepted=True,
                timeout=timeout,
                error_msg='Impossible to check availability to get exit status',
            ):
                if channel.recv_exit_status() == 0:
                    return None

            stdout = ''
            stderr = ''
            channel.settimeout(0)

            try:
                stdout = channel.recv(1024 ** 3).decode()
            except Exception as e:
                self.log(f'Impossible to get stdout: "{e}"')
            try:
                stderr = channel.recv_stderr(1024 ** 3).decode()
            except Exception as e:
                self.log(f'Impossible to get stderr: "{e}"')

            return f'{stdout}\n{stderr}'

    def exec_ssh_commands(self, client, commands, timeout=60):
        for command in commands:
            error = self.exec_ssh_command(client, command, timeout)
            if error:
                raise Exception(f'Impossible to execute SSH command "{command}":\n{error}')

    def rm(self, vm_name, timeout=60):
        try:
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

    def build(self, vm_info: VirtualBoxInfo, timeout=60 * 10):
        try:
            self.exec_commands(
                commands=[
                    f'vboxmanage clonevm {vm_info.vm_name}_base --name {vm_info.vm_name} --mode all --register',
                    f'vboxmanage startvm --type headless {vm_info.vm_name}',
                ],
                timeout=timeout,
            )

            return self.wait_ssh(vm_info, timeout)

        except Exception as e:
            self.log(f'Impossible to clone virtual machine:\n{e}')
            return False

    def run(self, vm_info: VirtualBoxInfo, timeout=60 * 3):
        try:
            with SSHClient() as ssh:
                ssh.set_missing_host_key_policy(AutoAddPolicy())
                ssh.connect(
                    hostname=vm_info.credentials.host, port=vm_info.credentials.port,
                    username=vm_info.credentials.login, password=vm_info.credentials.password,
                )

                work_dir = vm_info.credentials.work_dir
                results_dir = f'{work_dir}/results'
                results_file = f'{vm_info.os_name}_{vm_info.build_name}.json'

                self.exec_ssh_commands(
                    client=ssh,
                    commands=[
                        f'mkdir -p {work_dir}',
                        f'mkdir -p {results_dir}',
                    ],
                    timeout=timeout,
                )

                sftp: SFTPClient = ssh.open_sftp()
                sftp.chdir(work_dir)
                sftp.put(f'prepare/{vm_info.os_name}.sh', 'prepare.sh')
                sftp.chmod('prepare.sh', o777)
                sftp.put(f'install/{vm_info.os_name}_{vm_info.build_name}.sh', 'install.sh')
                sftp.chmod('install.sh', o777)
                sftp.put('init.lua', f'init.lua')

                self.exec_ssh_commands(
                    client=ssh,
                    commands=[
                        f'{work_dir}/prepare.sh',
                        f'{work_dir}/install.sh',
                        f'cd {work_dir} && '
                        f'export RESULTS_FILE="{results_dir}/{results_file}" && '
                        f'tarantool init.lua',
                    ],
                    timeout=timeout,
                )

                sftp.get(f'{results_dir}/{results_file}', f'./results/{results_file}')

            return True

        except Exception as e:
            self.log(f'Impossible to run tarantool on virtual machine:\n{e}')

        return False

    def deploy(self, build_info):
        if not self.rm(build_info.vm_name):
            return False
        if not self.build(build_info):
            return False
        if not self.run(build_info):
            return False
        if not self.rm(build_info.vm_name):
            return False
        return True
