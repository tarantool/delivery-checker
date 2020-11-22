import subprocess


class ShellClient:
    def __init__(self, log_func=print):
        self.log = log_func

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
