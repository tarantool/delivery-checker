import subprocess

from classes.helpers.common import print_logs


class ShellClient:
    def __init__(self, log_func=print):
        self.log = log_func

    def exec_command(self, command, timeout=60, input_data=None):
        print_logs(in_data=command, log=self.log)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        stdout, stderr = process.communicate(input=input_data, timeout=timeout)
        stdout = stdout.decode()
        stderr = stderr.decode()
        print_logs(out_data=f'{stdout}\n{stderr}\nExit code: {process.returncode}', log=self.log)

        if process.returncode != 0:
            return f'{stdout}\n{stderr}'

        return None

    def exec_commands(self, commands, timeout=60, good_errors=None):
        good_errors = good_errors or []

        for command in commands:
            output = self.exec_command(command, timeout)
            if output is not None:
                output_lower = output.lower()

                is_good = False
                for good_error in good_errors:
                    if good_error.lower() in output_lower:
                        is_good = True
                        break

                if not is_good:
                    return output
