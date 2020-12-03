import logging
import os
from collections import namedtuple

from paramiko import SSHClient, AutoAddPolicy

from classes.helpers.common import wait_until, print_logs

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

    def wait_ssh(self, timeout=60 * 10, reconnect=False):
        old_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.CRITICAL)

        connected = wait_until(
            lambda: self.__connect(timeout=timeout, reconnect=reconnect),
            timeout=timeout,
            period=5,
            error_msg='Impossible to connect to virtual machine',
            log=self.log,
        )

        logging.getLogger().setLevel(old_level)

        return connected

    def __wait_exit_code(self, channel, timeout=60):
        if wait_until(
            channel.exit_status_ready,
            excepted=True,
            timeout=timeout,
            error_msg='Impossible to check availability to get exit status',
            log=self.log,
        ):
            return channel.recv_exit_status()
        return 1

    def __get_channel_output(self, channel):
        channel.settimeout(1)

        stdout = ''
        try:
            stdout = channel.recv(1024 ** 3).decode()
        except Exception as e:
            self.log(f'Impossible to get stderr: "{e}"')

        stderr = ''
        try:
            stderr = channel.recv_stderr(1024 ** 3).decode()
        except Exception as e:
            self.log(f'Impossible to get stderr: "{e}"')

        return f'{stdout}\n{stderr}'

    def exec_ssh_command(self, command, timeout=60, input_data=None):
        self.__connect()

        with self.__ssh.get_transport().open_session() as channel:
            channel.get_pty()
            channel.settimeout(timeout)

            print_logs(in_data=command, log=self.log)
            channel.exec_command(command)
            if input_data is not None:
                channel.send(input_data)

            exit_code = self.__wait_exit_code(channel, timeout)
            output = self.__get_channel_output(channel)
            print_logs(out_data=f'Logs:\n{output}\nExit code: {exit_code}', log=self.log)
            if exit_code != 0:
                return output

    def exec_ssh_commands(self, commands, timeout=60, good_errors=None):
        good_errors = good_errors or []

        for command in commands:
            output = self.exec_ssh_command(command, timeout)
            if output is not None:
                output_lower = output.lower()

                is_good = False
                for good_error in good_errors:
                    if good_error.lower() in output_lower:
                        is_good = True
                        break

                if not is_good:
                    return output

    def get_sftp(self):
        self.__connect()

        if self.__sftp is not None:
            return self.__sftp

        self.__sftp = self.__ssh.open_sftp()
        return self.__sftp

    def send_file(self, zip_name='output.zip', remote_dir='.', timeout=60 * 5):
        try:
            self.exec_ssh_command(f'mkdir -p {remote_dir}', timeout=timeout)
            self.get_sftp().put(zip_name, f'{remote_dir}/{zip_name}')
        finally:
            os.remove(zip_name)
