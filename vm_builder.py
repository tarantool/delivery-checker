import logging
import subprocess
import time
from collections import namedtuple

from paramiko import SSHClient, AutoAddPolicy, SFTPClient
from paramiko.common import o777

Credentials = namedtuple(
    typename='Credentials',
    field_names=('login', 'password', 'host', 'port', 'work_dir'),
    defaults=('root', 'toor', '127.0.0.1', 10022, '/opt/tarantool'),
)

VmInfo = namedtuple(
    typename='VmInfo',
    field_names=('os_name', 'build_name', 'vm_name', 'credentials'),
)

NAMES = {
    'freebsd': ['freebsd_12.2'],
}

CREDENTIALS = {}


class VmBuilder:
    def __init__(self, log_func=print):
        self.log = log_func

    @staticmethod
    def get_builds(os_name, build_name):
        if os_name not in NAMES:
            return None

        names = NAMES[os_name]
        builds = list(map(
            lambda name: VmInfo(
                os_name, build_name,
                name, CREDENTIALS.get(name, Credentials())
            ),
            names,
        ))

        return builds

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

    @staticmethod
    def exec_ssh_command(client, command, timeout=60, input_data=None):
        with client.get_transport().open_session() as channel:
            channel.get_pty()
            channel.settimeout(timeout)

            channel.exec_command(command)
            if input_data is not None:
                channel.send(input_data)

            if channel.recv_exit_status() != 0:
                return channel.recv(1024 * 1024).decode()

            return None

    def rm(self, vm_name, timeout=60):
        try:
            error = self.exec_command(
                f'vboxmanage controlvm {vm_name} poweroff',
                timeout=timeout,
            )
            if error and 'not currently running' not in error and 'Could not find a registered machine' not in error:
                self.log('Impossible to remove virtual machine:')
                self.log(error)
                return False

            removed = False
            for _ in range(5):  # Maybe it stopping
                error = self.exec_command(
                    f'vboxmanage unregistervm {vm_name} --delete',
                    timeout=timeout,
                )
                if not error or 'Could not find a registered machine' in error:
                    removed = True
                    break

                self.log('Impossible to remove virtual machine:')
                self.log(error)
                time.sleep(3)

            if not removed:
                return False

            error = self.exec_command(
                f'VBoxManage closemedium $HOME/VMs/{vm_name}/{vm_name}.vdi',
                timeout=timeout,
            )
            if error and 'Could not find file' not in error:
                self.log('Impossible to remove virtual machine:')
                self.log(error)
                return False

            error = self.exec_command(
                f'rm -rf $HOME/VMs/{vm_name}',
                timeout=timeout,
            )
            if error:
                self.log('Impossible to remove virtual machine:')
                self.log(error)
                return False

            return True

        except Exception as e:
            self.log(f'Impossible to remove virtual machine: {e}')

        return False

    def build(self, vm_info: VmInfo, timeout=60 * 10):
        try:
            vm_name = vm_info.vm_name

            error = self.exec_command(
                f'vboxmanage clonevm {vm_name}_base --name {vm_name} --mode all --register',
                timeout=timeout,
            )
            if error:
                self.log('Impossible to clone virtual machine:')
                self.log(error)
                return False

            error = self.exec_command(
                f'vboxmanage startvm --type headless {vm_name}',
                timeout=timeout,
            )
            if error:
                self.log('Impossible to run virtual machine:')
                self.log(error)
                return False

            # Wait for SSH connect
            connected = False
            with SSHClient() as client:
                client.set_missing_host_key_policy(AutoAddPolicy())

                old_level = logging.getLogger().level
                logging.getLogger().setLevel(logging.CRITICAL)

                start = time.time()
                while (time.time() - start) < timeout:
                    try:
                        client.connect(
                            hostname=vm_info.credentials.host, port=vm_info.credentials.port,
                            timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
                            username=vm_info.credentials.login, password=vm_info.credentials.password,
                        )
                        connected = True
                        break
                    except Exception as e:
                        self.log(f'Impossible to connect to virtual machine: {e}')
                        time.sleep(5)

                logging.getLogger().setLevel(old_level)

            return connected

        except Exception as e:
            self.log(f'Impossible to clone virtual machine: {e}')

        return False

    def run(self, vm_info: VmInfo, timeout=60 * 10):
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

                error = self.exec_ssh_command(ssh, f'mkdir -p {work_dir} && mkdir -p {results_dir}')
                if error:
                    self.log('Impossible to create working directory on virtual machine:')
                    self.log(error)
                    return False

                sftp: SFTPClient = ssh.open_sftp()
                sftp.chdir(work_dir)
                sftp.put(f'prepare/{vm_info.os_name}.sh', 'prepare.sh')
                sftp.chmod('prepare.sh', o777)
                sftp.put(f'install/{vm_info.os_name}_{vm_info.build_name}.sh', 'install.sh')
                sftp.chmod('install.sh', o777)
                sftp.put('init.lua', f'init.lua')

                error = self.exec_ssh_command(ssh, f'{work_dir}/prepare.sh', timeout)
                if error:
                    self.log('Impossible to prepare virtual machine:')
                    self.log(error)
                    return False

                error = self.exec_ssh_command(ssh, f'{work_dir}/install.sh', timeout)
                if error:
                    self.log('Impossible to install tarantool on virtual machine:')
                    self.log(error)
                    return False

                error = self.exec_ssh_command(
                    ssh,
                    f'export RESULTS_FILE="{results_dir}/{results_file}" && '
                    f'cd {work_dir} && tarantool init.lua',
                    timeout=timeout,
                )
                if error:
                    self.log('Impossible to run tarantool on virtual machine:')
                    self.log(error)
                    return False

                sftp.get(f'{results_dir}/{results_file}', f'./results/{results_file}')

            return True

        except Exception as e:
            self.log(f'Impossible to run tarantool on virtual machine: {e}')

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
