import logging
import os
import time
import zipfile
from collections import namedtuple

from paramiko import SSHClient, AutoAddPolicy

Credentials = namedtuple(
    typename='Credentials',
    field_names=('login', 'password', 'host', 'port'),
)


class SshClient:
    def __init__(self, credentials: Credentials, log_func=print):
        self.log = log_func
        self.credentials = credentials
        self.__ssh = None
        self.__sftp = None

    def __del__(self):
        if self.__sftp is not None:
            self.__sftp.close()
        if self.__ssh is not None:
            self.__ssh.close()

    def __connect(self, timeout=60, reconnect=False):
        if self.__ssh is not None:
            if not reconnect:
                return

            self.__sftp.close()
            self.__sftp = None

            self.__ssh.close()
            self.__ssh = None

        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(
            hostname=self.credentials.host, port=self.credentials.port,
            username=self.credentials.login, password=self.credentials.password,
            timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
        )
        self.__ssh = ssh

    def wait_until(self, func, excepted=None, timeout=30, period=1, error_msg='Impossible to wait', *args, **kwargs):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if func(*args, **kwargs) == excepted:
                    return True
            except Exception as e:
                self.log(f'{error_msg}: {e}')
            time.sleep(period)

        self.log(f'{error_msg}: timeout')
        return False

    def wait_ssh(self, timeout=60 * 10):
        old_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.CRITICAL)

        connected = self.wait_until(
            lambda: self.__connect(timeout=timeout),
            timeout=timeout,
            period=5,
            error_msg='Impossible to connect to virtual machine',
        )

        logging.getLogger().setLevel(old_level)

        return connected

    def exec_ssh_command(self, command, timeout=60, input_data=None):
        self.__connect()

        with self.__ssh.get_transport().open_session() as channel:
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

    def exec_ssh_commands(self, commands, timeout=60):
        for command in commands:
            error = self.exec_ssh_command(command, timeout)
            if error:
                raise Exception(f'Impossible to execute SSH command "{command}":\n{error}')

    def get_sftp(self):
        self.__connect()

        if self.__sftp is not None:
            return self.__sftp

        self.__sftp = self.__ssh.open_sftp()
        return self.__sftp

    @staticmethod
    def __zip_one(fp, path, rel_dir='.'):
        rel_path = os.path.relpath(path, rel_dir)
        if rel_path != '.':
            fp.write(path, rel_path)

    def __zip_all(self, fp, path, rel_dir='.'):
        if os.path.isdir(path):
            for root, sub_dirs, files in os.walk(path):
                for sub_dir in sub_dirs:
                    self.__zip_one(fp, os.path.join(root, sub_dir), rel_dir)
                for file in files:
                    self.__zip_one(fp, os.path.join(root, file), rel_dir)
        else:
            self.__zip_one(fp, path, rel_dir)

    def send_files_as_zip(self, paths, rel_dir='.', zip_name='output.zip', remote_dir='.', timeout=60 * 5):
        try:
            fp = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
            for path in paths:
                self.__zip_all(fp, path, rel_dir)
            fp.close()

            self.exec_ssh_command(f'mkdir -p {remote_dir}', timeout=timeout)
            self.get_sftp().put(zip_name, f'{remote_dir}/{zip_name}')
        finally:
            os.remove(zip_name)
