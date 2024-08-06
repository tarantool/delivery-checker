import os
import traceback
from collections import namedtuple

HostInfo = namedtuple(
    typename='HostInfo',
    field_names=(
        'os_name', 'build_name', 'build_commands', 'skip', 'tnt_version'
    )
)


class HostBuilder:
    def __init__(
            self,
            build_info: HostInfo,
            archive_dir_path='./archive',
            scripts_dir_path='.',
            prepare_dir_path='./prepare',
            tests_dir_path='./local/tests',
            results_file_path='results.json'):
        self.build_info = build_info
        self.archive_dir_path = archive_dir_path
        self.scripts_dir_path = scripts_dir_path
        self.prepare_dir_path = prepare_dir_path
        self.tests_dir_path = tests_dir_path
        self.results_file_path = results_file_path

    def run(self):
        try:
            # Get and run the script to prepare OS before tarantool installation
            prepare_script = os.path.join(self.prepare_dir_path,
                                          f'{self.build_info.os_name}.sh')
            os.system(prepare_script)

            # Run commands from API URL (commands_url) for certain OS, build and
            # tarantool version
            for command in self.build_info.build_commands:
                os.system(command)

            # Set env for 'init.lua' check. Run the 'init.lua' test script
            os.environ["TNT_VERSION"] = self.build_info.tnt_version
            os.environ["RESULTS_FILE"] = self.results_file_path
            os.system(os.path.join(str(self.scripts_dir_path), 'init.lua'))

            # Get the path to result file where the class 'Result' awaits it
            path = os.path.join(str(self.tests_dir_path),
                                f'{self.build_info.os_name}_'
                                f'{self.build_info.build_name}.json')
            os.system(f'mv {self.results_file_path} {path}')
        except Exception:
            traceback.print_exc()
            return False

        return True
